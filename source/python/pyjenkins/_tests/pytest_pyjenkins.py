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
