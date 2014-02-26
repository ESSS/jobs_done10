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
    TYPE_BUILD_WRAPPER = 'buildWrappers'
    TYPE_PARAMETER = 'parameter'
    TYPE_TRIGGER = 'triggers'
    TYPE_PUBLISHER = 'publishers'
    TYPE_SCM = 'scm'

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

        # Add some plugins
        xunit_plugin = job_generator.AddPlugin("xunit")
        xunit_plugin.junit_patterns = junit_patterns

        print job_generator.GetContent()

    :ivar str job_name:
        Determines the job name

    :ivar str description:
        The job description.

    :ivar str display_name:
        The job display-name. This value can use attribute replacement such as %(name)s

    :ivar str label_expression:
        This must match the execution nodes configuration in order to be built on that node.

    :ivar int days_to_keep:
        Number of days to keep the job history.

    :ivar int num_to_keep:
        Number of history entries to keep.

    :ivar int timeout:
        Job build timeout in minutes. After the timeout the job automatically fails

    :ivar str custom_workspace:
        Path to the (custom) workspace for the job.
    '''
    CONFIG_FILENAME = 'config.xml'

    DEFAULT_LABEL_EXPRESSION = ''

    PLUGINS = {}

    def __init__(self, job_name):
        self.job_name = job_name
        self.description = ''
        self.display_name = ''
        self.label_expression = self.DEFAULT_LABEL_EXPRESSION
        self.days_to_keep = 7
        self.num_to_keep = -1
        self.timeout = None
        self.custom_workspace = None
        self.__plugins = {}


    # Plugins --------------------------------------------------------------------------------------
    @classmethod
    def RegisterPlugin(cls, plugin_name, plugin_class):
        assert plugin_name not in cls.PLUGINS, \
            "Plugin class named '%s' already registered" % plugin_name
        cls.PLUGINS[plugin_name] = plugin_class


    def ObtainPlugin(self, name, *args, **kwargs):
        '''
        Adds a plugin in the generator instance.
        Plugins are registered using the class method JenkinsJobGenerator.RegisterPlugin

        :return IJenkinsJobGeneratorPlugin:
            Returns the instance of the plugin.
            If the plugin was already added, returns it and do not create a new instance.
        '''
        instances = self.__plugins.get(name)
        if instances is not None:
            return instances[0]

        return self.CreatePlugin(name, *args, **kwargs)


    def CreatePlugin(self, name, *args, **kwargs):
        '''
        Adds a plugin in the generator instance.
        Plugins are registered using the class method JenkinsJobGenerator.RegisterPlugin

        :return IJenkinsJobGeneratorPlugin:
            Returns the instance of the plugin.
            If the plugin was already added, returns it and do not create a new instance.
        '''
        plugin_class = self.PLUGINS.get(name)
        assert plugin_class is not None, 'Plugin class "%s" not found!' % name

        plugin_instance = plugin_class(*args, **kwargs)
        self.__plugins.setdefault(name, []).append(plugin_instance)

        return plugin_instance


    def ListPlugins(self, type_):
        '''
        Lists all plugins instances of the given type.

        :param IJenkinsJobGeneratorPlugin.TYPE_XXX type:

        :return list(IJenkinsJobGeneratorPlugin):
        '''
        from ben10.foundation.types_ import Flatten
        plugins = [p for p in Flatten(self.__plugins.itervalues()) if p.TYPE == type_]

        # Sort plugins because some might required a defined order among them
        return sorted(plugins)


    # Job ------------------------------------------------------------------------------------------
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
            xml_factory['displayName'] = self.display_name % self.__dict__
        xml_factory['keepDependencies'] = 'false'
        xml_factory['blockBuildWhenDownstreamBuilding'] = 'false'
        xml_factory['blockBuildWhenUpstreamBuilding'] = 'false'
        xml_factory['concurrentBuild'] = 'false'
        xml_factory['assignedNode'] = self.label_expression % self.__dict__
        xml_factory['canRoam'] = 'false'

        # Log Rotator
        xml_factory['logRotator/daysToKeep'] = self.days_to_keep
        xml_factory['logRotator/numToKeep'] = self.num_to_keep
        xml_factory['logRotator/artifactDaysToKeep'] = -1
        xml_factory['logRotator/artifactNumToKeep'] = -1

        # Parameters
        for i_parameter_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_PARAMETER):
            i_parameter_plugin.Create(xml_factory)

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

        triggers_xml = xml_factory[IJenkinsJobGeneratorPlugin.TYPE_TRIGGER]
        for i_trigger_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_TRIGGER):
            i_trigger_plugin.Create(triggers_xml)

        if self.custom_workspace:
            xml_factory['customWorkspace'] = self.custom_workspace % self.__dict__

        return xml_factory.GetContent(xml_header=True)


    def CreateConfigFile(self, config_filename):
        '''
        Create the job configuration file with the given filename.

        :param str config_file:
            The configuration filename.
        '''
        CreateFile(config_filename, self.GetContent())



#===================================================================================================
# BaseJenkinsJobGeneratorPlugin
#===================================================================================================
class BaseJenkinsJobGeneratorPlugin(object):
    '''
    :cvar int PRIORITY:
        Priority of this plugin in relation to others.
        Smaller values mean higher priority.
    '''
    PRIORITY = 0

    def __cmp__(self, other):
        '''
        Used for sorting plugins in order of priority.

        :param BaseJenkinsJobGeneratorPlugin other:
            Other plugin being compared to this one.
        '''
        return cmp(self.PRIORITY, other.PRIORITY)



#===================================================================================================
# PyJenkinsPlugin
#===================================================================================================
def PyJenkinsPlugin(plugin_name):
    '''
    Decorator for plugin classes

    :param str plugin_name:
        Name of the plugin, used in `JenkinsJobGenerator.AddPlugin`
    '''
    def PluginDecorator(plugin_class):
        JenkinsJobGenerator.RegisterPlugin(plugin_name, plugin_class)
        return plugin_class
    return PluginDecorator



#===================================================================================================
# GitBuilder
#===================================================================================================
@PyJenkinsPlugin('git')
class GitBuilder(BaseJenkinsJobGeneratorPlugin):
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
        xml_factory['scm/scmName']

        # Checkout to local branch is done twice to work with different versions of plugin (2.0+, 1.5)
        xml_factory['scm/extensions/hudson.plugins.git.extensions.impl.LocalBranch/localBranch'] = self.branch
        xml_factory['scm/localBranch'] = self.branch



#===================================================================================================
# ShellBuilder
#===================================================================================================
@PyJenkinsPlugin('shell')
class ShellBuilder(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that adds a shell (linux) command shell.

    :ivar list(str) command_lines:
        Command lines to execute.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_BUILDER

    def __init__(self, command):
        self.command = command

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        xml_factory['hudson.tasks.Shell+/command'] = self.command



#===================================================================================================
# BatchBuilder
#===================================================================================================
@PyJenkinsPlugin('batch')
class BatchBuilder(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that adds a batch (windows) command.

    :ivar list(str) command_lines:
        Command lines to execute.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_BUILDER

    def __init__(self, command):
        self.command = command

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        xml_factory['hudson.tasks.BatchFile+/command'] = self.command



#===================================================================================================
# DescriptionSetterPublisher
#===================================================================================================
@PyJenkinsPlugin('description-setter')
class DescriptionSetterPublisher(BaseJenkinsJobGeneratorPlugin):
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



#===================================================================================================
# StashNotifier
#===================================================================================================
@PyJenkinsPlugin('stash-notifier')
class StashNotifier(BaseJenkinsJobGeneratorPlugin):
    '''
    Notifies Stash instances when a build passes

    :ivar str url:
        Stash URL

    :ivar str username:

    :ivar str password:
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER

    # StashNotifier must always be the last plugin when compared to other plugins, to make sure that
    # things such as test result publisher are executed before this, otherwise, builds with failed
    # tests might be reported as successful to Stash.
    PRIORITY = 1

    def __init__(self, url='', username='', password=''):
        self.url = url
        self.username = username
        self.password = password

        if password and not username:
            raise ValueError('Must pass "username" when passing "password"')


    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        notifier = xml_factory['org.jenkinsci.plugins.stashNotifier.StashNotifier']
        notifier['stashServerBaseUrl'] = self.url
        notifier['stashUserName'] = self.username
        notifier['stashUserPassword'] = self.password



