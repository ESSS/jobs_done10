from ben10.filesystem import GetFileContents
from ben10.foundation.string import Dedent
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

        assert GetFileContents(config_filename) == Dedent(
            '''
            <?xml version="1.0" ?>
            <project>
              <actions/>
              <description></description>
              <keepDependencies>false</keepDependencies>
              <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
              <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
              <concurrentBuild>false</concurrentBuild>
              <assignedNode></assignedNode>
              <canRoam>false</canRoam>
              <logRotator>
                <daysToKeep>7</daysToKeep>
                <numToKeep>-1</numToKeep>
                <artifactDaysToKeep>-1</artifactDaysToKeep>
                <artifactNumToKeep>-1</artifactNumToKeep>
              </logRotator>
              <builders/>
              <publishers/>
              <buildWrappers/>
              <triggers/>
            </project>
            '''
        )
