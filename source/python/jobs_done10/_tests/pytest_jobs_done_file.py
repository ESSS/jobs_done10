from ben10.foundation.string import Dedent
from jobs_done10.jobs_done_file import JobsDoneFile, UnknownJobsDoneFileOption
import pytest



#===================================================================================================
# Test
#===================================================================================================
class Test(object):

    def testCreateJobsDoneFileFromYAML(self):
        ci_contents = Dedent(
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
        jobs_done_files = JobsDoneFile.CreateFromYAML(ci_contents)

        # Two possible variations (mercury-europa and venus-europa)
        assert len(jobs_done_files) == 2

        # In this case, they are both the same
        for jobs_done_file in jobs_done_files:
            assert jobs_done_file.junit_patterns == ['junit*.xml']
            assert jobs_done_file.boosttest_patterns == ['cpptest*.xml']
            assert jobs_done_file.build_batch_command == 'command'
            assert jobs_done_file.parameters == [{
                'choice' : {
                    'name': 'PARAM',
                    'choices': ['choice_1', 'choice_2'],
                    'description': 'Description',
                }
            }]


    def testCreateJobsDoneFileFromYAMLWithConditions(self):
        ci_contents = Dedent(
            '''
            platform-windows:junit_patterns:
            - "junit*.xml"

            platform-linux:build_shell_command: "{platform} command"
            platform-windows:build_batch_command: "{platform} command"

            platform:
            - linux
            - windows
            '''
        )
        for jd_file in JobsDoneFile.CreateFromYAML(ci_contents):
            if jd_file.variation['platform'] == 'linux':
                assert jd_file.junit_patterns == None
                assert jd_file.build_batch_command == None
                assert jd_file.build_shell_command == 'linux command'
            else:
                assert jd_file.junit_patterns == ['junit*.xml']
                assert jd_file.build_batch_command == 'windows command'
                assert jd_file.build_shell_command == None


    def testUnknownOption(self):
        # Variables are fine (anything unknown which is a list, even if it only has one value)
        ci_contents = Dedent(
            '''
            planets:
            - mercury
            - venus

            moons:
            - europa
            '''
        )
        JobsDoneFile.CreateFromYAML(ci_contents)

        # Unknown options with a single value should fail
        ci_contents = Dedent(
            '''
            moon: europa
            '''
        )
        with pytest.raises(UnknownJobsDoneFileOption) as e:
            JobsDoneFile.CreateFromYAML(ci_contents)

        assert e.value.option_name == 'moon'
