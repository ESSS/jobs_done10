from ben10.foundation.string import Dedent
from jobs_done10.builders.jenkins import JenkinsJobBuilder
from jobs_done10.jobs_done_file import JobsDoneFile
from jobs_done10.job_builder import JobBuilderConfigurator
from jobs_done10.repository import Repository
import pytest
import functools



#===================================================================================================
# Test
#===================================================================================================
class Test(object):

    #===============================================================================================
    # Setup for common results in all tests
    #===============================================================================================
    # Baseline expected YAML. All tests are compared against this baseline, this way each test only
    # has to verify what is expected to be different, this way, if the baseline is changed, we don't
    # have to fix all tests.
    BASIC_EXPECTED_YAML = Dedent(
        '''
        - job-template:
            name: "fake-master"
            node: "fake"
            scm:
            - git:
                url: "http://fake.git"
                basedir: "fake"
                wipe-workspace: false
                branches:
                - "master"
            logrotate:
                daysToKeep: 7
                numToKeep: 16
                artifactDaysToKeep: -1
                artifactNumToKeep: -1

        - project:
            name: fake-master
            jobs:
            - "fake-master"


        '''
    )


    def testEmpty(self):
        '''
        Tests the most basic YAML possible (created from no ci_contents at all)

        If this test fails, tests marked with @_SkipIfFailTestEmpty will be skipped.
        '''
        self._DoTest(ci_contents='', expected_diff='')


    def _SkipIfFailTestEmpty(original_test):  # @NoSelf
        '''
        Decorator that skips tests if self.testEmpty fails.

        This is useful because if a change is made to the most basic YAML possible (created from
        no ci_contents at all), all tests would fail, polluting the output.

        Fixing testEmpty should make other tests run again.
        '''
        @functools.wraps(original_test)
        def testFunc(self, *args, **kwargs):
            try:
                self.testEmpty()
            except:
                pytest.skip('Skipping until testEmpty is fixed.')
                return
            return original_test(self, *args, **kwargs)

        return testFunc


    #===============================================================================================
    # Tests
    #===============================================================================================
    @_SkipIfFailTestEmpty
    def testParameters(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                parameters:
                  - choice:
                      name: "PARAM"
                      choices:
                      - "choice_1"
                      - "choice_2"
                      description: "Description"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +    parameters:
                +    - choice:
                +        choices:
                +        - choice_1
                +        - choice_2
                +        description: Description
                +        name: PARAM
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testJUnitPatterns(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                junit_patterns:
                - "junit*.xml"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +    publishers:
                +    - xunit:
                +        thresholds:
                +        - failed:
                +            unstable: '0'
                +            unstablenew: '0'
                +        types:
                +        - junit:
                +            pattern: junit*.xml
                +            requireupdate: 'false'
                +            stoponerror: 'false'
                '''
            ),

        )

    @_SkipIfFailTestEmpty
    def testMulitpleTestResults(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                junit_patterns:
                - "junit*.xml"

                boosttest_patterns:
                - "boosttest*.xml"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +    publishers:
                +    - xunit:
                +        thresholds:
                +        - failed:
                +            unstable: '0'
                +            unstablenew: '0'
                +        types:
                +        - junit:
                +            pattern: junit*.xml
                +            requireupdate: 'false'
                +            stoponerror: 'false'
                +        - boosttest:
                +            pattern: boosttest*.xml
                +            requireupdate: 'false'
                +            stoponerror: 'false'
                '''
            ),

        )


    @_SkipIfFailTestEmpty
    def testBuildBatchCommand(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                build_batch_command: my_command
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +    builders:
                +    - batch: my_command
                '''
            ),

        )

        self._DoTest(
            ci_contents=Dedent(
                '''
                build_batch_command: |
                  multi_line
                  command
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +    builders:
                +    - batch: 'multi_line
                +%s
                +        command'
                ''' % '    '
            ),

        )


    @_SkipIfFailTestEmpty
    def testDescriptionSetter(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                description_regex: "JENKINS DESCRIPTION: (.*)"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +    publishers:
                +    - descriptionsetter:
                +        regexp: 'JENKINS DESCRIPTION: (.*)'
                '''
            ),

        )


    @_SkipIfFailTestEmpty
    def testVariables(self):
        ci_contents = Dedent(
            '''
            planet:
            - earth
            - mars

            moon:
            - europa
            '''
        )
        repository = Repository(url='http://fake.git')

        # This test should create two jobs_done_files from their variations
        jobs_done_files = JobsDoneFile.CreateFromYAML(ci_contents)

        builder = JenkinsJobBuilder()
        for jd_file in jobs_done_files:
            JobBuilderConfigurator.Configure(builder, jd_file, repository)
            obtained_yaml = builder.Build()

            if jd_file.variation['planet'] == 'earth':
                self._AssertDiff(
                    obtained_yaml,
                    Dedent(
                        '''
                        @@ @@
                        -    name: "fake-master"
                        -    node: "fake"
                        +    name: "fake-master-europa-earth"
                        +    node: "fake-europa-earth"
                        @@ @@
                        -    - "fake-master"
                        +    - "fake-master-europa-earth"
                        '''
                    )
                )
            else:
                self._AssertDiff(
                    obtained_yaml,
                    Dedent(
                        '''
                        @@ @@
                        -    name: "fake-master"
                        -    node: "fake"
                        +    name: "fake-master-europa-mars"
                        +    node: "fake-europa-mars"
                        @@ @@
                        -    - "fake-master"
                        +    - "fake-master-europa-mars"
                        '''
                    )
                )

    def testCreateFromConfigFile(self):
        from jobs_done10.builders.jenkins import JenkinsJobBuilderToUrl
        builder = JenkinsJobBuilderToUrl.CreateFromConfigFile(config_file_contents=Dedent(
            '''
            jenkins_url: my_url
            '''
        ))

        assert builder.url == 'my_url'
        assert builder.username == None
        assert builder.password == None


        builder = JenkinsJobBuilderToUrl.CreateFromConfigFile(config_file_contents=Dedent(
            '''
            jenkins_url: my_url
            jenkins_username: my_username
            jenkins_password: my_password
            '''
        ))

        assert builder.url == 'my_url'
        assert builder.username == 'my_username'
        assert builder.password == 'my_password'



    def _DoTest(self, ci_contents, expected_diff):
        '''
        :param str ci_contents:
            Contents of JobsDoneFile used for this test

        :param str expected_diff:
            Expected diff from build jobs from `ci_contents`, when compared to BASIC_EXPECTED_YAML.
        '''
        repository = Repository(url='http://fake.git')
        jobs_done_files = JobsDoneFile.CreateFromYAML(ci_contents)

        builder = JenkinsJobBuilder()
        JobBuilderConfigurator.Configure(builder, jobs_done_files[0], repository)
        obtained_yaml = builder.Build()

        self._AssertDiff(obtained_yaml, expected_diff)


    def _AssertDiff(self, obtained_yaml, expected_diff):
        import difflib

        diff = ''.join(difflib.unified_diff(
            self.BASIC_EXPECTED_YAML.splitlines(1),
            str(obtained_yaml).splitlines(1),
            n=0,
        ))
        diff = '\n'.join(diff.splitlines()[2:])
        import re
        diff = re.sub('@@.*@@', '@@ @@', diff, flags=re.MULTILINE)

        assert expected_diff == diff
