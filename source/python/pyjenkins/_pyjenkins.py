from ben10.filesystem import CreateFile
from ben10.foundation.decorators import Implements
from ben10.interface import ImplementsInterface, Interface



#===================================================================================================
# IJenkinsJobGeneratorPlugin
#===================================================================================================
class IJenkinsJobGeneratorPlugin(Interface):
    '''
    Interface for jenkins-job-generators plugins.

    All plugins must define a TYPE (class attribute) and implement the Create method. That's it!
    '''

    TYPE_BUILDER = 'builders'
    TYPE_PUBLISHER = 'publishers'
    TYPE_SCM = 'scm'
    TYPE_BUILD_WRAPPER = 'buildWrappers'

    # One of the TYPE_XXX constants above.
    TYPE = None

    def Create(self, xml_factory):
        '''
        Create the xml-nodes inside the given xml_factory.
        '''



#===================================================================================================
# JenkinsJobGenerator
#===================================================================================================
class JenkinsJobGenerator(object):
    '''
    Configure a Jenkins job for generation.

    Usage:
        job_generator = JenkinsJobGenerator('alpha', 'bravo-lib')

        # Configure some options...
        job_generator.num_to_keep = 10

        job_generator.CreateJobDirectory('.')


    :ivar str id:
        The job identification string. This is used to generate the job name.

    :ivar str name:
        The job name. This is used inside templates.

    :ivar str description:
        The job description.

    :ivar str display_name:
        The job display-name. This value can use attribute replacement such as %(name)s

    :ivar str assigned_node:
        This must match the execution nodes configuration in order to be built on that node.

    :ivar int days_to_keep:
        Number of days to keep the job history.

    :ivar int num_to_keep:
        Number of history entries to keep.

    :ivar int timeout:
        Job build timeout in minutes. After the timeout the job automatically fails

    :ivar str custom_workspace:
        Path to the (custom) workspace for the job.

    :ivar str job_name_format:
        Determine the format of the job-name (GetJobName)
        The dictionary expressions are replaced by this class attributes.

    :ivar dict(str,tuple(str,str,list(str))) __parameters:
        Holds information about job parameters
        Use the following method to add a parameter:
          AddChoiceParameter(name, description, choices)
    '''
    CONFIG_FILENAME = 'config.xml'

    DEFAULT_ASSIGNED_NODE = ''

    PLUGINS = {}

    @classmethod
    def RegisterPlugin(cls, plugin_name, plugin_class):
        assert plugin_name not in cls.PLUGINS, \
            "Plugin class named '%s' already registered" % plugin_name
        cls.PLUGINS[plugin_name] = plugin_class


    class BuilderFilenameNotFound(RuntimeError):
        '''
        Exception raised when a builder is not found.

        This exception has the following attributes:

        :ivar str filename:
            The filename "as requested" of the builder

        :ivar list(str) tried:
            A list of full filenames tried by the algorithm for the given filename.
        '''

        def __init__(self, filename, tried):
            '''
            :param list(str) tried:
                List of
            '''
            RuntimeError.__init__(self)
            self.filename = filename
            self.tried = tried

        def __str__(self):
            return "Builder filename not found:%s.\nTried:%s" % (
                self.filename,
                '\n  - '.join([''] + self.tried)
            )


    def __init__(self, job_id):
        self.id = job_id
        self.name = job_id
        self.description = 'JenkinsJobGenerator'
        self.display_name = ''
        self.assigned_node = self.DEFAULT_ASSIGNED_NODE
        self.days_to_keep = 7
        self.num_to_keep = 16
        self.timeout = None
        self.custom_workspace = None
        self.job_name_format = '%(id)s'
        self.__parameters = {}
        self.__plugins = {}


    # Plugins --------------------------------------------------------------------------------------

    def AddPlugin(self, name, *args, **kwargs):
        '''
        Adds a plugin in the generator instance.
        Plugins are registered using the class method JenkinsJobGenerator.RegisterPlugin

        :return IJenkinsJobGeneratorPlugin:
            Returns the instance of the plugin.
            If the plugin was already added, returns it and do not create a new instance.
        '''
        plugin_class = self.PLUGINS.get(name)
        assert plugin_class is not None, 'Plugin class "%s" not found!' % name

        plugin_instance = self.__plugins.get(name)
        if plugin_instance is None:
            plugin_instance = plugin_class(*args, **kwargs)
            self.__plugins[name] = plugin_instance

        return plugin_instance


    def ListPlugins(self, type_):
        '''
        Lists all plugins instances of the given type.

        :param IJenkinsJobGeneratorPlugin.TYPE_XXX type:

        :return list(IJenkinsJobGeneratorPlugin):
        '''
        return [i for i in self.__plugins.itervalues() if i.TYPE == type_]


    # Job ------------------------------------------------------------------------------------------

    def GetJobName(self, **kwargs):
        '''
        Returns the job name.
        Uses the format defined in job_name_format attribute.

        :rtype: str
        :returns:
            The job name.
        '''
        dd = self._ReplacementDict()
        dd.update(kwargs)
        return self.job_name_format % dd


    def _ReplacementDict(self):
        '''
        Returns a replacement dict used to expand symbols for dynamically generated names (such
        as GetJobName).
        '''
        return self.__dict__


    def GetContent(self):
        '''
        Returns the configuration file XML contents.

        :return str:
        '''
        from xml_factory import XmlFactory

        xml_factory = XmlFactory('project')
        xml_factory['actions']
        xml_factory['description'] = self.description
        if self.display_name != '':
            xml_factory['displayName'] = self.display_name % self._ReplacementDict()
        xml_factory['keepDependencies'] = 'false'
        xml_factory['blockBuildWhenDownstreamBuilding'] = 'false'
        xml_factory['blockBuildWhenUpstreamBuilding'] = 'false'
        xml_factory['concurrentBuild'] = 'false'
        xml_factory['assignedNode'] = self.assigned_node % self._ReplacementDict()
        xml_factory['canRoam'] = 'false'

        # Log Rotator
        xml_factory['logRotator/daysToKeep'] = self.days_to_keep
        xml_factory['logRotator/numToKeep'] = self.num_to_keep
        xml_factory['logRotator/artifactDaysToKeep'] = -1
        xml_factory['logRotator/artifactNumToKeep'] = -1

        self._CreateProperties(xml_factory)

        # Configure SCM
        for i_publisher_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_SCM):
            i_publisher_plugin.Create(xml_factory)

        xml_factory['blockBuildWhenDownstreamBuilding'] = 'false'
        xml_factory['blockBuildWhenUpstreamBuilding'] = 'false'
        xml_factory['concurrentBuild'] = 'false'

        builders_xml = xml_factory[IJenkinsJobGeneratorPlugin.TYPE_BUILDER]
        for i_builder_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_BUILDER):
            i_builder_plugin.Create(builders_xml)

        publishers_xml = xml_factory[IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER]
        for i_publisher_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER):
            i_publisher_plugin.Create(publishers_xml)

        build_wrappers_xml = xml_factory[IJenkinsJobGeneratorPlugin.TYPE_BUILD_WRAPPER]
        for i_publisher_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_BUILD_WRAPPER):
            i_publisher_plugin.Create(build_wrappers_xml)

        if self.custom_workspace:
            xml_factory['customWorkspace'] = self.custom_workspace % self._ReplacementDict()

        return xml_factory.GetContent(xml_header=True)


    def CreateConfigFile(self, config_filename):
        '''
        Create the job configuration file with the given filename.

        :param str config_file:
            The configuration filename.
        '''
        CreateFile(config_filename, self.GetContent())


    PARAM_CHOICE = 'CHOICE'

    def AddChoiceParameter(self, name, description, choices):
        '''
        Adds a choice parameter to the job.

        :param str name:
            The name of the parameter. Usually PARAM_XXX
        :param str description:
            The description of the parameter
        :param list(str) choices:
            List of possible values. The first is the default.
        '''
        self.__parameters[name] = (self.PARAM_CHOICE, description, choices)


    def _CreateProperties(self, xml_factory):
        '''
        Create the "properties" XML entry for the job.

        This XML branch is where the job parameters are configured.

        :param XmlFactory xml_factory:
            A xml-factory to fill.
        '''
        parameters_xml_path = 'hudson.model.ParametersDefinitionProperty/parameterDefinitions/' \
            'hudson.model.ChoiceParameterDefinition'

        properties = xml_factory['properties']
        for (i_name, (i_type, i_description, i_choices)) in self.__parameters.iteritems():
            if i_type == self.PARAM_CHOICE:
                p = properties[parameters_xml_path]
                p['name'] = i_name
                p['description'] = i_description
                p['choices@class'] = 'java.util.Arrays$ArrayList'
                p['choices/a@class'] = 'string-array'
                for j_choice in i_choices:
                    p['choices/a/string+'] = j_choice



