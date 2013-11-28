from ben10.filesystem import CreateDirectory, CreateFile
from ben10.foundation.string import Dedent
from jobs_done10.generators.jenkins import GetJobsFromFile, GetJobsFromDirectory, UploadJobsFromFile
from jobs_done10.jobs_done_file import JOBS_DONE_FILENAME
from jobs_done10.repository import Repository
from sharedscripts10.shared_scripts.git_ import Git
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

        build_batch_command: "command"

        planets:
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


    def testBranchPatterns(self, embed_data):
        # Using a pattern that does not match our branch will prevent jobs from being generated
        jd_file_contents = self._JOBS_DONE_FILE_CONTENTS
        jd_file_contents += Dedent(
            '''
            branch_patterns:
            - feature-.*
            '''
        )
        _job_group, jobs = GetJobsFromFile(self._REPOSITORY, jd_file_contents)
        assert len(jobs) == 0

        # Matching patterns work as usual
        jd_file_contents = self._JOBS_DONE_FILE_CONTENTS
        jd_file_contents += Dedent(
            '''
            branch_patterns:
            - branch
            '''
        )
        _job_group, jobs = GetJobsFromFile(self._REPOSITORY, jd_file_contents)
        assert len(jobs) == 3

        # Also works with several patterns and regexes
        jd_file_contents = self._JOBS_DONE_FILE_CONTENTS
        jd_file_contents += Dedent(
            '''
            branch_patterns:
            - master
            - b.*
            '''
        )
        _job_group, jobs = GetJobsFromFile(self._REPOSITORY, jd_file_contents)
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
        assert job_group == self._REPOSITORY.name + '-' + self._REPOSITORY.branch
        assert len(jobs) == 0
        
        # Create jobs_done file
        CreateFile(os.path.join(repo_path, JOBS_DONE_FILENAME), self._JOBS_DONE_FILE_CONTENTS)
        git.Add(repo_path, '.')
        git.Commit(repo_path, 'Added jobs_done file')

        job_group, jobs = GetJobsFromDirectory(repo_path)
        assert job_group == self._REPOSITORY.name + '-' + self._REPOSITORY.branch
        assert len(jobs) == 3


    def testUploadJobsFromFile(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        new_jobs, updated_jobs, deleted_jobs = UploadJobsFromFile(
            repository=self._REPOSITORY,
            jobs_done_file_contents=self._JOBS_DONE_FILE_CONTENTS,
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == set(['space-branch-venus', 'space-branch-jupiter'])
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == set(['space-branch-mercury'])
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == set(['space-branch-saturn'])


    def testUploadJobsFromFile2(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        new_jobs, updated_jobs, deleted_jobs = UploadJobsFromFile(
            repository=self._REPOSITORY,
            jobs_done_file_contents=None,
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == set()
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == set()
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == set(['space-branch-mercury', 'space-branch-saturn'])


    def _MockJenkinsAPI(self, monkeypatch):
        class MockJenkins(object):
            NEW_JOBS = set()
            UPDATED_JOBS = set()
            DELETED_JOBS = set()

            def __init__(self, url, username, password):
                assert url == 'jenkins_url'
                assert username == 'jenkins_user'
                assert password == 'jenkins_pass'

            def get_jobs(self):
                return [
                    {'name' : 'space-branch-mercury'},
                    {'name' : 'space-branch-saturn'},
                ]

            def create_job(self, name, xml):
                self.NEW_JOBS.add(name)

            def reconfig_job(self, name, xml):
                self.UPDATED_JOBS.add(name)

            def delete_job(self, name):
                self.DELETED_JOBS.add(name)


        import jenkins
        monkeypatch.setattr(jenkins, 'Jenkins', MockJenkins)

        return MockJenkins
