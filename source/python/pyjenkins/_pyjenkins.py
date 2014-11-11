from __future__ import unicode_literals
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

    :ivar unicode job_name:
        Determines the job name

    :ivar unicode description:
        The job description.

    :ivar unicode display_name:
        The job display-name. This value can use attribute replacement such as %(name)s

    :ivar unicode label_expression:
        This must match the execution nodes configuration in order to be built on that node.

    :ivar int days_to_keep:
        Number of days to keep the job history.

    :ivar int num_to_keep:
        Number of history entries to keep.

    :ivar int timeout:
        Job build timeout in minutes. After the timeout the job automatically fails
    '''
    CONFIG_FILENAME = 'config.xml'

    DEFAULT_LABEL_EXPRESSION = ''

    PLUGINS = {}

    def __init__(self, job_name):
        self.job_name = job_name
        self.description = ''
        self.display_name = ''
        self.custom_workspace = ''
        self.auth_token = ''
        self.label_expression = self.DEFAULT_LABEL_EXPRESSION
        self.days_to_keep = 7
        self.num_to_keep = -1
        self.timeout = None

        from ben10.foundation.odict import odict
        self.__plugins = odict()  # Use odict to maintain order


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

        # Sort plugins because some might require a defined order among them
        return sorted(plugins)


    # Job ------------------------------------------------------------------------------------------
    def GetContent(self):
        '''
        Returns the configuration file XML contents.

        :return unicode:
        '''
        from xml_factory import XmlFactory

        xml_factory = XmlFactory('project')
        xml_factory['actions']
        xml_factory['description'] = self.description

        if self.auth_token:
            xml_factory['authToken'] = self.auth_token
        if self.custom_workspace:
            xml_factory['customWorkspace'] = self.custom_workspace % self.__dict__
        if self.display_name:
            xml_factory['displayName'] = self.display_name % self.__dict__

        xml_factory['keepDependencies'] = _ToString(False)
        xml_factory['blockBuildWhenDownstreamBuilding'] = _ToString(False)
        xml_factory['blockBuildWhenUpstreamBuilding'] = _ToString(False)
        xml_factory['concurrentBuild'] = _ToString(False)
        xml_factory['assignedNode'] = self.label_expression % self.__dict__
        xml_factory['canRoam'] = _ToString(False)

        # Log Rotator
        xml_factory['logRotator/daysToKeep'] = self.days_to_keep
        xml_factory['logRotator/numToKeep'] = self.num_to_keep
        xml_factory['logRotator/artifactDaysToKeep'] = -1
        xml_factory['logRotator/artifactNumToKeep'] = -1

        # Parameters
        for i_parameter_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_PARAMETER):
            i_parameter_plugin.Create(xml_factory)

        # Configure SCM
        for i_scm_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_SCM):
            i_scm_plugin.Create(xml_factory)

        xml_factory['blockBuildWhenDownstreamBuilding'] = _ToString(False)
        xml_factory['blockBuildWhenUpstreamBuilding'] = _ToString(False)
        xml_factory['concurrentBuild'] = _ToString(False)

        builders_xml = xml_factory[IJenkinsJobGeneratorPlugin.TYPE_BUILDER]
        for i_builder_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_BUILDER):
            i_builder_plugin.Create(builders_xml)

        publishers_xml = xml_factory[IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER]
        for i_publisher_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER):
            i_publisher_plugin.Create(publishers_xml)

        build_wrappers_xml = xml_factory[IJenkinsJobGeneratorPlugin.TYPE_BUILD_WRAPPER]
        for i_build_wrapper_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_BUILD_WRAPPER):
            i_build_wrapper_plugin.Create(build_wrappers_xml)

        triggers_xml = xml_factory[IJenkinsJobGeneratorPlugin.TYPE_TRIGGER]
        for i_trigger_plugin in self.ListPlugins(IJenkinsJobGeneratorPlugin.TYPE_TRIGGER):
            i_trigger_plugin.Create(triggers_xml)

        return xml_factory.GetContents(xml_header=True)


    def CreateConfigFile(self, config_filename):
        '''
        Create the job configuration file with the given filename.

        :param unicode config_file:
            The configuration filename.
        '''
        from ben10.filesystem._filesystem import CreateFile
        CreateFile(config_filename, self.GetContent())



#===================================================================================================
# _ToString
#===================================================================================================
def _ToString(boolean):
    '''
    :param bool boolean:
        True or False

    :return unicode:
        `boolean` representation as a string used by Jenkins XML
    '''
    return unicode(boolean).lower()


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

    :param unicode plugin_name:
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

    :ivar unicode url:
        The git repository URL.

    :ivar unicode target_dir:
        The target directory for the working copy.
        Defaults to "" which means that the workspace directory will be the working copy.

    :ivar unicode branch:
        The branch to build.
        Default to "master"

    :ivar unicode remote:
        The name of the git remote to configure.
        Default to "origin"

    :ivar unicode refspec:
        "A refspec controls the remote refs to be retrieved and how they map to local refs."
        Default to "+refs/heads/*:refs/remotes/origin/*"

    :ivar bool shallow_clone:
        Perform shallow clone, so that git will not download history of the project, saving time and
        disk space when you just want to access the latest version of a repository.

    :ivar unicode reference:
        Specify a folder containing a repository that will be used by Git as a reference during
        clone operations.

        This option will be ignored if the folder is not available on the master or slave where the
        clone is being executed.

    :ivar int timeout:
        Specify a timeout (in minutes) for clone and fetch operations.
        This option overrides the default timeout defined in Jenkins.

    :ivar bool recursive_submodules:
        Retrieve all submodules recursively (uses '--recursive' option which requires git>=1.6.5)

    :ivar bool multi_scm:
        If True, uses syntax for multiple repositories.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_SCM

    def __init__(
        self,
        url=None,
        target_dir=None,
        branch='master',
        remote='origin',
        refspec='+refs/heads/*:refs/remotes/origin/*',
        shallow_clone=False,
        reference=None,
        timeout=None,
        recursive_submodules=False,
        multi_scm=False):
        self.url = url
        self.target_dir = target_dir
        self.branch = branch
        self.remote = remote
        self.refspec = refspec
        self.shallow_clone = shallow_clone
        self.reference = reference
        self.timeout = timeout
        self.recursive_submodules = recursive_submodules
        self.multi_scm = multi_scm


    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        if self.multi_scm:
            xml_factory['scm@class'] = 'org.jenkinsci.plugins.multiplescms.MultiSCM'
            scm_config = xml_factory['scm/scms/hudson.plugins.git.GitSCM+']
        else:
            xml_factory['scm@class'] = 'hudson.plugins.git.GitSCM'
            scm_config = xml_factory['scm']

        scm_config['configVersion'] = '2'
        scm_config['userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/name'] = self.remote
        scm_config['userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/refspec'] = self.refspec
        scm_config['userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url'] = self.url
        scm_config['branches/hudson.plugins.git.BranchSpec/name'] = self.branch

        if self.target_dir:
            scm_config['relativeTargetDir'] = self.target_dir

        # Checkout to local branch is done twice to work with different versions of plugin (2.0+, 1.5)
        scm_config['extensions/hudson.plugins.git.extensions.impl.LocalBranch/localBranch'] = self.branch
        scm_config['localBranch'] = self.branch

        if self.recursive_submodules:
            scm_config['extensions/hudson.plugins.git.extensions.impl.SubmoduleOption/recursiveSubmodules'] = _ToString(self.recursive_submodules)

        if self.shallow_clone:
            scm_config['extensions/hudson.plugins.git.extensions.impl.CloneOption/shallow'] = _ToString(self.shallow_clone)

        if self.reference:
            scm_config['extensions/hudson.plugins.git.extensions.impl.CloneOption/reference'] = self.reference

        if self.timeout:
            scm_config['extensions/hudson.plugins.git.extensions.impl.CloneOption/timeout'] = unicode(self.timeout)



#===================================================================================================
# ShellBuilder
#===================================================================================================
@PyJenkinsPlugin('shell')
class ShellBuilder(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that adds a shell (linux) command shell.

    :ivar list(unicode) command_lines:
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
# PythonBuilder
#===================================================================================================
@PyJenkinsPlugin('python')
class PythonBuilder(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that adds a python commands to build steps.

    Requires https://wiki.jenkins-ci.org/display/JENKINS/Python+Plugin

    :ivar list(unicode) command_lines:
        Command lines to execute.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_BUILDER

    def __init__(self, command):
        self.command = command

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        xml_factory['hudson.plugins.python.Python+/command'] = self.command



#===================================================================================================
# BatchBuilder
#===================================================================================================
@PyJenkinsPlugin('batch')
class BatchBuilder(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that adds a batch (windows) command.

    :ivar list(unicode) command_lines:
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

    :ivar unicode regexp:
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
        xml_factory['hudson.plugins.descriptionsetter.DescriptionSetterPublisher/setForMatrix'] = _ToString(False)



#===================================================================================================
# StashNotifier
#===================================================================================================
@PyJenkinsPlugin('stash-notifier')
class StashNotifier(BaseJenkinsJobGeneratorPlugin):
    '''
    Notifies Stash instances when a build passes

    :ivar unicode url:
        Stash URL

    :ivar unicode username:

    :ivar unicode password:
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER

    # StashNotifier must always be the last plugin when compared to other plugins, to make sure that
    # things such as test result publisher are executed before this, otherwise, builds with failed
    # tests might be reported as successful to Stash.
    PRIORITY = 2

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

    :ivar unicode boost_patterns:
        File patterns to find Boost-Test files.

    :ivar unicode jsunit_patterns:
        File patterns to find JSUnit files.

    :ivar unicode junit_patterns:
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

        for pattern_plugin, pattern in types.iteritems():
            if not pattern:
                continue
            plugin_xml = xml_factory['xunit/types/' + pattern_plugin]
            plugin_xml['pattern'] = ','.join(pattern)
            plugin_xml['skipNoTestFiles'] = _ToString(True)
            plugin_xml['failIfNotNew'] = _ToString(False)
            plugin_xml['deleteOutputFiles'] = _ToString(True)
            plugin_xml['stopProcessingIfError'] = _ToString(True)

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
        build_timeout_wrapper['timeoutMinutes'] = unicode(self.timeout)
        build_timeout_wrapper['failBuild'] = _ToString(True)



