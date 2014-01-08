from pyjenkins import JenkinsJobGenerator
import os



#===================================================================================================
# Test
#===================================================================================================
class Test:

    def testCreateConfigFile(self, embed_data):
        config_filename = embed_data['testCreateConfigFile.xml']

        assert os.path.isfile(config_filename) == False

        job_generator = JenkinsJobGenerator('job-name')
        job_generator.CreateConfigFile(config_filename)

        assert os.path.isfile(config_filename) == True

        expected_config_filename = embed_data['testCreateConfigFile.expected.xml']
        embed_data.AssertEqualFiles(config_filename, expected_config_filename)


    def testGetJobName(self):
        job_generator = JenkinsJobGenerator('job-name')
        assert (
            job_generator.GetJobName()
            == 'job-name'
        )

        job_generator.index = 9
        job_generator.job_name_format = '%(index)02d-%(id)s'
        assert (
            job_generator.GetJobName()
            == '09-job-name'
        )

        job_generator.stream_name = 'ETK'
        job_generator.job_name_format = '%(stream_name)s__%(index)02d-%(id)s'
        assert (
            job_generator.GetJobName()
            == 'ETK__09-job-name'
        )

        job_generator.dist = '12.0-win32'
        job_generator.job_name_format = '%(stream_name)s__%(dist)s__%(index)02d-%(id)s'
        assert (
            job_generator.GetJobName()
            == 'ETK__12.0-win32__09-job-name'
        )
