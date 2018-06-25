

import difflib
import os
import re
from subprocess import check_call
from textwrap import dedent

import jenkins
import pytest
from jobs_done10.generators.jenkins import (
    GetJobsFromDirectory, GetJobsFromFile, JenkinsJob, JenkinsJobPublisher, JenkinsXmlJobGenerator,
    UploadJobsFromFile)
from jobs_done10.job_generator import JobGeneratorConfigurator
from jobs_done10.jobs_done_job import JOBS_DONE_FILENAME, JobsDoneFileTypeError, JobsDoneJob
from jobs_done10.repository import Repository


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
    BASIC_EXPECTED_XML = dedent(
        '''\
        <?xml version="1.0" ?>
        <project>
          <description>&lt;!-- Managed by Job's Done --&gt;</description>
          <keepDependencies>false</keepDependencies>
          <logRotator>
            <daysToKeep>7</daysToKeep>
            <numToKeep>-1</numToKeep>
            <artifactDaysToKeep>-1</artifactDaysToKeep>
            <artifactNumToKeep>-1</artifactNumToKeep>
          </logRotator>
          <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
          <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
          <concurrentBuild>false</concurrentBuild>
          <canRoam>false</canRoam>
          <scm class="hudson.plugins.git.GitSCM">
            <configVersion>2</configVersion>
            <relativeTargetDir>fake</relativeTargetDir>
            <userRemoteConfigs>
              <hudson.plugins.git.UserRemoteConfig>
                <url>http://fake.git</url>
              </hudson.plugins.git.UserRemoteConfig>
            </userRemoteConfigs>
            <branches>
              <hudson.plugins.git.BranchSpec>
                <name>not_master</name>
              </hudson.plugins.git.BranchSpec>
            </branches>
            <extensions>
              <hudson.plugins.git.extensions.impl.LocalBranch>
                <localBranch>not_master</localBranch>
              </hudson.plugins.git.extensions.impl.LocalBranch>
              <hudson.plugins.git.extensions.impl.CleanCheckout/>
              <hudson.plugins.git.extensions.impl.GitLFSPull/>
            </extensions>
            <localBranch>not_master</localBranch>
          </scm>
          <assignedNode>fake</assignedNode>
        </project>''',
    )


    #===============================================================================================
    # Tests
    #===============================================================================================
    def testEmpty(self):
        with pytest.raises(ValueError) as e:
            self._DoTest(yaml_contents='', expected_diff=None)
        assert str(e.value) == 'Could not parse anything from .yaml contents'


    def testChoiceParameters(self):
        self._DoTest(
            yaml_contents=dedent(
                '''\
                parameters:
                  - choice:
                      name: "PARAM"
                      choices:
                      - "choice_1"
                      - "choice_2"
                      description: "Description"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.ChoiceParameterDefinition>
                +          <choices class="java.util.Arrays$ArrayList">
                +            <a class="string-array">
                +              <string>choice_1</string>
                +              <string>choice_2</string>
                +            </a>
                +          </choices>
                +          <name>PARAM</name>
                +          <description>Description</description>
                +        </hudson.model.ChoiceParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>'''
            ),
        )

    def testMultipleChoiceParameters(self):
        self._DoTest(
            yaml_contents=dedent(
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
            expected_diff=dedent(
                '''\
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.ChoiceParameterDefinition>
                +          <choices class="java.util.Arrays$ArrayList">
                +            <a class="string-array">
                +              <string>choice_1</string>
                +              <string>choice_2</string>
                +            </a>
                +          </choices>
                +          <name>PARAM</name>
                +          <description>Description</description>
                +        </hudson.model.ChoiceParameterDefinition>
                +        <hudson.model.ChoiceParameterDefinition>
                +          <choices class="java.util.Arrays$ArrayList">
                +            <a class="string-array">
                +              <string>choice_1</string>
                +              <string>choice_2</string>
                +            </a>
                +          </choices>
                +          <name>PARAM_2</name>
                +          <description>Description</description>
                +        </hudson.model.ChoiceParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>'''
            ),
        )


    def testStringParameters(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                parameters:
                  - string:
                      name: "PARAM_VERSION"
                      default: "Default"
                      description: "Description"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.StringParameterDefinition>
                +          <defaultValue>Default</defaultValue>
                +          <name>PARAM_VERSION</name>
                +          <description>Description</description>
                +        </hudson.model.StringParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>'''
            ),
        )


    def testMultipleStringParameters(self):
        self._DoTest(
            yaml_contents=dedent(
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
            expected_diff=dedent(
                '''\
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.StringParameterDefinition>
                +          <defaultValue>Default</defaultValue>
                +          <name>PARAM_VERSION</name>
                +          <description>Description</description>
                +        </hudson.model.StringParameterDefinition>
                +        <hudson.model.StringParameterDefinition>
                +          <defaultValue>Default</defaultValue>
                +          <name>PARAM_VERSION_2</name>
                +          <description>Description</description>
                +        </hudson.model.StringParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>'''
            ),
        )


    def testParametersMaintainOrder(self):
        self._DoTest(
            yaml_contents=dedent(
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
            expected_diff=dedent(
                '''\
                @@ @@
                +  <properties>
                +    <hudson.model.ParametersDefinitionProperty>
                +      <parameterDefinitions>
                +        <hudson.model.ChoiceParameterDefinition>
                +          <choices class="java.util.Arrays$ArrayList">
                +            <a class="string-array">
                +              <string>choice_1</string>
                +              <string>choice_2</string>
                +            </a>
                +          </choices>
                +          <name>PARAM</name>
                +          <description>Description</description>
                +        </hudson.model.ChoiceParameterDefinition>
                +        <hudson.model.StringParameterDefinition>
                +          <defaultValue>Default</defaultValue>
                +          <name>PARAM_VERSION</name>
                +          <description>Description</description>
                +        </hudson.model.StringParameterDefinition>
                +      </parameterDefinitions>
                +    </hudson.model.ParametersDefinitionProperty>
                +  </properties>'''
            ),
        )


    def testJUnitPatterns(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                junit_patterns:
                - "junit*.xml"
                - "others.xml"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <xunit>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +      <types>
                +        <JUnitType>
                +          <pattern>junit*.xml,others.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JUnitType>
                +      </types>
                +    </xunit>
                +  </publishers>
                +  <buildWrappers>
                +    <hudson.plugins.ws__cleanup.PreBuildCleanup>
                +      <patterns>
                +        <hudson.plugins.ws__cleanup.Pattern>
                +          <pattern>junit*.xml</pattern>
                +          <type>INCLUDE</type>
                +        </hudson.plugins.ws__cleanup.Pattern>
                +        <hudson.plugins.ws__cleanup.Pattern>
                +          <pattern>others.xml</pattern>
                +          <type>INCLUDE</type>
                +        </hudson.plugins.ws__cleanup.Pattern>
                +      </patterns>
                +    </hudson.plugins.ws__cleanup.PreBuildCleanup>
                +  </buildWrappers>'''
            ),

        )


    def testTimeoutAbsolute(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                timeout: 60
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <buildWrappers>
                +    <hudson.plugins.build__timeout.BuildTimeoutWrapper>
                +      <timeoutMinutes>60</timeoutMinutes>
                +      <failBuild>true</failBuild>
                +    </hudson.plugins.build__timeout.BuildTimeoutWrapper>
                +  </buildWrappers>'''
            ),
        )


    def testTimeoutNoActivity(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                timeout_no_activity: 600
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <buildWrappers>
                +    <hudson.plugins.build__timeout.BuildTimeoutWrapper>
                +      <strategy class="hudson.plugins.build_timeout.impl.NoActivityTimeOutStrategy">
                +        <timeoutSecondsString>600</timeoutSecondsString>
                +      </strategy>
                +      <operationList>
                +        <hudson.plugins.build__timeout.operations.FailOperation/>
                +      </operationList>
                +    </hudson.plugins.build__timeout.BuildTimeoutWrapper>
                +  </buildWrappers>'''
            ),
        )


    def testCustomWorkspace(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                custom_workspace: workspace/WS
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <customWorkspace>workspace/WS</customWorkspace>'''
            ),
        )

    def testAuthToken(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                auth_token: my_token
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <authToken>my_token</authToken>'''
            ),
        )


    def testBoosttestPatterns(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                boosttest_patterns:
                - "boost*.xml"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <xunit>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +      <types>
                +        <BoostTestJunitHudsonTestType>
                +          <pattern>boost*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </BoostTestJunitHudsonTestType>
                +      </types>
                +    </xunit>
                +  </publishers>
                +  <buildWrappers>
                +    <hudson.plugins.ws__cleanup.PreBuildCleanup>
                +      <patterns>
                +        <hudson.plugins.ws__cleanup.Pattern>
                +          <pattern>boost*.xml</pattern>
                +          <type>INCLUDE</type>
                +        </hudson.plugins.ws__cleanup.Pattern>
                +      </patterns>
                +    </hudson.plugins.ws__cleanup.PreBuildCleanup>
                +  </buildWrappers>'''
            ),
        )


    def testJSUnitPatterns(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                jsunit_patterns:
                - "jsunit*.xml"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <xunit>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +      <types>
                +        <JSUnitPluginType>
                +          <pattern>jsunit*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JSUnitPluginType>
                +      </types>
                +    </xunit>
                +  </publishers>
                +  <buildWrappers>
                +    <hudson.plugins.ws__cleanup.PreBuildCleanup>
                +      <patterns>
                +        <hudson.plugins.ws__cleanup.Pattern>
                +          <pattern>jsunit*.xml</pattern>
                +          <type>INCLUDE</type>
                +        </hudson.plugins.ws__cleanup.Pattern>
                +      </patterns>
                +    </hudson.plugins.ws__cleanup.PreBuildCleanup>
                +  </buildWrappers>'''
            ),
        )


    def testMultipleTestResults(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                junit_patterns:
                - "junit*.xml"

                boosttest_patterns:
                - "boosttest*.xml"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <xunit>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +      <types>
                +        <BoostTestJunitHudsonTestType>
                +          <pattern>boosttest*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </BoostTestJunitHudsonTestType>
                +        <JUnitType>
                +          <pattern>junit*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JUnitType>
                +      </types>
                +    </xunit>
                +  </publishers>
                +  <buildWrappers>
                +    <hudson.plugins.ws__cleanup.PreBuildCleanup>
                +      <patterns>
                +        <hudson.plugins.ws__cleanup.Pattern>
                +          <pattern>boosttest*.xml</pattern>
                +          <type>INCLUDE</type>
                +        </hudson.plugins.ws__cleanup.Pattern>
                +        <hudson.plugins.ws__cleanup.Pattern>
                +          <pattern>junit*.xml</pattern>
                +          <type>INCLUDE</type>
                +        </hudson.plugins.ws__cleanup.Pattern>
                +      </patterns>
                +    </hudson.plugins.ws__cleanup.PreBuildCleanup>
                +  </buildWrappers>'''
            ),
        )


    def testBuildBatchCommand(self):
        # works with a single command
        self._DoTest(
            yaml_contents=dedent(
                '''
                build_batch_commands:
                - my_command
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <builders>
                +    <hudson.tasks.BatchFile>
                +      <command>my_command</command>
                +    </hudson.tasks.BatchFile>
                +  </builders>'''
            ),

        )

        # Works with multi line commands
        self._DoTest(
            yaml_contents=dedent(
                '''
                build_batch_commands:
                - |
                  multi_line
                  command
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <builders>
                +    <hudson.tasks.BatchFile>
                +      <command>multi_line&#xd;
                +command</command>
                +    </hudson.tasks.BatchFile>
                +  </builders>'''
            ),

        )

        # Works with multiple commands
        self._DoTest(
            yaml_contents=dedent(
                '''
                build_batch_commands:
                - command_1
                - command_2
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <builders>
                +    <hudson.tasks.BatchFile>
                +      <command>command_1</command>
                +    </hudson.tasks.BatchFile>
                +    <hudson.tasks.BatchFile>
                +      <command>command_2</command>
                +    </hudson.tasks.BatchFile>
                +  </builders>'''
            ),

        )


    def testBuildPythonCommand(self):
        # works with a single command
        self._DoTest(
            yaml_contents=dedent(
                '''
                build_python_commands:
                - print 'hello'
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <builders>
                +    <hudson.plugins.python.Python>
                +      <command>print 'hello'</command>
                +    </hudson.plugins.python.Python>
                +  </builders>'''
            ),

        )


    def testBuildShellCommand(self):
        # works with a single command
        self._DoTest(
            yaml_contents=dedent(
                '''
                build_shell_commands:
                - my_command
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <builders>
                +    <hudson.tasks.Shell>
                +      <command>my_command</command>
                +    </hudson.tasks.Shell>
                +  </builders>'''
            ),

        )

        # Works with multi line commands
        self._DoTest(
            yaml_contents=dedent(
                '''
                build_shell_commands:
                - |
                  multi_line
                  command
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <builders>
                +    <hudson.tasks.Shell>
                +      <command>multi_line
                +command</command>
                +    </hudson.tasks.Shell>
                +  </builders>'''
            ),

        )

        # Works with multiple commands
        self._DoTest(
            yaml_contents=dedent(
                '''
                build_shell_commands:
                - command_1
                - command_2
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <builders>
                +    <hudson.tasks.Shell>
                +      <command>command_1</command>
                +    </hudson.tasks.Shell>
                +    <hudson.tasks.Shell>
                +      <command>command_2</command>
                +    </hudson.tasks.Shell>
                +  </builders>'''
            ),

        )


    def testDescriptionRegex(self):
        self._DoTest(
            yaml_contents=dedent(
                r'''
                description_regex: "JENKINS DESCRIPTION\\: (.*)"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <hudson.plugins.descriptionsetter.DescriptionSetterPublisher>
                +      <regexp>JENKINS DESCRIPTION\: (.*)</regexp>
                +      <regexpForFailed>JENKINS DESCRIPTION\: (.*)</regexpForFailed>
                +      <setForMatrix>false</setForMatrix>
                +    </hudson.plugins.descriptionsetter.DescriptionSetterPublisher>
                +  </publishers>'''
            ),

        )


    def testNotifyStash(self):
        self._DoTest(
            yaml_contents=dedent(
                r'''
                notify_stash:
                  url: stash.com
                  username: user
                  password: pass
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +      <stashServerBaseUrl>stash.com</stashServerBaseUrl>
                +      <stashUserName>user</stashUserName>
                +      <stashUserPassword>pass</stashUserPassword>
                +    </org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +  </publishers>'''
            ),

        )


    def testNotifyStashServerDefault(self):
        '''
        When given no parameters, use the default Stash configurations set in the Jenkins server
        '''
        self._DoTest(
            yaml_contents=dedent(
                '''
                notify_stash: stash.com
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +      <stashServerBaseUrl>stash.com</stashServerBaseUrl>
                +    </org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +  </publishers>'''
            ),
        )


    def testNotifyStashWithTests(self):
        '''
        When we have both notify_stash, and some test pattern, we have to make sure that the output
        jenkins job xml places the notify_stash publisher AFTER the test publisher, otherwise builds
        with failed tests might be reported as successful to Stash
        '''
        self._DoTest(
            yaml_contents=dedent(
                '''
                notify_stash:
                  url: stash.com
                  username: user
                  password: pass

                jsunit_patterns:
                - "jsunit*.xml"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <xunit>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +      <types>
                +        <JSUnitPluginType>
                +          <pattern>jsunit*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JSUnitPluginType>
                +      </types>
                +    </xunit>
                +    <org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +      <stashServerBaseUrl>stash.com</stashServerBaseUrl>
                +      <stashUserName>user</stashUserName>
                +      <stashUserPassword>pass</stashUserPassword>
                +    </org.jenkinsci.plugins.stashNotifier.StashNotifier>
                +  </publishers>
                +  <buildWrappers>
                +    <hudson.plugins.ws__cleanup.PreBuildCleanup>
                +      <patterns>
                +        <hudson.plugins.ws__cleanup.Pattern>
                +          <pattern>jsunit*.xml</pattern>
                +          <type>INCLUDE</type>
                +        </hudson.plugins.ws__cleanup.Pattern>
                +      </patterns>
                +    </hudson.plugins.ws__cleanup.PreBuildCleanup>
                +  </buildWrappers>'''
            ),
        )


    def testMatrix(self):
        yaml_contents = dedent(
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
        jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository)

        job_generator = JenkinsXmlJobGenerator()

        for jd_file in jobs_done_jobs:
            JobGeneratorConfigurator.Configure(job_generator, jd_file)
            jenkins_job = job_generator.GetJob()

            planet = jd_file.matrix_row['planet']

            # Matrix affects the jobs name, but single value rows are left out
            assert jenkins_job.name == 'fake-not_master-%(planet)s' % locals()

            self._AssertDiff(
                jenkins_job.xml,
                dedent(
                    '''\
                    @@ @@
                    -  <assignedNode>fake</assignedNode>
                    +  <assignedNode>fake-%(planet)s</assignedNode>
                    +  <builders>
                    +    <hudson.tasks.Shell>
                    +      <command>%(planet)s_command</command>
                    +    </hudson.tasks.Shell>
                    +  </builders>''' % locals()
                ),
            )


    def testMatrixSingleValueOnly(self):
        yaml_contents = dedent(
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
        jd_file = JobsDoneJob.CreateFromYAML(yaml_contents, repository)[0]
        job_generator = JenkinsXmlJobGenerator()

        JobGeneratorConfigurator.Configure(job_generator, jd_file)
        jenkins_job = job_generator.GetJob()

        # Matrix usually affects the jobs name, but single value rows are left out
        assert jenkins_job.name == 'fake-not_master'

        # XML should have no diff too, because single values do not affect label_expression
        self._AssertDiff(jenkins_job.xml, '')


    def testDisplayName(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                display_name: "{name}-{branch}"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <displayName>fake-not_master</displayName>'''
            ),
        )


    def testLabelExpression(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                label_expression: "win32&&dist-12.0"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                -  <assignedNode>fake</assignedNode>
                +  <assignedNode>win32&amp;&amp;dist-12.0</assignedNode>'''
            ),
        )


    def testCron(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                cron: |
                       # Everyday at 22 pm
                       0 22 * * *
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <triggers>
                +    <hudson.triggers.TimerTrigger>
                +      <spec># Everyday at 22 pm
                +0 22 * * *</spec>
                +    </hudson.triggers.TimerTrigger>
                +  </triggers>'''
            ),
        )


    def testSCMPoll(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                scm_poll: |
                       # Everyday at 22 pm
                       0 22 * * *
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <triggers>
                +    <hudson.triggers.SCMTrigger>
                +      <spec># Everyday at 22 pm
                +0 22 * * *</spec>
                +    </hudson.triggers.SCMTrigger>
                +  </triggers>'''
            ),
        )


    def testAdditionalRepositories(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                additional_repositories:
                - git:
                    url: http://some_url.git
                    branch: my_branch
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                -  <scm class="hudson.plugins.git.GitSCM">
                -    <configVersion>2</configVersion>
                -    <relativeTargetDir>fake</relativeTargetDir>
                -    <userRemoteConfigs>
                -      <hudson.plugins.git.UserRemoteConfig>
                -        <url>http://fake.git</url>
                -      </hudson.plugins.git.UserRemoteConfig>
                -    </userRemoteConfigs>
                -    <branches>
                -      <hudson.plugins.git.BranchSpec>
                -        <name>not_master</name>
                -      </hudson.plugins.git.BranchSpec>
                -    </branches>
                -    <extensions>
                -      <hudson.plugins.git.extensions.impl.LocalBranch>
                +  <assignedNode>fake</assignedNode>
                +  <scm class="org.jenkinsci.plugins.multiplescms.MultiSCM">
                +    <scms>
                +      <hudson.plugins.git.GitSCM>
                +        <configVersion>2</configVersion>
                +        <relativeTargetDir>fake</relativeTargetDir>
                +        <userRemoteConfigs>
                +          <hudson.plugins.git.UserRemoteConfig>
                +            <url>http://fake.git</url>
                +          </hudson.plugins.git.UserRemoteConfig>
                +        </userRemoteConfigs>
                +        <branches>
                +          <hudson.plugins.git.BranchSpec>
                +            <name>not_master</name>
                +          </hudson.plugins.git.BranchSpec>
                +        </branches>
                +        <extensions>
                +          <hudson.plugins.git.extensions.impl.LocalBranch>
                +            <localBranch>not_master</localBranch>
                +          </hudson.plugins.git.extensions.impl.LocalBranch>
                +          <hudson.plugins.git.extensions.impl.CleanCheckout/>
                +          <hudson.plugins.git.extensions.impl.GitLFSPull/>
                +        </extensions>
                @@ @@
                -      </hudson.plugins.git.extensions.impl.LocalBranch>
                -      <hudson.plugins.git.extensions.impl.CleanCheckout/>
                -      <hudson.plugins.git.extensions.impl.GitLFSPull/>
                -    </extensions>
                -    <localBranch>not_master</localBranch>
                +      </hudson.plugins.git.GitSCM>
                +      <hudson.plugins.git.GitSCM>
                +        <configVersion>2</configVersion>
                +        <relativeTargetDir>some_url</relativeTargetDir>
                +        <userRemoteConfigs>
                +          <hudson.plugins.git.UserRemoteConfig>
                +            <url>http://some_url.git</url>
                +          </hudson.plugins.git.UserRemoteConfig>
                +        </userRemoteConfigs>
                +        <branches>
                +          <hudson.plugins.git.BranchSpec>
                +            <name>my_branch</name>
                +          </hudson.plugins.git.BranchSpec>
                +        </branches>
                +        <extensions>
                +          <hudson.plugins.git.extensions.impl.LocalBranch>
                +            <localBranch>my_branch</localBranch>
                +          </hudson.plugins.git.extensions.impl.LocalBranch>
                +          <hudson.plugins.git.extensions.impl.CleanCheckout/>
                +          <hudson.plugins.git.extensions.impl.GitLFSPull/>
                +        </extensions>
                +        <localBranch>my_branch</localBranch>
                +      </hudson.plugins.git.GitSCM>
                +    </scms>
                @@ @@
                -  <assignedNode>fake</assignedNode>'''
            ),
        )


    def testGitAndAdditionalRepositories(self):
        '''
        Make sure that everything works just fine when we mix 'git' and 'additional_repositories'
        '''
        # We expect the same diff for both orders (git -> additional and additional -> git)
        expected_diff = dedent(
            '''\
            @@ @@
            -  <scm class="hudson.plugins.git.GitSCM">
            -    <configVersion>2</configVersion>
            -    <relativeTargetDir>fake</relativeTargetDir>
            -    <userRemoteConfigs>
            -      <hudson.plugins.git.UserRemoteConfig>
            -        <url>http://fake.git</url>
            -      </hudson.plugins.git.UserRemoteConfig>
            -    </userRemoteConfigs>
            -    <branches>
            -      <hudson.plugins.git.BranchSpec>
            -        <name>not_master</name>
            -      </hudson.plugins.git.BranchSpec>
            -    </branches>
            -    <extensions>
            -      <hudson.plugins.git.extensions.impl.LocalBranch>
            -        <localBranch>not_master</localBranch>
            -      </hudson.plugins.git.extensions.impl.LocalBranch>
            -      <hudson.plugins.git.extensions.impl.CleanCheckout/>
            -      <hudson.plugins.git.extensions.impl.GitLFSPull/>
            -    </extensions>
            -    <localBranch>not_master</localBranch>
            +  <assignedNode>fake</assignedNode>
            +  <scm class="org.jenkinsci.plugins.multiplescms.MultiSCM">
            +    <scms>
            +      <hudson.plugins.git.GitSCM>
            +        <configVersion>2</configVersion>
            +        <relativeTargetDir>fake</relativeTargetDir>
            +        <userRemoteConfigs>
            +          <hudson.plugins.git.UserRemoteConfig>
            +            <url>http://fake.git</url>
            +          </hudson.plugins.git.UserRemoteConfig>
            +        </userRemoteConfigs>
            +        <branches>
            +          <hudson.plugins.git.BranchSpec>
            +            <name>custom_main</name>
            +          </hudson.plugins.git.BranchSpec>
            +        </branches>
            +        <extensions>
            +          <hudson.plugins.git.extensions.impl.LocalBranch>
            +            <localBranch>custom_main</localBranch>
            +          </hudson.plugins.git.extensions.impl.LocalBranch>
            +          <hudson.plugins.git.extensions.impl.CleanCheckout/>
            +          <hudson.plugins.git.extensions.impl.GitLFSPull/>
            +        </extensions>
            +        <localBranch>custom_main</localBranch>
            +      </hudson.plugins.git.GitSCM>
            +      <hudson.plugins.git.GitSCM>
            +        <configVersion>2</configVersion>
            +        <relativeTargetDir>additional</relativeTargetDir>
            +        <userRemoteConfigs>
            +          <hudson.plugins.git.UserRemoteConfig>
            +            <url>http://additional.git</url>
            +          </hudson.plugins.git.UserRemoteConfig>
            +        </userRemoteConfigs>
            +        <branches>
            +          <hudson.plugins.git.BranchSpec>
            +            <name>custom_additional</name>
            +          </hudson.plugins.git.BranchSpec>
            +        </branches>
            +        <extensions>
            +          <hudson.plugins.git.extensions.impl.LocalBranch>
            +            <localBranch>custom_additional</localBranch>
            +          </hudson.plugins.git.extensions.impl.LocalBranch>
            +          <hudson.plugins.git.extensions.impl.CleanCheckout/>
            +          <hudson.plugins.git.extensions.impl.GitLFSPull/>
            +        </extensions>
            +        <localBranch>custom_additional</localBranch>
            +      </hudson.plugins.git.GitSCM>
            +    </scms>
            @@ @@
            -  <assignedNode>fake</assignedNode>'''
        )

        # Test git -> additional
        self._DoTest(
            yaml_contents=dedent(
                '''
                git:
                  branch: custom_main

                additional_repositories:
                - git:
                    url: http://additional.git
                    branch: custom_additional
                '''
            ),
            expected_diff=expected_diff
        )

        # Test additional -> git
        self._DoTest(
            yaml_contents=dedent(
                '''
                additional_repositories:
                - git:
                    url: http://additional.git
                    branch: custom_additional

                git:
                  branch: custom_main
                '''
            ),
            expected_diff=expected_diff
        )


    def testUnknownGitOptions(self):
        with pytest.raises(RuntimeError) as e:
            self._DoTest(
                yaml_contents=dedent(
                    '''
                    git:
                      unknown: ""
                    '''
                ),
                expected_diff=''
            )
        assert str(e.value) == "Received unknown git options: ['unknown']"


    def testGitOptions(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                git:
                  recursive_submodules: true
                  reference: "/home/reference.git"
                  target_dir: "main_application"
                  timeout: 30
                  clean_checkout: false
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                -    <relativeTargetDir>fake</relativeTargetDir>
                +    <relativeTargetDir>main_application</relativeTargetDir>
                @@ @@
                +      <hudson.plugins.git.extensions.impl.SubmoduleOption>
                +        <recursiveSubmodules>true</recursiveSubmodules>
                +      </hudson.plugins.git.extensions.impl.SubmoduleOption>
                +      <hudson.plugins.git.extensions.impl.CloneOption>
                +        <reference>/home/reference.git</reference>
                +        <timeout>30</timeout>
                +      </hudson.plugins.git.extensions.impl.CloneOption>'''
            ),
        )



    def testEmailNotificationDict(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                email_notification:
                  recipients: user@company.com other@company.com
                  notify_every_build: true
                  notify_individuals: true

                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <hudson.tasks.Mailer>
                +      <recipients>user@company.com other@company.com</recipients>
                +      <dontNotifyEveryUnstableBuild>false</dontNotifyEveryUnstableBuild>
                +      <sendToIndividuals>true</sendToIndividuals>
                +    </hudson.tasks.Mailer>
                +  </publishers>'''
            ),
        )

    def testEmailNotificationString(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                email_notification: user@company.com other@company.com
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <hudson.tasks.Mailer>
                +      <recipients>user@company.com other@company.com</recipients>
                +      <dontNotifyEveryUnstableBuild>true</dontNotifyEveryUnstableBuild>
                +      <sendToIndividuals>false</sendToIndividuals>
                +    </hudson.tasks.Mailer>
                +  </publishers>'''
            ),
        )

    def testEmailNotificationWithTests(self):
        '''
        When we have both email_notification, and some test pattern, we have to make sure that the
        output jenkins job xml places the email_notification publisher AFTER the test publisher,
        otherwise builds with failed tests might be reported as successful via email
        '''
        self._DoTest(
            yaml_contents=dedent(
                '''
                email_notification:
                  recipients: user@company.com other@company.com
                  notify_every_build: true
                  notify_individuals: true

                jsunit_patterns:
                - "jsunit*.xml"
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <xunit>
                +      <thresholds>
                +        <org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +          <unstableThreshold>0</unstableThreshold>
                +          <unstableNewThreshold>0</unstableNewThreshold>
                +        </org.jenkinsci.plugins.xunit.threshold.FailedThreshold>
                +      </thresholds>
                +      <thresholdMode>1</thresholdMode>
                +      <types>
                +        <JSUnitPluginType>
                +          <pattern>jsunit*.xml</pattern>
                +          <skipNoTestFiles>true</skipNoTestFiles>
                +          <failIfNotNew>false</failIfNotNew>
                +          <deleteOutputFiles>true</deleteOutputFiles>
                +          <stopProcessingIfError>true</stopProcessingIfError>
                +        </JSUnitPluginType>
                +      </types>
                +    </xunit>
                +    <hudson.tasks.Mailer>
                +      <recipients>user@company.com other@company.com</recipients>
                +      <dontNotifyEveryUnstableBuild>false</dontNotifyEveryUnstableBuild>
                +      <sendToIndividuals>true</sendToIndividuals>
                +    </hudson.tasks.Mailer>
                +  </publishers>
                +  <buildWrappers>
                +    <hudson.plugins.ws__cleanup.PreBuildCleanup>
                +      <patterns>
                +        <hudson.plugins.ws__cleanup.Pattern>
                +          <pattern>jsunit*.xml</pattern>
                +          <type>INCLUDE</type>
                +        </hudson.plugins.ws__cleanup.Pattern>
                +      </patterns>
                +    </hudson.plugins.ws__cleanup.PreBuildCleanup>
                +  </buildWrappers>'''
            ),
        )


    def testNotification(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                notification:
                  protocol: ALPHA
                  format: BRAVO
                  url: https://bravo
                '''
            ),
            expected_diff=dedent(
            '''\
            @@ @@
            +  <properties>
            +    <com.tikal.hudson.plugins.notification.HudsonNotificationProperty plugin="notification@1.9">
            +      <endpoints>
            +        <com.tikal.hudson.plugins.notification.Endpoint>
            +          <protocol>ALPHA</protocol>
            +          <format>BRAVO</format>
            +          <url>https://bravo</url>
            +          <event>all</event>
            +          <timeout>30000</timeout>
            +          <loglines>1</loglines>
            +        </com.tikal.hudson.plugins.notification.Endpoint>
            +      </endpoints>
            +    </com.tikal.hudson.plugins.notification.HudsonNotificationProperty>
            +  </properties>'''
            )
        ),


    def testSlack(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                slack:
                  team: esss
                  room: zulu
                  token: ALPHA
                  url: https://bravo
                '''
            ),
            expected_diff=dedent(
            '''\
            @@ @@
            +  <properties>
            +    <jenkins.plugins.slack.SlackNotifier_-SlackJobProperty plugin="slack@1.2">
            +      <room>#zulu</room>
            +      <startNotification>true</startNotification>
            +      <notifySuccess>true</notifySuccess>
            +      <notifyAborted>true</notifyAborted>
            +      <notifyNotBuilt>true</notifyNotBuilt>
            +      <notifyUnstable>true</notifyUnstable>
            +      <notifyFailure>true</notifyFailure>
            +      <notifyBackToNormal>true</notifyBackToNormal>
            +    </jenkins.plugins.slack.SlackNotifier_-SlackJobProperty>
            +  </properties>
            +  <publishers>
            +    <jenkins.plugins.slack.SlackNotifier plugin="slack@1.2">
            +      <teamDomain>esss</teamDomain>
            +      <authToken>ALPHA</authToken>
            +      <buildServerUrl>https://bravo</buildServerUrl>
            +      <room>#zulu</room>
            +    </jenkins.plugins.slack.SlackNotifier>
            +  </publishers>'''
            )
        ),

    @pytest.mark.parametrize('conf_value, expected_name', [
        ('', 'xterm'),
        ('xterm', 'xterm'),
        ('vga', 'vga'),
    ])
    def testAnsiColor(self, conf_value, expected_name):
        self._DoTest(
            yaml_contents=dedent(
                '''
                console_color: %s
                '''
            ) % (conf_value,),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <buildWrappers>
                +    <hudson.plugins.ansicolor.AnsiColorBuildWrapper plugin="ansicolor@0.4.2">
                +      <colorMapName>%s</colorMapName>
                +    </hudson.plugins.ansicolor.AnsiColorBuildWrapper>
                +  </buildWrappers>'''
            ) % (expected_name,)
        )


    def testTimestamps(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                timestamps:
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <buildWrappers>
                +    <hudson.plugins.timestamper.TimestamperBuildWrapper plugin="timestamper@1.7.4"/>
                +  </buildWrappers>'''
            )
        )


    @pytest.mark.parametrize('condition', ('SUCCESS', 'UNSTABLE', 'FAILED', 'ALWAYS'))
    def testTriggerJobNoParameters(self, condition):
        self._DoTest(
            yaml_contents=dedent(
                '''
                trigger_jobs:
                  names:
                    - etk-master-linux64-27
                    - etk-master-linux64-36
                  condition: {condition}
                '''.format(condition=condition)
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <hudson.plugins.parameterizedtrigger.BuildTrigger plugin="parameterized-trigger@2.33">
                +      <configs>
                +        <hudson.plugins.parameterizedtrigger.BuildTriggerConfig>
                +          <configs class="empty-list"/>
                +          <projects>etk-master-linux64-27, etk-master-linux64-36</projects>
                +          <condition>{condition}</condition>
                +          <triggerWithNoParameters>true</triggerWithNoParameters>
                +          <triggerFromChildProjects>false</triggerFromChildProjects>
                +        </hudson.plugins.parameterizedtrigger.BuildTriggerConfig>
                +      </configs>
                +    </hudson.plugins.parameterizedtrigger.BuildTrigger>
                +  </publishers>'''.format(condition=condition)
            )
        )


    def testTriggerJobInvalidCondition(self):
        with pytest.raises(RuntimeError, match=r"Invalid value for condition: u?'UNKNOWN', expected one of .*"):
            self._DoTest(
                yaml_contents=dedent(
                    '''
                    trigger_jobs:
                      names:
                        - etk-master-linux64-27
                        - etk-master-linux64-36
                      condition: UNKNOWN
                    '''
                ),
                expected_diff='',
            )

    def testTriggerJobParameters(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                trigger_jobs:
                  names:
                    - etk-master-linux64-27
                    - etk-master-linux64-36
                  parameters:
                    - KEY1=VALUE1
                    - KEY2=VALUE2
                '''
            ),
            expected_diff=dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <hudson.plugins.parameterizedtrigger.BuildTrigger plugin="parameterized-trigger@2.33">
                +      <configs>
                +        <hudson.plugins.parameterizedtrigger.BuildTriggerConfig>
                +          <configs>
                +            <hudson.plugins.parameterizedtrigger.PredefinedBuildParameters>
                +              <properties>KEY1=VALUE1 KEY2=VALUE2</properties>
                +            </hudson.plugins.parameterizedtrigger.PredefinedBuildParameters>
                +          </configs>
                +          <projects>etk-master-linux64-27, etk-master-linux64-36</projects>
                +          <condition>SUCCESS</condition>
                +          <triggerWithNoParameters>false</triggerWithNoParameters>
                +          <triggerFromChildProjects>false</triggerFromChildProjects>
                +        </hudson.plugins.parameterizedtrigger.BuildTriggerConfig>
                +      </configs>
                +    </hudson.plugins.parameterizedtrigger.BuildTrigger>
                +  </publishers>'''
            )
        )


    def testAnsiColorUnknowOption(self):
        with pytest.raises(RuntimeError, match='Received unknown console_color option.'):
            self._DoTest(
                yaml_contents=dedent(
                    '''
                    console_color: unknown-value
                    '''
                ),
                expected_diff='',
            )

    @pytest.mark.parametrize(
        'scenario',
        [
            'complete',
            'incomplete_metrics',
            'incomplete_values',
        ]
    )
    def testCoverage(self, scenario):
        # Expected defaults
        healthy_method = 80
        healthy_line = 80
        healthy_conditional = 80

        unhealthy_method = 0
        unhealthy_line = 0
        unhealthy_conditional = 0

        failing_method = 0
        failing_line = 0
        failing_conditional = 0

        if scenario == 'complete':
            healthy_method = 100
            healthy_line = 100
            healthy_conditional = 90

            unhealthy_method = 70
            unhealthy_line = 70
            unhealthy_conditional = 60

            failing_method = 60
            failing_line = 60
            failing_conditional = 50
            contents = dedent(
                r'''
                coverage:
                  report_pattern: "**/build/coverage/*.xml"
                  healthy:
                    method: {healthy_method}
                    line: {healthy_line}
                    conditional: {healthy_conditional}
                  unhealthy:
                    method: {unhealthy_method}
                    line: {unhealthy_line}
                    conditional: {unhealthy_conditional}
                  failing:
                    method: {failing_method}
                    line: {failing_line}
                    conditional: {failing_conditional}
                '''
            )
        elif scenario == 'incomplete_metrics':
            healthy_method = 100
            healthy_line = 100
            healthy_conditional = 90

            contents = dedent(
                r'''
                coverage:
                  report_pattern: "**/build/coverage/*.xml"
                  healthy:
                    method: {healthy_method}
                    line: {healthy_line}
                    conditional: {healthy_conditional}
                '''
            )
        else:
            assert scenario == 'incomplete_values', "Unknown scenario"
            healthy_method = 100
            healthy_line = 100

            contents = dedent(
                r'''
                coverage:
                  report_pattern: "**/build/coverage/*.xml"
                  healthy:
                    method: {healthy_method}
                    line: {healthy_line}
                '''
            )

        expected_diff = dedent(
                '''\
                @@ @@
                +  <publishers>
                +    <hudson.plugins.cobertura.CoberturaPublisher plugin="cobertura@1.9.7">
                +      <coberturaReportFile>**/build/coverage/*.xml</coberturaReportFile>
                +      <onlyStable>false</onlyStable>
                +      <failUnhealthy>true</failUnhealthy>
                +      <failUnstable>true</failUnstable>
                +      <autoUpdateHealth>false</autoUpdateHealth>
                +      <autoUpdateStability>false</autoUpdateStability>
                +      <zoomCoverageChart>false</zoomCoverageChart>
                +      <maxNumberOfBuilds>0</maxNumberOfBuilds>
                +      <sourceEncoding>UTF_8</sourceEncoding>
                +      <healthyTarget>
                +        <targets class="enum-map" enum-type="hudson.plugins.cobertura.targets.CoverageMetric">
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>METHOD</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{healthy_method}</int>
                +          </entry>
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>LINE</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{healthy_line}</int>
                +          </entry>
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>CONDITIONAL</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{healthy_conditional}</int>
                +          </entry>
                +        </targets>
                +      </healthyTarget>
                +      <unhealthyTarget>
                +        <targets class="enum-map" enum-type="hudson.plugins.cobertura.targets.CoverageMetric">
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>METHOD</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{unhealthy_method}</int>
                +          </entry>
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>LINE</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{unhealthy_line}</int>
                +          </entry>
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>CONDITIONAL</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{unhealthy_conditional}</int>
                +          </entry>
                +        </targets>
                +      </unhealthyTarget>
                +      <failingTarget>
                +        <targets class="enum-map" enum-type="hudson.plugins.cobertura.targets.CoverageMetric">
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>METHOD</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{failing_method}</int>
                +          </entry>
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>LINE</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{failing_line}</int>
                +          </entry>
                +          <entry>
                +            <hudson.plugins.cobertura.targets.CoverageMetric>CONDITIONAL</hudson.plugins.cobertura.targets.CoverageMetric>
                +            <int>{failing_conditional}</int>
                +          </entry>
                +        </targets>
                +      </failingTarget>
                +    </hudson.plugins.cobertura.CoberturaPublisher>
                +  </publishers>'''
            )

        contents_ = contents.format(**locals())

        healthy_method *= 100000
        healthy_line *= 100000
        healthy_conditional *= 100000
        unhealthy_method *= 100000
        unhealthy_line *= 100000
        unhealthy_conditional *= 100000
        failing_method *= 100000
        failing_line *= 100000
        failing_conditional *= 100000
        expected_diff_ = expected_diff.format(**locals())

        self._DoTest(
            yaml_contents=contents_,
            expected_diff=expected_diff_,
        )

    def testCoverageFailWhenMissingReportPattern(self):
        with pytest.raises(ValueError, match='Report pattern is required by coverage') as e:
            self._GenerateJob(yaml_contents=dedent(
                r'''
                coverage:
                  healthy:
                    method: 100
                    line: 100
                '''
            ))


    def testWarnings(self):
        self._DoTest(
            yaml_contents=dedent(
                '''
                warnings:
                  console:
                    - parser: Clang (LLVM based)
                    - parser: PyLint
                  file:
                    - parser: CppLint
                      file_pattern: "*.cpplint"
                    - parser: CodeAnalysis
                      file_pattern: "*.codeanalysis"
                '''
            ),
            expected_diff='@@ @@\n' + '\n'.join('+  ' + s for s in dedent(
            '''\
            <publishers>
              <hudson.plugins.warnings.WarningsPublisher plugin="warnings@4.59">
                <healthy/>
                <unHealthy/>
                <thresholdLimit>low</thresholdLimit>
                <pluginName>[WARNINGS]</pluginName>
                <defaultEncoding/>
                <canRunOnFailed>true</canRunOnFailed>
                <usePreviousBuildAsReference>false</usePreviousBuildAsReference>
                <useStableBuildAsReference>false</useStableBuildAsReference>
                <useDeltaValues>false</useDeltaValues>
                <thresholds plugin="analysis-core@1.82">
                  <unstableTotalAll/>
                  <unstableTotalHigh/>
                  <unstableTotalNormal/>
                  <unstableTotalLow/>
                  <unstableNewAll/>
                  <unstableNewHigh/>
                  <unstableNewNormal/>
                  <unstableNewLow/>
                  <failedTotalAll/>
                  <failedTotalHigh/>
                  <failedTotalNormal/>
                  <failedTotalLow/>
                  <failedNewAll/>
                  <failedNewHigh/>
                  <failedNewNormal/>
                  <failedNewLow/>
                </thresholds>
                <shouldDetectModules>false</shouldDetectModules>
                <dontComputeNew>true</dontComputeNew>
                <doNotResolveRelativePaths>false</doNotResolveRelativePaths>
                <includePattern/>
                <excludePattern/>
                <messagesPattern/>
                <parserConfigurations>
                  <hudson.plugins.warnings.ParserConfiguration>
                    <pattern>*.cpplint</pattern>
                    <parserName>CppLint</parserName>
                  </hudson.plugins.warnings.ParserConfiguration>
                  <hudson.plugins.warnings.ParserConfiguration>
                    <pattern>*.codeanalysis</pattern>
                    <parserName>CodeAnalysis</parserName>
                  </hudson.plugins.warnings.ParserConfiguration>
                </parserConfigurations>
                <consoleParsers>
                  <hudson.plugins.warnings.ConsoleParser>
                    <parserName>Clang (LLVM based)</parserName>
                  </hudson.plugins.warnings.ConsoleParser>
                  <hudson.plugins.warnings.ConsoleParser>
                    <parserName>PyLint</parserName>
                  </hudson.plugins.warnings.ConsoleParser>
                </consoleParsers>
              </hudson.plugins.warnings.WarningsPublisher>
            </publishers>''').splitlines()),
        )


    def testWarningsEmpty(self):
        with pytest.raises(JobsDoneFileTypeError):
            self._GenerateJob(yaml_contents='warnings:')
        with pytest.raises(ValueError, match="Empty 'warnings' options.*"):
            self._GenerateJob(yaml_contents='warnings: {}')


    def testWarningsWrongOption(self):
        with pytest.raises(ValueError, match="Received unknown 'warnings' options: zucchini."):
            self._GenerateJob(yaml_contents=dedent('''\
                warnings:
                  zucchini:
                    - parser: Pizza
                  file:
                    - parser: CppLint
                      file_pattern: "*.cpplint"
                ''')
            )


    def _GenerateJob(self, yaml_contents):
        repository = Repository(url='http://fake.git', branch='not_master')
        jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository)

        job_generator = JenkinsXmlJobGenerator()
        JobGeneratorConfigurator.Configure(job_generator, jobs_done_jobs[0])
        return job_generator.GetJob()

    def _DoTest(self, yaml_contents, expected_diff):
        '''
        :param unicode yaml_contents:
            Contents of JobsDoneJob used for this test

        :param unicode expected_diff:
            Expected diff from build jobs from `yaml_contents`, when compared to BASIC_EXPECTED_XML.
        '''
        jenkins_job = self._GenerateJob(yaml_contents=yaml_contents)
        self._AssertDiff(jenkins_job.xml, expected_diff)


    def _AssertDiff(self, obtained_xml, expected_diff):
        diff = ''.join(difflib.unified_diff(
            self.BASIC_EXPECTED_XML.splitlines(1),
            str(obtained_xml).splitlines(1),
            n=0,
        ))
        diff = '\n'.join(diff.splitlines()[2:])
        diff = re.sub('@@.*@@', '@@ @@', diff, flags=re.MULTILINE)

        print(obtained_xml)

        # print diff
        assert expected_diff == diff