#===================================================================================================
# ChoiceParameter
#===================================================================================================
@PyJenkinsPlugin('choice-parameter')
class ChoiceParameter(BaseJenkinsJobGeneratorPlugin):
    '''
    A jenkins-job-generator plugin that configures a choice parameter.

    :ivar unicode name:
        The name of the parameter. Usually PARAM_XXX

    :ivar unicode description:
        The description of the parameter

    :ivar list(unicode) choices:
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

    :ivar unicode name:
        The name of the parameter. Usually PARAM_XXX

    :ivar unicode description:
        The description of the parameter

    :ivar unicode default:
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

    :ivar unicode schedule:
        Cron configurations using a format employed by Jenkins.
    '''
    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_TRIGGER

    def __init__(self, schedule):
        self.schedule = schedule

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        xml_factory['hudson.triggers.TimerTrigger/spec'] = self.schedule



#===================================================================================================
# SCMPoll
#===================================================================================================
@PyJenkinsPlugin('scm-poll')
class SMCPoll(BaseJenkinsJobGeneratorPlugin):
    '''
    Configures a job to poll SCM based on a schedule, and trigger a build if there are changes

    :ivar unicode schedule:
        Cron configurations using a format employed by Jenkins.
    '''
    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_TRIGGER

    def __init__(self, schedule):
        self.schedule = schedule

    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        xml_factory['hudson.triggers.SCMTrigger/spec'] = self.schedule



