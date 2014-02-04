from ben10.filesystem import CreateDirectory, CreateFile
from ben10.foundation.string import Dedent
from jobs_done10.generators.jenkins import GetJobsFromDirectory, GetJobsFromFile, UploadJobsFromFile
from jobs_done10.git import Git
from jobs_done10.jobs_done_job import JOBS_DONE_FILENAME
from jobs_done10.repository import Repository
import os



#===================================================================================================
# Test
#===================================================================================================
class Test(object):
    '''
    Integration tests for Jenkins actions
    '''

    _JOBS_DONE_FILE_CONTENTS = Dedent(
        '''
        junit_patterns:
        - "junit*.xml"

        boosttest_patterns:
        - "cpptest*.xml"

        parameters:
          - choice:
              name: "PARAM"
              choices:
              - "choice_1"
              - "choice_2"
              description: "Description"

        build_batch_commands:
        - "command"

        matrix:
            planet:
            - mercury
            - venus
            - jupiter

        '''
    )

    _REPOSITORY = Repository(url='http://space.git', branch='branch')

    def testGetJobsFromFile(self, embed_data):
        job_group, jobs = GetJobsFromFile(self._REPOSITORY, self._JOBS_DONE_FILE_CONTENTS)

        assert job_group == self._REPOSITORY.name + '-' + self._REPOSITORY.branch
        assert len(jobs) == 3


    def testGetJobsFromDirectory(self, embed_data):
        repo_path = embed_data['git_repository']
        CreateDirectory(repo_path)

        # Prepare git repository
        git = Git()
        git.Execute(['init'], repo_path)
        git.AddRemote(repo_path, 'origin', self._REPOSITORY.url)
        git.CreateLocalBranch(repo_path, self._REPOSITORY.branch)
        CreateFile(os.path.join(repo_path, '.gitignore'), '')
        git.Add(repo_path, '.')
        git.Commit(repo_path, 'First commitAdded jobs_done file')

        # If there is no jobs_done file, we should get zero jobs
        job_group, jobs = GetJobsFromDirectory(repo_path)
        assert job_group == 'space-branch'
        assert len(jobs) == 0

        # Create jobs_done file
        CreateFile(os.path.join(repo_path, JOBS_DONE_FILENAME), self._JOBS_DONE_FILE_CONTENTS)
        git.Add(repo_path, '.')
        git.Commit(repo_path, 'Added jobs_done file')

        job_group, jobs = GetJobsFromDirectory(repo_path)
        assert job_group == self._REPOSITORY.name + '-' + self._REPOSITORY.branch
        assert len(jobs) == 3


    def testUploadJobsFromFile(self, monkeypatch):
        '''
        Tests that UploadJobsFromFile correctly calls JenkinsJobPublisher (already tested elsewhere)
        '''
        def MockPublishToUrl(self, url, username, password):
            assert url == 'jenkins_url'
            assert username == 'jenkins_user'
            assert password == 'jenkins_pass'

            assert set(self.jobs.keys()) == set([
                'space-branch-venus', 'space-branch-jupiter', 'space-branch-mercury'])

            return 'mock publish result'

        from jobs_done10.generators.jenkins import JenkinsJobPublisher
        monkeypatch.setattr(JenkinsJobPublisher, 'PublishToUrl', MockPublishToUrl)

        result = UploadJobsFromFile(
            repository=self._REPOSITORY,
            jobs_done_file_contents=self._JOBS_DONE_FILE_CONTENTS,
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert result == 'mock publish result'
