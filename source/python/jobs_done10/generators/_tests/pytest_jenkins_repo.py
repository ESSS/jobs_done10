from jobs_done10.generators.jenkins import JenkinsJobGenerator
from jobs_done10.job_generator import JobGeneratorConfigurator
from jobs_done10.jobs_done_file import JobsDoneFile
from jobs_done10.repository import Repository
import os



#===================================================================================================
# Test
#===================================================================================================
class Test(object):



    def testEmpty(self, embed_data):
        '''
        '''
        repo_dir = embed_data['jd_repo']

        # Enable git repo for jobs
        os.environ['JOBS_DONE_JENKINS_REPO'] = repo_dir

        # Create some jobs

        # See that they were created in the repository





    def _DoTest(self, ci_contents, expected_diff):
        '''
        :param str ci_contents:
            Contents of JobsDoneFile used for this test

        :param str expected_diff:
            Expected diff from build jobs from `ci_contents`, when compared to BASIC_EXPECTED_YAML.
        '''
        repository = Repository(url='http://fake.git')
        jobs_done_files = JobsDoneFile.CreateFromYAML(ci_contents)

        job_generator = JenkinsJobGenerator()
        JobGeneratorConfigurator.Configure(job_generator, jobs_done_files[0], repository)
        obtained_yaml = job_generator.Build()

        self._AssertDiff(obtained_yaml, expected_diff)