#===================================================================================================
# EmailNotification
#===================================================================================================
@PyJenkinsPlugin('email-notification')
class EmailNotification(BaseJenkinsJobGeneratorPlugin):
    '''
    Sends emails for failed builds.

    :ivar list(unicode) recipients:
        List of recipients receivers that will be informed of failed builds

    :ivar bool notify_every_build:
        If True, every failed build is notified (even when previous executions failed too)

    :ivar bool notify_individuals:
        If True, notifies individuals who broke the build.

        From Jenkins:

        If this option is checked, the notification e-mail will be sent to individuals who have
        committed changes for the broken build (by assuming that those changes broke the build).

        If e-mail addresses are also specified in the recipient list, then both the individuals
        as well as the specified addresses get the notification e-mail.

        If the recipient list is empty, then only the individuals will receive e-mails.
    '''

    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_PUBLISHER

    # EmailNotification has to be at the end of the plugin list, because we need to allow other
    # plugins (such as xunit) to fail a build before sending emails.
    PRIORITY = 1

    def __init__(self, recipients, notify_every_build, notify_individuals):
        self.recipients = recipients
        self.notify_every_build = notify_every_build
        self.notify_individuals = notify_individuals


    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        mailer = xml_factory['hudson.tasks.Mailer']
        mailer['recipients'] = ' '.join(self.recipients)
        mailer['dontNotifyEveryUnstableBuild'] = _ToString(False) if self.notify_every_build else _ToString(True)
        mailer['sendToIndividuals'] = _ToString(True) if self.notify_individuals else _ToString(False)



#===================================================================================================
# WorkspaceCleanup
#===================================================================================================
@PyJenkinsPlugin('workspace-cleanup')
class WorkspaceCleanup(BaseJenkinsJobGeneratorPlugin):
    '''
    Cleans up files in the workspace before running a build.

    The Jenkins plugins supports cleanup after build, but this is not implemented here yet.

    :ivar list(unicode) include_patterns:
        List of patterns for files to be deleted.

    :ivar list(unicode) exclude_patterns:
        List of patterns for files that must not be deleted.
    '''
    ImplementsInterface(IJenkinsJobGeneratorPlugin)

    TYPE = IJenkinsJobGeneratorPlugin.TYPE_BUILD_WRAPPER

    def __init__(self, include_patterns=None, exclude_patterns=None):

        if include_patterns is None:
            include_patterns = []
        if exclude_patterns is None:
            exclude_patterns = []

        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns


    @Implements(IJenkinsJobGeneratorPlugin.Create)
    def Create(self, xml_factory):
        cleanup = xml_factory['hudson.plugins.ws__cleanup.PreBuildCleanup']

        if self.include_patterns or self.exclude_patterns:
            for pattern in self.include_patterns:
                pattern_tag = cleanup['patterns/hudson.plugins.ws__cleanup.Pattern+']
                pattern_tag['pattern'] = pattern
                pattern_tag['type'] = 'INCLUDE'
            for pattern in self.exclude_patterns:
                pattern_tag = cleanup['patterns/hudson.plugins.ws__cleanup.Pattern+']
                pattern_tag['pattern'] = pattern
                pattern_tag['type'] = 'EXCLUDE'
