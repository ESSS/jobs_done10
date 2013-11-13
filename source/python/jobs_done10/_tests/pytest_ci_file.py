from ben10.foundation.string import Dedent
from jobs_done10.ci_file import CIFile, UnknownCIFileOption
import pytest



#===================================================================================================
# Test
#===================================================================================================
class Test(object):

    def testCreateCIFileFromYAML(self):
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
        ci_file = CIFile.CreateFromYAML(ci_contents)

        assert ci_file.junit_patterns == ['junit*.xml']
        assert ci_file.boosttest_patterns == ['cpptest*.xml']
        assert ci_file.build_batch_command == 'command'
        assert ci_file.parameters == [{
            'choice' : {
                'name': 'PARAM',
                'choices': ['choice_1', 'choice_2'],
                'description': 'Description',
            }
        }]

        assert ci_file.variables == {
            'planets' : ['mercury', 'venus'],
            'moons' : ['europa']
        }


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
        CIFile.CreateFromYAML(ci_contents)

        # Unknown options with a single value should fail
        ci_contents = Dedent(
            '''
            moon: europa
            '''
        )
        with pytest.raises(UnknownCIFileOption) as e:
            CIFile.CreateFromYAML(ci_contents)

        assert e.value.option_name == 'moon'