#===================================================================================================
# TestJenkinsActions
#===================================================================================================
class TestJenkinsActions(object):
    '''
    Integration tests for Jenkins actions
    '''

    _JOBS_DONE_FILE_CONTENTS = dedent(
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

    def testGetJobsFromFile(self):
        jobs = GetJobsFromFile(self._REPOSITORY, self._JOBS_DONE_FILE_CONTENTS)
        assert len(jobs) == 3


    def testGetJobsFromDirectory(self, tmpdir):
        repo_path = tmpdir / 'git_repository'
        repo_path.mkdir()

        # Prepare git repository
        with repo_path.as_cwd():
            check_call('git init', shell=True)
            check_call('git config user.name Bob', shell=True)
            check_call('git config user.email bob@example.com', shell=True)
            check_call('git remote add origin %s' % self._REPOSITORY.url, shell=True)
            check_call('git checkout -b %s' % self._REPOSITORY.branch, shell=True)
            repo_path.join('.gitignore').write('')
            check_call('git add .', shell=True)
            check_call('git commit -a -m "First commit"', shell=True)

            # If there is no jobs_done file, we should get zero jobs
            _repository, jobs = GetJobsFromDirectory(str(repo_path))
            assert len(jobs) == 0

            # Create jobs_done file
            repo_path.join(JOBS_DONE_FILENAME).write(self._JOBS_DONE_FILE_CONTENTS)
            check_call('git add .', shell=True)
            check_call('git commit -a -m "Added jobs_done file"', shell=True)

            _repository, jobs = GetJobsFromDirectory(str(repo_path))
            assert len(jobs) == 3


    def testUploadJobsFromFile(self, monkeypatch):
        '''
        Tests that UploadJobsFromFile correctly calls JenkinsJobPublisher (already tested elsewhere)
        '''
        def MockPublishToUrl(self, url, username, password):
            assert url == 'jenkins_url'
            assert username == 'jenkins_user'
            assert password == 'jenkins_pass'

            assert set(self.jobs.keys()) == {'space-branch-venus', 'space-branch-jupiter', 'space-branch-mercury'}

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

    def testPublishToDirectory(self, tmpdir):
        self._GetPublisher().PublishToDirectory(str(tmpdir))

        assert set(os.path.basename(str(x)) for x in tmpdir.listdir()) == {
            'space-milky_way-jupiter', 'space-milky_way-mercury', 'space-milky_way-venus'}

        assert tmpdir.join('space-milky_way-jupiter').read() == 'jupiter'
        assert tmpdir.join('space-milky_way-mercury') .read() == 'mercury'
        assert tmpdir.join('space-milky_way-venus').read() == 'venus'


    def testPublishToUrl(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        new_jobs, updated_jobs, deleted_jobs = self._GetPublisher().PublishToUrl(
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == {'space-milky_way-venus', 'space-milky_way-jupiter'}
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == {'space-milky_way-mercury'}
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == {'space-milky_way-saturn'}


    def testPublishToUrlProxyErrorOnce(self, monkeypatch):
        # Do not actually sleep during tests
        monkeypatch.setattr(JenkinsJobPublisher, 'RETRY_SLEEP', 0)

        # Tell mock jenkins to raise a proxy error, our retry should catch it and continue
        mock_jenkins = self._MockJenkinsAPI(monkeypatch, proxy_errors=1)
        new_jobs, updated_jobs, deleted_jobs = self._GetPublisher().PublishToUrl(
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == {'space-milky_way-venus', 'space-milky_way-jupiter'}
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == {'space-milky_way-mercury'}
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == {'space-milky_way-saturn'}


    def testPublishToUrlProxyErrorTooManyTimes(self, monkeypatch):
        # Do not actually sleep during tests
        monkeypatch.setattr(JenkinsJobPublisher, 'RETRY_SLEEP', 0)
        monkeypatch.setattr(JenkinsJobPublisher, 'RETRIES', 3)

        # Tell mock jenkins to raise 5 proxy errors in a row, this should bust our retry limit
        self._MockJenkinsAPI(monkeypatch, proxy_errors=5)

        from requests.exceptions import HTTPError
        with pytest.raises(HTTPError):
            self._GetPublisher().PublishToUrl(
                url='jenkins_url',
                username='jenkins_user',
                password='jenkins_pass',
            )


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
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == {'space-milky_way-mercury', 'space-milky_way-saturn'}


    def _GetPublisher(self):
        repository = Repository(url='http://server/space.git', branch='milky_way')
        jobs = [
            JenkinsJob(name='space-milky_way-jupiter', xml='jupiter', repository=repository),
            JenkinsJob(name='space-milky_way-mercury', xml='mercury', repository=repository),
            JenkinsJob(name='space-milky_way-venus', xml='venus', repository=repository),
        ]

        return JenkinsJobPublisher(repository, jobs)


    def _MockJenkinsAPI(self, monkeypatch, proxy_errors=0):
        class MockJenkins(object):
            NEW_JOBS = set()
            UPDATED_JOBS = set()
            DELETED_JOBS = set()

            def __init__(self, url, username, password):
                assert url == 'jenkins_url'
                assert username == 'jenkins_user'
                assert password == 'jenkins_pass'
                self.proxy_errors_raised = 0

            def get_jobs(self):
                return [{'name': 'space-milky_way-mercury'}, {'name': 'space-milky_way-saturn'}]

            def get_job_config(self, job_name):
                # Test with single, and multiple scms
                if job_name == 'space-milky_way-mercury':
                    return dedent(
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
                    return dedent(
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
                else:
                    assert 0, f'unknown job name: {job_name}'

            def create_job(self, name, xml):
                assert type(xml) is str
                self.NEW_JOBS.add(name)

            def reconfig_job(self, name, xml):
                self.UPDATED_JOBS.add(name)

            def delete_job(self, name):
                if self.proxy_errors_raised < proxy_errors:
                    self.proxy_errors_raised += 1
                    from unittest.mock import Mock
                    from requests.exceptions import HTTPError
                    response = Mock()
                    response.status_code = 403
                    raise HTTPError(response=response)

                self.DELETED_JOBS.add(name)


        monkeypatch.setattr(jenkins, 'Jenkins', MockJenkins)

        return MockJenkins
