from pyjenkins import JenkinsJobGenerator
import os
# from sharedscripts10.res_loader import ResourceLoaderByFiles
# from sharedscripts10.shared_script import SharedScript, SharedScriptContext



#===================================================================================================
# Test
#===================================================================================================
class Test:

    def testCreateJobDirectory(self, embed_data):
        assert os.path.isfile(embed_data['job-name/config.xml']) == False
        assert os.path.isdir(embed_data['job-name']) == False

        job_generator = JenkinsJobGenerator('job-stream', 'job-name')
        job_generator.CreateJobDirectory(embed_data.GetDataDirectory())

        assert os.path.isdir(embed_data['job-name']) == True
        assert os.path.isfile(embed_data['job-name/config.xml']) == True


    def testCreateJobDirectoryReindex(self, embed_data):
        assert os.path.isfile(embed_data['02-job-name/config.xml']) == False

        assert os.path.isdir(embed_data['01-job-name']) == False
        assert os.path.isdir(embed_data['02-job-name']) == False

        job_generator = JenkinsJobGenerator('job-stream', 'job-name')
        job_generator.job_name_format = '%(index)02d-%(id)s'
        job_generator.index = 1
        job_generator.CreateJobDirectory(embed_data.GetDataDirectory(), reindex=True)

        assert os.path.isdir(embed_data['01-job-name']) == True
        assert os.path.isdir(embed_data['02-job-name']) == False

        # Reindex works only with reindex_directory set.
        job_generator.index = 2
        job_generator.CreateJobDirectory(
            embed_data.GetDataDirectory(),
            reindex=True,
            reindex_directory=embed_data['01-job-name']
        )

        assert not os.path.isdir(embed_data['01-job-name'])
        assert os.path.isdir(embed_data['02-job-name'])


    def testCreateConfigFile(self, embed_data):
        config_filename = embed_data['testCreateConfigFile.xml']

        assert os.path.isfile(config_filename) == False

        job_generator = JenkinsJobGenerator('job-stream', 'job-name')
        job_generator.CreateConfigFile(config_filename)

        assert os.path.isfile(config_filename) == True

        expected_config_filename = embed_data['testCreateConfigFile.expected.xml']
        embed_data.AssertEqualFiles(config_filename, expected_config_filename)


    def testGetJobName(self):
        job_generator = JenkinsJobGenerator('job-stream', 'job-name')
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