#===================================================================================================
# GitBuilder
#===================================================================================================
class GitBuilder(object):
    '''
    A jenkins-job-generator plugin that adds a git SCM in the generation.

    :ivar str url:
        The git repository URL.

    :ivar str target_dir:
        The target directory for the working copy.
        Defaults to "" which means that the workspace directory will be the working copy.

    :ivar str branch:
        The branch to build.
        Default to "master"

    :ivar str remote:
        The name of the git remote to configure.
        Default to "origin"

    :ivar str refspec:
        "A refspec controls the remote refs to be retrieved and how they map to local refs."
        Default to "+refs/heads/*:refs/remotes/origin/*"
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_SCM

    def __init__(
        self,
        url,
        target_dir=None,
        branch='master',
        remote='origin',
        refspec='+refs/heads/*:refs/remotes/origin/*'):

        self.url = url
        self.target_dir = target_dir
        self.branch = branch
        self.remote = remote
        self.refspec = refspec


    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        xml_factory['scm@class'] = 'hudson.plugins.git.GitSCM'
        xml_factory['scm/configVersion'] = '2'
        xml_factory['scm/userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/name'] = self.remote
        xml_factory['scm/userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/refspec'] = self.refspec
        xml_factory['scm/userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url'] = self.url
        xml_factory['scm/branches/hudson.plugins.git.BranchSpec/name'] = self.branch
        xml_factory['scm/excludedUsers']
        xml_factory['scm/buildChooser@class'] = 'hudson.plugins.git.util.DefaultBuildChooser'
        xml_factory['scm/disableSubmodules'] = 'false'
        xml_factory['scm/recursiveSubmodules'] = 'false'
        xml_factory['scm/doGenerateSubmoduleConfigurations'] = 'false'
        xml_factory['scm/authorOrCommitter'] = 'false'
        xml_factory['scm/clean'] = 'false'
        xml_factory['scm/wipeOutWorkspace'] = 'false'
        xml_factory['scm/pruneBranches'] = 'false'
        xml_factory['scm/remotePoll'] = 'false'
        xml_factory['scm/gitTool'] = 'Default'
        xml_factory['scm/submoduleCfg@class'] = 'list'
        xml_factory['scm/relativeTargetDir'] = self.target_dir
        xml_factory['scm/reference']
        xml_factory['scm/gitConfigName']
        xml_factory['scm/gitConfigEmail']
        xml_factory['scm/skipTag'] = 'false'
        xml_factory['scm/scmName']


JenkinsJobGenerator.RegisterPlugin('git', GitBuilder)



#===================================================================================================
# ShellBuilder
#===================================================================================================
class ShellBuilder(object):
    '''
    A jenkins-job-generator plugin that adds a shell (linux) command shell.

    :ivar list(str) command_lines:
        Command lines to execute.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_BUILDER

    def __init__(self):
        self.command_lines = []

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        for i_command_line in self.command_lines:
            xml_factory['hudson.tasks.Shell+/command'] = i_command_line

