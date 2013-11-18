from ben10.filesystem import ListFiles
from ben10.foundation.string import Dedent
from jobs_done10.actions import BuildJobsFromFiles
from jobs_done10.builders.jenkins import JenkinsJobBuilderToOutputDirectory
from jobs_done10.repository import Repository



#===================================================================================================
# Test
#===================================================================================================
class Test(object):


    def testBuildJobsFromFiles(self, embed_data):
        '''
        Integration test for JenkinsJobBuilderToOutputDirectory
        '''
        jobs_done_file_contents = Dedent(
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

            moons:
            - europa
            '''
        )

        repository = Repository(url='http://project.git', branch='branch')
        builder = JenkinsJobBuilderToOutputDirectory(embed_data['.'])

        BuildJobsFromFiles(
            builder,
            repository,
            [jobs_done_file_contents]
        )

        assert ListFiles(embed_data['.']) == \
            ['project-branch-europa-mercury', 'project-branch-europa-venus']
