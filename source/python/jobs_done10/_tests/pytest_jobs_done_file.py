from ben10.foundation.string import Dedent
from jobs_done10.jobs_done_file import (JobsDoneFile, UnknownJobsDoneFileOption,
    JobsDoneFileTypeError)
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

            build_batch_commands:
            - "command"

            matrix:
              planet:
              - mercury
              - venus

              moon:
              - europa
            '''
        )
        jobs_done_files = JobsDoneFile.CreateFromYAML(ci_contents)

        # Two possible variations (mercury-europa and venus-europa)
        assert len(jobs_done_files) == 2

        def CheckCommonValues(jobs_done_file):
            assert jobs_done_file.matrix == {'moon': ['europa'], 'planet': ['mercury', 'venus']}
            assert jobs_done_file.junit_patterns == ['junit*.xml']
            assert jobs_done_file.boosttest_patterns == ['cpptest*.xml']
            assert jobs_done_file.build_batch_commands == ['command']
            assert jobs_done_file.parameters == [{
                'choice' : {
                    'name': 'PARAM',
                    'choices': ['choice_1', 'choice_2'],
                    'description': 'Description',
                }
            }]

        CheckCommonValues(jobs_done_files[0])
        CheckCommonValues(jobs_done_files[1])

        # Cant determine order of jobs, but these must be the possible matrix rows
        matrix_row_0 = jobs_done_files[0].matrix_row
        matrix_row_1 = jobs_done_files[1].matrix_row
        expected_matrixes = [{'moon': 'europa', 'planet': 'mercury'}, {'moon': 'europa', 'planet': 'venus'}]
        assert [matrix_row_0, matrix_row_1] == expected_matrixes \
            or \
               [matrix_row_1, matrix_row_0] == expected_matrixes \


    def testCreateJobsDoneFileFromYAMLWithConditions(self):
        ci_contents = Dedent(
            '''
            platform-windows:junit_patterns:
            - "junit*.xml"

            platform-linux:build_shell_commands:
            - "{platform} command"

            platform-windows:build_batch_commands:
            - "{platform} command"

            matrix:
                platform:
                - linux
                - windows
            '''
        )
        for jd_file in JobsDoneFile.CreateFromYAML(ci_contents):
            if jd_file.matrix_row['platform'] == 'linux':
                assert jd_file.junit_patterns == None
                assert jd_file.build_batch_commands == None
                assert jd_file.build_shell_commands == ['linux command']
            else:
                assert jd_file.junit_patterns == ['junit*.xml']
                assert jd_file.build_batch_commands == ['windows command']
                assert jd_file.build_shell_commands == None


    def testUnknownOption(self):
        # Unknown options should fail
        ci_contents = Dedent(
            '''
            moon: europa
            '''
        )
        with pytest.raises(UnknownJobsDoneFileOption) as e:
            JobsDoneFile.CreateFromYAML(ci_contents)

        assert e.value.option_name == 'moon'


    def testTypeChecking(self):
        # List is the correct type for build_batch_commands
        ci_contents = Dedent(
            '''
            build_batch_commands:
            - "list item 1"
            '''
        )
        JobsDoneFile.CreateFromYAML(ci_contents)

        # Trying to set a different value, should raise an error
        ci_contents = Dedent(
            '''
            build_batch_commands: "string item"
            '''
        )
        with pytest.raises(JobsDoneFileTypeError) as e:
            JobsDoneFile.CreateFromYAML(ci_contents)

        assert e.value.option_name == 'build_batch_commands'
        assert e.value.expected_type == JobsDoneFile.PARSED_OPTIONS['build_batch_commands']
        assert e.value.obtained_type == str