JenkinsJobGenerator.RegisterPlugin('shell', ShellBuilder)



#===================================================================================================
# BatchBuilder
#===================================================================================================
class BatchBuilder(object):
    '''
    A jenkins-job-generator plugin that adds a batch (windows) command.

    :ivar list(str) command_lines:
        Command lines to execute.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_BUILDER

    def __init__(self):
        self.command_lines = []

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        for i_command_line in self.command_lines:
            xml_factory['hudson.tasks.BatchFile+/command'] = i_command_line

JenkinsJobGenerator.RegisterPlugin('batch', BatchBuilder)



#===================================================================================================
# DescriptionSetterPublisher
#===================================================================================================
class DescriptionSetterPublisher(object):
    '''
    A jenkins-job-generator plugin that configures the description-setter.

    :ivar str regexp:
        Regular expression (Java) for the description setter.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER

    def __init__(self, regexp):
        self.regexp = regexp

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        xml_factory['hudson.plugins.descriptionsetter.DescriptionSetterPublisher/regexp'] = self.regexp
        xml_factory['hudson.plugins.descriptionsetter.DescriptionSetterPublisher/regexpForFailed'] = self.regexp
        xml_factory['hudson.plugins.descriptionsetter.DescriptionSetterPublisher/setForMatrix'] = 'false'


