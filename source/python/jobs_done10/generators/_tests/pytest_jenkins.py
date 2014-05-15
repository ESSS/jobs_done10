from ben10.filesystem import CreateDirectory, CreateFile, GetFileContents, ListFiles
from ben10.foundation.string import Dedent
from gitit.git import Git
from jobs_done10.generators.jenkins import (GetJobsFromDirectory, GetJobsFromFile, JenkinsJob,
    JenkinsJobPublisher, JenkinsXmlJobGenerator, UploadJobsFromFile)
from jobs_done10.job_generator import JobGeneratorConfigurator
from jobs_done10.jobs_done_job import JOBS_DONE_FILENAME, JobsDoneJob
from jobs_done10.repository import Repository
import difflib
import functools
import jenkins
import os
import pytest
import re



#===================================================================================================
# TestJenkinsXmlJobGenerator
#===================================================================================================
class TestJenkinsXmlJobGenerator(object):

    #===============================================================================================
    # Setup for common results in all tests
    #===============================================================================================
    # Baseline expected XML. All tests are compared against this baseline, this way each test only
    # has to verify what is expected to be different, this way, if the baseline is changed, we don't
    # have to fix all tests.
    BASIC_EXPECTED_XML = Dedent(
        '''
        <?xml version="1.0" ?>
        <project>
          <actions/>
          <description>&lt;!-- Managed by Job's Done --&gt;</description>
          <keepDependencies>false</keepDependencies>
          <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
          <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
          <concurrentBuild>false</concurrentBuild>
          <assignedNode>fake</assignedNode>
          <canRoam>false</canRoam>
          <logRotator>
            <daysToKeep>7</daysToKeep>
            <numToKeep>-1</numToKeep>
            <artifactDaysToKeep>-1</artifactDaysToKeep>
            <artifactNumToKeep>-1</artifactNumToKeep>
          </logRotator>
          <scm class="hudson.plugins.git.GitSCM">
            <configVersion>2</configVersion>
            <userRemoteConfigs>
              <hudson.plugins.git.UserRemoteConfig>
                <name>origin</name>
                <refspec>+refs/heads/*:refs/remotes/origin/*</refspec>
                <url>http://fake.git</url>
              </hudson.plugins.git.UserRemoteConfig>
            </userRemoteConfigs>
            <branches>
              <hudson.plugins.git.BranchSpec>
                <name>not_master</name>
              </hudson.plugins.git.BranchSpec>
            </branches>
            <relativeTargetDir>fake</relativeTargetDir>
            <extensions>
              <hudson.plugins.git.extensions.impl.LocalBranch>
                <localBranch>not_master</localBranch>
              </hudson.plugins.git.extensions.impl.LocalBranch>
            </extensions>
            <localBranch>not_master</localBranch>
          </scm>
          <builders/>
          <publishers/>
          <buildWrappers/>
          <triggers/>
        </project>
        ''',
        ignore_last_linebreak=True
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
            except:  # pragma: no cover
                pytest.skip('Skipping until testEmpty is fixed.')
                return
            return original_test(self, *args, **kwargs)

        return testFunc


    #===============================================================================================
    # Tests
    #===============================================================================================
    @_SkipIfFailTestEmpty
    def testChoiceParameters(self):
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
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.ChoiceParameterDefinition>
                +          <name>PARAM</name>
                +          <description>Description</description>
                +          <choices class="java.util.Arrays$ArrayList">
                +            <a class="string-array">
                +              <string>choice_1</string>
                +              <string>choice_2</string>
                +            </a>
                +          </choices>
                +        </hudson.model.ChoiceParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>
                '''
            ),
        )

    @_SkipIfFailTestEmpty
    def testMultipleChoiceParameters(self):
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
                  - choice:
                      name: "PARAM_2"
                      choices:
                      - "choice_1"
                      - "choice_2"
                      description: "Description"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.ChoiceParameterDefinition>
                +          <name>PARAM</name>
                +          <description>Description</description>
                +          <choices class="java.util.Arrays$ArrayList">
                +            <a class="string-array">
                +              <string>choice_1</string>
                +              <string>choice_2</string>
                +            </a>
                +          </choices>
                +        </hudson.model.ChoiceParameterDefinition>
                +        <hudson.model.ChoiceParameterDefinition>
                +          <name>PARAM_2</name>
                +          <description>Description</description>
                +          <choices class="java.util.Arrays$ArrayList">
                +            <a class="string-array">
                +              <string>choice_1</string>
                +              <string>choice_2</string>
                +            </a>
                +          </choices>
                +        </hudson.model.ChoiceParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testStringParameters(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                parameters:
                  - string:
                      name: "PARAM_VERSION"
                      default: "Default"
                      description: "Description"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.StringParameterDefinition>
                +          <name>PARAM_VERSION</name>
                +          <description>Description</description>
                +          <defaultValue>Default</defaultValue>
                +        </hudson.model.StringParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testMultipleStringParameters(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                parameters:
                  - string:
                      name: "PARAM_VERSION"
                      default: "Default"
                      description: "Description"
                  - string:
                      name: "PARAM_VERSION_2"
                      default: "Default"
                      description: "Description"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.StringParameterDefinition>
                +          <name>PARAM_VERSION</name>
                +          <description>Description</description>
                +          <defaultValue>Default</defaultValue>
                +        </hudson.model.StringParameterDefinition>
                +        <hudson.model.StringParameterDefinition>
                +          <name>PARAM_VERSION_2</name>
                +          <description>Description</description>
                +          <defaultValue>Default</defaultValue>
                +        </hudson.model.StringParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testParametersMaintainOrder(self):
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
                  - string:
                      name: "PARAM_VERSION"
                      default: "Default"
                      description: "Description"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.ChoiceParameterDefinition>
                +          <name>PARAM</name>
                +          <description>Description</description>
                +          <choices class="java.util.Arrays$ArrayList">
                +            <a class="string-array">
                +              <string>choice_1</string>
                +              <string>choice_2</string>
                +            </a>
                +          </choices>
                +        </hudson.model.ChoiceParameterDefinition>
                +        <hudson.model.StringParameterDefinition>
                +          <name>PARAM_VERSION</name>
                +          <description>Description</description>
                +          <defaultValue>Default</defaultValue>
                +        </hudson.model.StringParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>
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
                - "others.xml"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <publishers/>
                +  <publishers>
                +    <xunit>
                +      <types>
                +        <JUnitType>
                +          <pattern>junit*.xml,others.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JUnitType>
                +      </types>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +    </xunit>
                +  </publishers>
                '''
            ),

        )


    @_SkipIfFailTestEmpty
    def testTimeout(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                timeout: 60
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <buildWrappers/>
                +  <buildWrappers>
                +    <hudson.plugins.build__timeout.BuildTimeoutWrapper>
                +      <timeoutMinutes>60</timeoutMinutes>
                +      <failBuild>true</failBuild>
                +    </hudson.plugins.build__timeout.BuildTimeoutWrapper>
                +  </buildWrappers>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testJSUnitPatterns(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                jsunit_patterns:
                - "jsunit*.xml"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <publishers/>
                +  <publishers>
                +    <xunit>
                +      <types>
                +        <JSUnitPluginType>
                +          <pattern>jsunit*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JSUnitPluginType>
                +      </types>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +    </xunit>
                +  </publishers>
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
                -  <publishers/>
                +  <publishers>
                +    <xunit>
                +      <types>
                +        <JUnitType>
                +          <pattern>junit*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JUnitType>
                +        <BoostTestJunitHudsonTestType>
                +          <pattern>boosttest*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </BoostTestJunitHudsonTestType>
                +      </types>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +    </xunit>
                +  </publishers>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testBuildBatchCommand(self):
        # works with a single command
        self._DoTest(
            ci_contents=Dedent(
                '''
                build_batch_commands:
                - my_command
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <builders/>
                +  <builders>
                +    <hudson.tasks.BatchFile>
                +      <command>my_command</command>
                +    </hudson.tasks.BatchFile>
                +  </builders>
                '''
            ),

        )

        # Works with multi line commands
        self._DoTest(
            ci_contents=Dedent(
                '''
                build_batch_commands:
                - |
                  multi_line
                  command
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <builders/>
                +  <builders>
                +    <hudson.tasks.BatchFile>
                +      <command>multi_line
                +command</command>
                +    </hudson.tasks.BatchFile>
                +  </builders>
                '''
            ),

        )

        # Works with multiple commands
        self._DoTest(
            ci_contents=Dedent(
                '''
                build_batch_commands:
                - command_1
                - command_2
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <builders/>
                +  <builders>
                +    <hudson.tasks.BatchFile>
                +      <command>command_1</command>
                +    </hudson.tasks.BatchFile>
                +    <hudson.tasks.BatchFile>
                +      <command>command_2</command>
                +    </hudson.tasks.BatchFile>
                +  </builders>
                '''
            ),

        )


    @_SkipIfFailTestEmpty
    def testBuildShellCommand(self):
        # works with a single command
        self._DoTest(
            ci_contents=Dedent(
                '''
                build_shell_commands:
                - my_command
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <builders/>
                +  <builders>
                +    <hudson.tasks.Shell>
                +      <command>my_command</command>
                +    </hudson.tasks.Shell>
                +  </builders>
                '''
            ),

        )

        # Works with multi line commands
        self._DoTest(
            ci_contents=Dedent(
                '''
                build_shell_commands:
                - |
                  multi_line
                  command
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <builders/>
                +  <builders>
                +    <hudson.tasks.Shell>
                +      <command>multi_line
                +command</command>
                +    </hudson.tasks.Shell>
                +  </builders>
                '''
            ),

        )

        # Works with multiple commands
        self._DoTest(
            ci_contents=Dedent(
                '''
                build_shell_commands:
                - command_1
                - command_2
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <builders/>
                +  <builders>
                +    <hudson.tasks.Shell>
                +      <command>command_1</command>
                +    </hudson.tasks.Shell>
                +    <hudson.tasks.Shell>
                +      <command>command_2</command>
                +    </hudson.tasks.Shell>
                +  </builders>
                '''
            ),

        )


    @_SkipIfFailTestEmpty
    def testDescriptionSetter(self):
        self._DoTest(
            ci_contents=Dedent(
                r'''
                description_regex: "JENKINS DESCRIPTION\\: (.*)"
                '''
            ),
            expected_diff=Dedent(
                r'''
                @@ @@
                -  <publishers/>
                +  <publishers>
                +    <hudson.plugins.descriptionsetter.DescriptionSetterPublisher>
                +      <regexp>JENKINS DESCRIPTION\: (.*)</regexp>
                +      <regexpForFailed>JENKINS DESCRIPTION\: (.*)</regexpForFailed>
                +      <setForMatrix>false</setForMatrix>
                +    </hudson.plugins.descriptionsetter.DescriptionSetterPublisher>
                +  </publishers>
                '''
            ),

        )


    @_SkipIfFailTestEmpty
    def testNotifyStash(self):
        self._DoTest(
            ci_contents=Dedent(
                r'''
                notify_stash:
                  url: stash.com
                  username: user
                  password: pass
                '''
            ),
            expected_diff=Dedent(
                r'''
                @@ @@
                -  <publishers/>
                +  <publishers>
                +    <org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +      <stashServerBaseUrl>stash.com</stashServerBaseUrl>
                +      <stashUserName>user</stashUserName>
                +      <stashUserPassword>pass</stashUserPassword>
                +    </org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +  </publishers>
                '''
            ),

        )


    @_SkipIfFailTestEmpty
    def testNotifyStashServerDefault(self):
        '''
        When given no parameters, use the default Stash configurations set in the Jenkins server
        '''
        self._DoTest(
            ci_contents=Dedent(
                r'''
                notify_stash:
                '''
            ),
            expected_diff=Dedent(
                r'''
                @@ @@
                -  <publishers/>
                +  <publishers>
                +    <org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +      <stashServerBaseUrl></stashServerBaseUrl>
                +      <stashUserName></stashUserName>
                +      <stashUserPassword></stashUserPassword>
                +    </org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +  </publishers>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testNotifyStashIncompleteParameters(self):
        with pytest.raises(ValueError) as e:
            self._DoTest(
                ci_contents=Dedent(
                    r'''
                    notify_stash:
                      url: stash.com
                      password: pass
                    '''
                ),
                expected_diff=None
            )
        assert str(e.value) == 'Must pass "username" when passing "password"'


    @_SkipIfFailTestEmpty
    def testNotifyStashWithTests(self):
        '''
        When we have both notify_stash, and some test pattern, we have to make sure that the output
        jenkins job xml places the notify_stash publisher AFTER the test publisher, otherwise builds
        with failed tests might be reported as successful to Stash
        '''
        self._DoTest(
            ci_contents=Dedent(
                '''
                notify_stash:
                  url: stash.com
                  username: user
                  password: pass

                jsunit_patterns:
                - "jsunit*.xml"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <publishers/>
                +  <publishers>
                +    <xunit>
                +      <types>
                +        <JSUnitPluginType>
                +          <pattern>jsunit*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JSUnitPluginType>
                +      </types>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +    </xunit>
                +    <org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +      <stashServerBaseUrl>stash.com</stashServerBaseUrl>
                +      <stashUserName>user</stashUserName>
                +      <stashUserPassword>pass</stashUserPassword>
                +    </org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +  </publishers>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testMatrix(self):
        ci_contents = Dedent(
            '''
            planet-earth:build_shell_commands:
            - earth_command

            planet-mars:build_shell_commands:
            - mars_command

            matrix:
                planet:
                - earth
                - mars

                moon:
                - europa
            '''
        )
        repository = Repository(url='http://fake.git', branch='not_master')

        # This test should create two jobs based on the given matrix
        jobs_done_jobs = JobsDoneJob.CreateFromYAML(ci_contents, repository)

        job_generator = JenkinsXmlJobGenerator()

        for jd_file in jobs_done_jobs:
            JobGeneratorConfigurator.Configure(job_generator, jd_file)
            jenkins_job = job_generator.GetJob()

            planet = jd_file.matrix_row['planet']

            # Matrix affects the jobs name, but single value rows are left out
            assert jenkins_job.name == 'fake-not_master-%(planet)s' % locals()

            self._AssertDiff(
                jenkins_job.xml,
                Dedent(
                    '''
                    @@ @@
                    -  <assignedNode>fake</assignedNode>
                    +  <assignedNode>fake-%(planet)s</assignedNode>
                    @@ @@
                    -  <builders/>
                    +  <builders>
                    +    <hudson.tasks.Shell>
                    +      <command>%(planet)s_command</command>
                    +    </hudson.tasks.Shell>
                    +  </builders>
                    ''' % locals()
                ),
            )


    @_SkipIfFailTestEmpty
    def testMatrixSingleValueOnly(self):
        ci_contents = Dedent(
            '''
            matrix:
                planet:
                - earth

                moon:
                - europa
            '''
        )
        repository = Repository(url='http://fake.git', branch='not_master')

        # This test should create two jobs based on the given matrix
        jd_file = JobsDoneJob.CreateFromYAML(ci_contents, repository)[0]
        job_generator = JenkinsXmlJobGenerator()

        JobGeneratorConfigurator.Configure(job_generator, jd_file)
        jenkins_job = job_generator.GetJob()

        # Matrix usually affects the jobs name, but single value rows are left out
        assert jenkins_job.name == 'fake-not_master'

        # XML should have no diff too, because single values do not affect label_expression
        self._AssertDiff(jenkins_job.xml, '')


    @_SkipIfFailTestEmpty
    def testDisplayName(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                display_name: "{name}-{branch}"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                +  <displayName>fake-not_master</displayName>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testLabelExpression(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                label_expression: "win32&&dist-12.0"
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <assignedNode>fake</assignedNode>
                +  <assignedNode>win32&amp;&amp;dist-12.0</assignedNode>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testCron(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                cron: |
                       # Everyday at 22 pm
                       0 22 * * *
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <triggers/>
                +  <triggers>
                +    <hudson.triggers.TimerTrigger>
                +      <spec># Everyday at 22 pm
                +0 22 * * *</spec>
                +    </hudson.triggers.TimerTrigger>
                +  </triggers>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testSCMPoll(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                scm_poll: |
                       # Everyday at 22 pm
                       0 22 * * *
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <triggers/>
                +  <triggers>
                +    <hudson.triggers.SCMTrigger>
                +      <spec># Everyday at 22 pm
                +0 22 * * *</spec>
                +    </hudson.triggers.SCMTrigger>
                +  </triggers>
                '''
            ),
        )


    @_SkipIfFailTestEmpty
    def testMultipleSCMs(self):
        self._DoTest(
            ci_contents=Dedent(
                '''
                additional_scms:
                - git:
                    url: http://some_url.git
                    branch: my_branch
                '''
            ),
            expected_diff=Dedent(
                '''
                @@ @@
                -  <scm class="hudson.plugins.git.GitSCM">
                -    <configVersion>2</configVersion>
                -    <userRemoteConfigs>
                -      <hudson.plugins.git.UserRemoteConfig>
                -        <name>origin</name>
                -        <refspec>+refs/heads/*:refs/remotes/origin/*</refspec>
                -        <url>http://fake.git</url>
                -      </hudson.plugins.git.UserRemoteConfig>
                -    </userRemoteConfigs>
                -    <branches>
                -      <hudson.plugins.git.BranchSpec>
                -        <name>not_master</name>
                -      </hudson.plugins.git.BranchSpec>
                -    </branches>
                -    <relativeTargetDir>fake</relativeTargetDir>
                -    <extensions>
                -      <hudson.plugins.git.extensions.impl.LocalBranch>
                +  <scm class="org.jenkinsci.plugins.multiplescms.MultiSCM">
                +    <scms>
                +      <hudson.plugins.git.GitSCM>
                +        <configVersion>2</configVersion>
                +        <userRemoteConfigs>
                +          <hudson.plugins.git.UserRemoteConfig>
                +            <name>origin</name>
                +            <refspec>+refs/heads/*:refs/remotes/origin/*</refspec>
                +            <url>http://fake.git</url>
                +          </hudson.plugins.git.UserRemoteConfig>
                +        </userRemoteConfigs>
                +        <branches>
                +          <hudson.plugins.git.BranchSpec>
                +            <name>not_master</name>
                +          </hudson.plugins.git.BranchSpec>
                +        </branches>
                +        <relativeTargetDir>fake</relativeTargetDir>
                +        <extensions>
                +          <hudson.plugins.git.extensions.impl.LocalBranch>
                +            <localBranch>not_master</localBranch>
                +          </hudson.plugins.git.extensions.impl.LocalBranch>
                +        </extensions>
                @@ @@
                -      </hudson.plugins.git.extensions.impl.LocalBranch>
                -    </extensions>
                -    <localBranch>not_master</localBranch>
                +      </hudson.plugins.git.GitSCM>
                +      <hudson.plugins.git.GitSCM>
                +        <configVersion>2</configVersion>
                +        <userRemoteConfigs>
                +          <hudson.plugins.git.UserRemoteConfig>
                +            <name>origin</name>
                +            <refspec>+refs/heads/*:refs/remotes/origin/*</refspec>
                +            <url>http://some_url.git</url>
                +          </hudson.plugins.git.UserRemoteConfig>
                +        </userRemoteConfigs>
                +        <branches>
                +          <hudson.plugins.git.BranchSpec>
                +            <name>my_branch</name>
                +          </hudson.plugins.git.BranchSpec>
                +        </branches>
                +        <relativeTargetDir>some_url</relativeTargetDir>
                +        <extensions>
                +          <hudson.plugins.git.extensions.impl.LocalBranch>
                +            <localBranch>my_branch</localBranch>
                +          </hudson.plugins.git.extensions.impl.LocalBranch>
                +        </extensions>
                +        <localBranch>my_branch</localBranch>
                +      </hudson.plugins.git.GitSCM>
                +    </scms>
                '''
            ),
        )


    def _DoTest(self, ci_contents, expected_diff):
        '''
        :param str ci_contents:
            Contents of JobsDoneJob used for this test

        :param str expected_diff:
            Expected diff from build jobs from `ci_contents`, when compared to BASIC_EXPECTED_XML.
        '''
        repository = Repository(url='http://fake.git', branch='not_master')
        jobs_done_jobs = JobsDoneJob.CreateFromYAML(ci_contents, repository)

        job_generator = JenkinsXmlJobGenerator()
        JobGeneratorConfigurator.Configure(job_generator, jobs_done_jobs[0])
        jenkins_job = job_generator.GetJob()

        self._AssertDiff(jenkins_job.xml, expected_diff)


    def _AssertDiff(self, obtained_xml, expected_diff):
        diff = ''.join(difflib.unified_diff(
            self.BASIC_EXPECTED_XML.splitlines(1),
            str(obtained_xml).splitlines(1),
            n=0,
        ))
        diff = '\n'.join(diff.splitlines()[2:])
        diff = re.sub('@@.*@@', '@@ @@', diff, flags=re.MULTILINE)

        print diff
        assert expected_diff == diff



#===================================================================================================
# TestJenkinsActions
#===================================================================================================
class TestJenkinsActions(object):
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

        build_batch_commands:
        - "command"

        matrix:
            planet:
            - mercury
            - venus
            - jupiter

        '''
    )

    _REPOSITORY = Repository(url='http://space.git', branch='branch')

    def testGetJobsFromFile(self, embed_data):
        jobs = GetJobsFromFile(self._REPOSITORY, self._JOBS_DONE_FILE_CONTENTS)
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
        git.Commit(repo_path, 'First commit')

        # If there is no jobs_done file, we should get zero jobs
        _repository, jobs = GetJobsFromDirectory(repo_path)
        assert len(jobs) == 0

        # Create jobs_done file
        CreateFile(os.path.join(repo_path, JOBS_DONE_FILENAME), self._JOBS_DONE_FILE_CONTENTS)
        git.Add(repo_path, '.')
        git.Commit(repo_path, 'Added jobs_done file')

        _repository, jobs = GetJobsFromDirectory(repo_path)
        assert len(jobs) == 3


    def testUploadJobsFromFile(self, monkeypatch):
        '''
        Tests that UploadJobsFromFile correctly calls JenkinsJobPublisher (already tested elsewhere)
        '''
        def MockPublishToUrl(self, url, username, password):
            assert url == 'jenkins_url'
            assert username == 'jenkins_user'
            assert password == 'jenkins_pass'

            assert set(self.jobs.keys()) == set([
                'space-branch-venus', 'space-branch-jupiter', 'space-branch-mercury'])

            return 'mock publish result'

        monkeypatch.setattr(JenkinsJobPublisher, 'PublishToUrl', MockPublishToUrl)

        result = UploadJobsFromFile(
            repository=self._REPOSITORY,
            jobs_done_file_contents=self._JOBS_DONE_FILE_CONTENTS,
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert result == 'mock publish result'



#===================================================================================================
# TestJenkinsPublisher
#===================================================================================================
class TestJenkinsPublisher(object):

    def testPublishToDirectory(self, embed_data):
        self._GetPublisher().PublishToDirectory(embed_data['.'])

        assert set(ListFiles(embed_data['.'])) == set([
            'space-milky_way-jupiter', 'space-milky_way-mercury', 'space-milky_way-venus'])

        assert GetFileContents(embed_data['space-milky_way-jupiter']) == 'jupiter'
        assert GetFileContents(embed_data['space-milky_way-mercury']) == 'mercury'
        assert GetFileContents(embed_data['space-milky_way-venus']) == 'venus'


    def testPublishToUrl(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        new_jobs, updated_jobs, deleted_jobs = self._GetPublisher().PublishToUrl(
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == set(['space-milky_way-venus', 'space-milky_way-jupiter'])
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == set(['space-milky_way-mercury'])
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == set(['space-milky_way-saturn'])


    def testPublishToUrl2(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        publisher = self._GetPublisher()
        publisher.jobs = {}

        new_jobs, updated_jobs, deleted_jobs = publisher.PublishToUrl(
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == set()
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == set()
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == set(['space-milky_way-mercury', 'space-milky_way-saturn'])


    def _GetPublisher(self):
        repository = Repository(url='http://server/space.git', branch='milky_way')
        jobs = [
            JenkinsJob(name='space-milky_way-jupiter', xml='jupiter', repository=repository),
            JenkinsJob(name='space-milky_way-mercury', xml='mercury', repository=repository),
            JenkinsJob(name='space-milky_way-venus', xml='venus', repository=repository),
        ]

        return JenkinsJobPublisher(repository, jobs)


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
                    {'name' : u'space-milky_way-mercury'},
                    {'name' : u'space-milky_way-saturn'},
                ]

            def get_job_config(self, job_name):
                # Test with single, and multiple scms
                if job_name == 'space-milky_way-mercury':
                    return Dedent(
                        '''
                        <project>
                          <scm>
                            <userRemoteConfigs>
                              <hudson.plugins.git.UserRemoteConfig>
                                <url>
                                  http://server/space.git
                                </url>
                              </hudson.plugins.git.UserRemoteConfig>
                            </userRemoteConfigs>
                            <branches>
                              <hudson.plugins.git.BranchSpec>
                                <name>milky_way</name>
                              </hudson.plugins.git.BranchSpec>
                            </branches>
                          </scm>
                        </project>
                        '''
                    )
                elif job_name == 'space-milky_way-saturn':
                    return Dedent(
                        '''
                        <project>
                          <scm>
                            <scms>
                              <!-- One of the SCMs is the one for space -->
                              <hudson.plugins.git.GitSCM>
                                <userRemoteConfigs>
                                  <hudson.plugins.git.UserRemoteConfig>
                                    <url>
                                      http://server/space.git
                                    </url>
                                  </hudson.plugins.git.UserRemoteConfig>
                                </userRemoteConfigs>
                                <branches>
                                  <hudson.plugins.git.BranchSpec>
                                    <name>milky_way</name>
                                  </hudson.plugins.git.BranchSpec>
                                </branches>
                              </hudson.plugins.git.GitSCM>

                              <!-- But a job might have multiple SCMs, we don't care about those -->
                              <hudson.plugins.git.GitSCM>
                                <userRemoteConfigs>
                                  <hudson.plugins.git.UserRemoteConfig>
                                    <url>
                                      http://server/space_dependencie.git
                                    </url>
                                  </hudson.plugins.git.UserRemoteConfig>
                                </userRemoteConfigs>
                                <branches>
                                  <hudson.plugins.git.BranchSpec>
                                    <name>other_branch</name>
                                  </hudson.plugins.git.BranchSpec>
                                </branches>
                              </hudson.plugins.git.GitSCM>
                            </scms>
                          </scm>
                        </project>
                        '''
                    )

            def create_job(self, name, xml):
                self.NEW_JOBS.add(name)

            def reconfig_job(self, name, xml):
                self.UPDATED_JOBS.add(name)

            def delete_job(self, name):
                self.DELETED_JOBS.add(name)


        monkeypatch.setattr(jenkins, 'Jenkins', MockJenkins)

        return MockJenkins