#===================================================================================================
# XUnitPublisher
#===================================================================================================
@PyJenkinsPlugin('xunit')
class XUnitPublisher(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that configures the unit-test publisher.

    :ivar str boost_patterns:
        File patterns to find Boost-Test files.

    :ivar str jsunit_patterns:
        File patterns to find JSUnit files.

    :ivar str junit_patterns:
        File patterns to find JUnit files.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER

    def __init__(self):
        self.boost_patterns = ''
        self.jsunit_patterns = ''
        self.junit_patterns = ''


    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        types = {
            'BoostTestJunitHudsonTestType' : self.boost_patterns,
            'JSUnitPluginType' : self.jsunit_patterns,
            'JUnitType' : self.junit_patterns,
        }
        if not any(types.values()):
            return

        for pattern_plugin, pattern in types.iteritems():
            if not pattern:
                continue
            plugin_xml = xml_factory['xunit/types/' + pattern_plugin]
            plugin_xml['pattern'] = ' '.join(pattern)
            plugin_xml['skipNoTestFiles'] = 'true'
            plugin_xml['failIfNotNew'] = 'false'
            plugin_xml['deleteOutputFiles'] = 'true'
            plugin_xml['stopProcessingIfError'] = 'true'

        xml_factory['xunit/thresholds/org.jenkinsci.plugins.xunit.threshold.FailedThreshold/unstableThreshold'] = '0'
        xml_factory['xunit/thresholds/org.jenkinsci.plugins.xunit.threshold.FailedThreshold/unstableNewThreshold'] = '0'
        xml_factory['xunit/thresholdMode'] = '1'



#===================================================================================================
# Timeout
#===================================================================================================
@PyJenkinsPlugin('timeout')
class Timeout(BaseJenkinsJobGeneratorPlugin):
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



#===================================================================================================
# ChoiceParameter
#===================================================================================================
@PyJenkinsPlugin('choice-parameter')
class ChoiceParameter(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that configures a choice parameter.

    :ivar str name:
        The name of the parameter. Usually PARAM_XXX

    :ivar str description:
        The description of the parameter

    :ivar list(str) choices:
        List of possible values. The first is the default.
    '''
    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_PARAMETER

    def __init__(self, param_name, description, choices):
        self.param_name = param_name
        self.description = description
        self.choices = choices

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        p = xml_factory['properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions/' \
            'hudson.model.ChoiceParameterDefinition+']
        p['name'] = self.param_name
        p['description'] = self.description
        p['choices@class'] = 'java.util.Arrays$ArrayList'
        p['choices/a@class'] = 'string-array'
        for i_choice in self.choices:
            p['choices/a/string+'] = i_choice



#===================================================================================================
# StringParameter
#===================================================================================================
@PyJenkinsPlugin('string-parameter')
class StringParameter(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that configures a string parameter.

    :ivar str name:
        The name of the parameter. Usually PARAM_XXX

    :ivar str description:
        The description of the parameter

    :ivar str default:
        Default value for parameter.

    '''
    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_PARAMETER

    def __init__(self, param_name, description, default=None):
        self.param_name = param_name
        self.description = description
        self.default = default

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        p = xml_factory['properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions/' \
            'hudson.model.StringParameterDefinition+']
        p['name'] = self.param_name
        p['description'] = self.description
        if self.default:
            p['defaultValue'] = self.default



#===================================================================================================
# Cron
#===================================================================================================
@PyJenkinsPlugin('cron')
class Cron(BaseJenkinsJobGeneratorPlugin):
    '''
    Configures a job to run based on a schedule

    :ivar str schedule:
        Cron configurations using a format employed by Jenkins.
    '''
    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_TRIGGER

    def __init__(self, schedule):
        self.schedule = schedule

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        xml_factory['hudson.triggers.TimerTrigger/spec'] = self.schedule