JenkinsJobGenerator.RegisterPlugin('description-setter', DescriptionSetterPublisher)



#===================================================================================================
# XUnitPublisher
#===================================================================================================
class XUnitPublisher(object):
    '''
    A jenkins-job-generator plugin that configures the unit-test publisher.

    :ivar str junit_patterns:
        File patterns to find JUnit files.

    :ivar str boost_patterns:
        File patterns to find Boost-Test files.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER

    def __init__(self):
        self.junit_patterns = ''
        self.boost_patterns = ''

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        if not self.junit_patterns and self.boost_patterns:
            return

        if self.junit_patterns:
            xml_factory['xunit/types/JUnitType/pattern'] = ' '.join(self.junit_patterns)
            xml_factory['xunit/types/JUnitType/skipNoTestFiles'] = 'true'
            xml_factory['xunit/types/JUnitType/failIfNotNew'] = 'false'
            xml_factory['xunit/types/JUnitType/deleteOutputFiles'] = 'true'
            xml_factory['xunit/types/JUnitType/stopProcessingIfError'] = 'true'

        if self.boost_patterns:
            xml_factory['xunit/types/BoostTestJunitHudsonTestType/pattern'] = ' '.join(self.boost_patterns)
            xml_factory['xunit/types/BoostTestJunitHudsonTestType/skipNoTestFiles'] = 'true'
            xml_factory['xunit/types/BoostTestJunitHudsonTestType/failIfNotNew'] = 'false'
            xml_factory['xunit/types/BoostTestJunitHudsonTestType/deleteOutputFiles'] = 'true'
            xml_factory['xunit/types/BoostTestJunitHudsonTestType/stopProcessingIfError'] = 'true'

        xml_factory['xunit/thresholds/org.jenkinsci.plugins.xunit.threshold.FailedThreshold/unstableThreshold'] = '0'
        xml_factory['xunit/thresholds/org.jenkinsci.plugins.xunit.threshold.FailedThreshold/unstableNewThreshold'] = '0'
        xml_factory['xunit/thresholdMode'] = '1'


JenkinsJobGenerator.RegisterPlugin('xunit', XUnitPublisher)



#===================================================================================================
# Timeout
#===================================================================================================
class Timeout(object):
    '''
    A jenkins-job-generator plugin that configures the job timetout.

    :ivar int timeout:
        The timeout value in minutes.
    '''
    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_BUILD_WRAPPER

    def __init__(self, timeout):
        self.timeout = timeout

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        build_timeout_wrapper = xml_factory['hudson.plugins.build__timeout.BuildTimeoutWrapper']
        build_timeout_wrapper['timeoutMinutes'] = str(self.timeout)
        build_timeout_wrapper['failBuild'] = 'true'


JenkinsJobGenerator.RegisterPlugin('timeout', Timeout)

