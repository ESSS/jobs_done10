'''
Module containing everything related to Jenkins in jobs_done10.

This includes a generator, job publishers, constants and command line interface commands.
'''
from __future__ import absolute_import, unicode_literals

import io
from collections import namedtuple

from jobs_done10.common import AsList



#===================================================================================================
# JenkinsJob
#===================================================================================================
#
# Represents a Jenkins job.
#
# :cvar unicode name:
#     Job name
#
# :cvar Repository repository:
#     Repository that this job belongs to
#
# :cvar unicode xml:
#     Job XML contents
JenkinsJob = namedtuple('JenkinsJob', 'name repository xml')



#===================================================================================================
# JenkinsXmlJobGenerator
#===================================================================================================
class JenkinsXmlJobGenerator(object):
    '''
    Generates Jenkins jobs.
    '''

    def __init__(self):
        # Initialize some variables
        self.__jjgen = None
        self.__scm_plugin = None

        self.repository = None


    def Reset(self):
        from jobs_done10.xml_factory import XmlFactory

        self.xml = XmlFactory('project')
        self.xml['description'] = "<!-- Managed by Job's Done -->"
        self.xml['keepDependencies'] = xmls(False)
        self.xml['logRotator/daysToKeep'] = 7
        self.xml['logRotator/numToKeep'] = -1
        self.xml['logRotator/artifactDaysToKeep'] = -1
        self.xml['logRotator/artifactNumToKeep'] = -1
        self.xml['blockBuildWhenDownstreamBuilding'] = xmls(False)
        self.xml['blockBuildWhenUpstreamBuilding'] = xmls(False)
        self.xml['concurrentBuild'] = xmls(False)
        self.xml['canRoam'] = xmls(False)

        # Configure git SCM
        self.git = self.xml['scm']
        self.git['@class'] = 'hudson.plugins.git.GitSCM'

        self.SetGit(dict(
            url=self.repository.url,
            target_dir=self.repository.name,
            branch=self.repository.branch
        ))

        self.job_name = None


    @classmethod
    def GetJobGroup(cls, repository):
        '''
        A single repository/branch combination can create many jobs, depending on the job matrix.

        This variable is used to identify jobs within the same group.

        :param Repository repository:
            A repository that can contain jobs

        :returns unicode:
            Job group for the given repository
        '''
        return repository.name + '-' + repository.branch


    def GetJob(self):
        '''
        :return JenkinsJob:
            Job created by this generator.
        '''
        # Mailer must always be at the end of the XML contents, otherwise Jenkins might try to
        # send emails before checking if tests passed.
        publishers = self.xml.root.find('publishers')
        if publishers is not None:
            mailer = publishers.find('hudson.tasks.Mailer')
            if mailer is not None:
                publishers.remove(mailer)
                publishers.append(mailer)

        return JenkinsJob(
            name=self.job_name,
            repository=self.repository,
            xml=self.xml.GetContents(xml_header=True)
        )



    #===============================================================================================
    # Configurator functions (.. seealso:: JobsDoneJob ivars for docs)
    #===============================================================================================
    def SetRepository(self, repository):
        self.repository = repository


    def SetMatrix(self, matrix, matrix_row):
        label_expression = self.repository.name
        self.job_name = self.GetJobGroup(self.repository)

        if matrix_row:
            row_representation = '-'.join([
                value for key, value \
                in sorted(matrix_row.items()) \

                # Matrix rows with only one possible value do not affect the representation
                if len(matrix[key]) > 1
            ])

            if row_representation:  # Might be empty
                label_expression += '-' + row_representation
                self.job_name += '-' + row_representation

        self.SetLabelExpression(label_expression)


    def SetAdditionalRepositories(self, repositories):
        # Remove current git configuration from xml
        self.xml.root.remove(self.git.root)

        # Create a MultiSCM block
        multi_scm = self.xml['scm']
        multi_scm['@class'] = 'org.jenkinsci.plugins.multiplescms.MultiSCM'

        # Add the current git implementation to multi_scm
        self.git.root.attrib = {}
        self.git.root.tag = 'hudson.plugins.git.GitSCM'
        multi_scm['scms'].root.append(self.git.root)

        # Replace main git with the one inside multi_scm
        self.git = multi_scm['scms/hudson.plugins.git.GitSCM']

        # Add additional repositories
        for repo in repositories:
            self.SetGit(repo['git'], git_xml=multi_scm['scms/hudson.plugins.git.GitSCM+'])



    def SetAuthToken(self, auth_token):
        self.xml['authToken'] = auth_token


    def SetBoosttestPatterns(self, boosttest_patterns):
        self._SetXunit('BoostTestJunitHudsonTestType', boosttest_patterns)


    def SetBuildBatchCommands(self, build_batch_commands):
        for command in build_batch_commands:
            self.xml['builders/hudson.tasks.BatchFile+/command'] = command


    def SetBuildShellCommands(self, build_shell_commands):
        for command in build_shell_commands:
            self.xml['builders/hudson.tasks.Shell+/command'] = command


    def SetBuildPythonCommands(self, build_shell_commands):
        for command in build_shell_commands:
            self.xml['builders/hudson.plugins.python.Python+/command'] = command


    def SetCron(self, schedule):
        self.xml['triggers/hudson.triggers.TimerTrigger/spec'] = schedule


    def SetDescriptionRegex(self, description_regex):
        description_setter = self.xml['publishers/hudson.plugins.descriptionsetter.DescriptionSetterPublisher']
        description_setter['regexp'] = description_regex
        description_setter['regexpForFailed'] = description_regex
        description_setter['setForMatrix'] = xmls(False)


    def SetDisplayName(self, display_name):
        self.xml['displayName'] = display_name


    def SetEmailNotification(self, notification_info):
        mailer = self.xml['publishers/hudson.tasks.Mailer']

        # Handle short mode where user only gives a list of recipients
        if isinstance(notification_info, basestring):
            notification_info = {'recipients' : notification_info}

        mailer['recipients'] = notification_info.pop('recipients')

        notify_every_build = notification_info.pop('notify_every_build', xmls(False))
        if notify_every_build in ['False', 'false']:
            mailer['dontNotifyEveryUnstableBuild'] = xmls(True)
        else:
            mailer['dontNotifyEveryUnstableBuild'] = xmls(False)
        mailer['sendToIndividuals'] = xmls(notification_info.pop('notify_individuals', xmls(False)))

        self._CheckUnknownOptions('email_notification', notification_info)


    def SetGit(self, git_options, git_xml=None):
        '''
        Sets git options

        :param dict git_options:
            Options that will be set in git

        :param None|xml_factory._xml_factory.XmlFactory git_xml:
            Target XmlFactory object to set options.
            If None, will use the main project's Xml (`self.git`)
        '''
        if git_xml is None:
            git_xml = self.git

        git_xml['configVersion'] = '2'

        def _Set(option, xml_path, default=None):
            value = git_options.pop(option, default)
            if value is not None:
                for xml_path in AsList(xml_path):
                    git_xml[xml_path] = value

        # Git branch option is set in many places
        branch_paths = [
            'branches/hudson.plugins.git.BranchSpec/name',  # Branch being built
            'extensions/hudson.plugins.git.extensions.impl.LocalBranch/localBranch',  # Checkout to local branch (GitPlugin 2.0+)
            'localBranch',  # Checkout to local branch (GitPlugin 1.5)
        ]

        # Set all options --------------------------------------------------------------------------
        # Try to obtain a default target_dir based on repository name
        if 'url' in git_options:
            from jobs_done10.repository import Repository
            repository = Repository(url=git_options['url'])
            _Set('target_dir', 'relativeTargetDir', default=repository.name)
        else:
            _Set('target_dir', 'relativeTargetDir')

        _Set('remote', 'userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/name')
        _Set('refspec', 'userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/refspec')
        _Set('url', 'userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url')
        _Set('branch', branch_paths)
        _Set('recursive_submodules', 'extensions/hudson.plugins.git.extensions.impl.SubmoduleOption/recursiveSubmodules')
        _Set('shallow_clone', 'extensions/hudson.plugins.git.extensions.impl.CloneOption/shallow')
        _Set('reference', 'extensions/hudson.plugins.git.extensions.impl.CloneOption/reference')
        _Set('timeout', 'extensions/hudson.plugins.git.extensions.impl.CloneOption/timeout')

        self._CheckUnknownOptions('git', git_options)


    def SetJunitPatterns(self, junit_patterns):
        self._SetXunit('JUnitType', junit_patterns)


    def SetJsunitPatterns(self, jsunit_patterns):
        self._SetXunit('JSUnitPluginType', jsunit_patterns)


    def SetLabelExpression(self, label_expression):
        self.xml['assignedNode'] = label_expression


    def SetNotifyStash(self, args):
        notifier = self.xml['publishers/org.jenkinsci.plugins.stashNotifier.StashNotifier']

        if isinstance(args, basestring):
            # Happens when no parameter is given, we just set the URL and assume that
            # username/password if the default configuration set in Jenkins server
            notifier['stashServerBaseUrl'] = args
        else:  # dict
            notifier['stashServerBaseUrl'] = args.pop('url')
            notifier['stashUserName'] = args.pop('username', '')
            notifier['stashUserPassword'] = args.pop('password', '')

            self._CheckUnknownOptions('notify_stash', args)


    def SetParameters(self, parameters):
        parameters_xml = self.xml['properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions']
        for i_parameter in parameters:
            for name, j_dict  in i_parameter.iteritems():
                if name == 'choice':
                    p = parameters_xml['hudson.model.ChoiceParameterDefinition+']
                    p['choices@class'] = 'java.util.Arrays$ArrayList'
                    p['choices/a@class'] = 'string-array'
                    for k_choice in j_dict['choices']:
                        p['choices/a/string+'] = k_choice

                elif name == 'string':
                    p = parameters_xml['hudson.model.StringParameterDefinition+']
                    if j_dict['default']:
                        p['defaultValue'] = j_dict['default']

                # Common options
                p['name'] = j_dict['name']
                p['description'] = j_dict['description']


    def SetScmPoll(self, schedule):
        self.xml['triggers/hudson.triggers.SCMTrigger/spec'] = schedule


    def SetTimeout(self, timeout):
        timeout_xml = self.xml['buildWrappers/hudson.plugins.build__timeout.BuildTimeoutWrapper']
        timeout_xml['timeoutMinutes'] = unicode(timeout)
        timeout_xml['failBuild'] = xmls(True)


    def SetTimeoutNoActivity(self, timeout):
        timeout_xml = self.xml['buildWrappers/hudson.plugins.build__timeout.BuildTimeoutWrapper']
        timeout_xml['strategy@class'] = 'hudson.plugins.build_timeout.impl.NoActivityTimeOutStrategy'
        timeout_xml['strategy/timeoutSecondsString'] = timeout
        timeout_xml['operationList/hudson.plugins.build__timeout.operations.FailOperation']


    def SetCustomWorkspace(self, custom_workspace):
        self.xml['customWorkspace'] = custom_workspace


    def SetSlack(self, options):
        room = options.get('room', 'general')

        properties = self.xml['properties/jenkins.plugins.slack.SlackNotifier_-SlackJobProperty']
        properties['@plugin'] = 'slack@1.2'
        properties['room'] = '#' + room
        properties['startNotification'] = 'true'
        properties['notifySuccess'] = 'true'
        properties['notifyAborted'] = 'true'
        properties['notifyNotBuilt'] = 'true'
        properties['notifyUnstable'] = 'true'
        properties['notifyFailure'] = 'true'
        properties['notifyBackToNormal'] = 'true'

        publisher = self.xml['publishers/jenkins.plugins.slack.SlackNotifier']
        publisher['@plugin'] = "slack@1.2"
        publisher['teamDomain'] = options['team']
        publisher['authToken'] = options['token']
        publisher['buildServerUrl'] = options['url']
        publisher['room'] = '#' + room


    def SetNotification(self, options):
        properties = self.xml['properties/com.tikal.hudson.plugins.notification.HudsonNotificationProperty']
        properties['@plugin'] = 'notification@1.9'
        endpoint = properties['endpoints/com.tikal.hudson.plugins.notification.Endpoint']
        endpoint['protocol'] = options.get('protocol', 'HTTP')
        endpoint['format'] = options.get('format', 'JSON')
        endpoint['url'] = options['url']
        endpoint['event'] = 'all'
        endpoint['timeout'] = '30000'
        endpoint['loglines'] = '1'


    # Internal functions ---------------------------------------------------------------------------
    def _SetXunit(self, xunit_type, patterns):
        # Set common xunit patterns
        xunit = self.xml['publishers/xunit']
        xunit['thresholds/org.jenkinsci.plugins.xunit.threshold.FailedThreshold/unstableThreshold'] = '0'
        xunit['thresholds/org.jenkinsci.plugins.xunit.threshold.FailedThreshold/unstableNewThreshold'] = '0'
        xunit['thresholdMode'] = '1'

        # Set patterns for the given type
        xunit_type_xml = xunit['types/' + xunit_type]
        xunit_type_xml['pattern'] = ','.join(patterns)
        xunit_type_xml['skipNoTestFiles'] = xmls(True)
        xunit_type_xml['failIfNotNew'] = xmls(False)
        xunit_type_xml['deleteOutputFiles'] = xmls(True)
        xunit_type_xml['stopProcessingIfError'] = xmls(True)

        # Add a cleanup sequence to delete all test results when a build starts
        cleanup = self.xml['buildWrappers/hudson.plugins.ws__cleanup.PreBuildCleanup']
        for pattern in patterns:
            pattern_tag = cleanup['patterns/hudson.plugins.ws__cleanup.Pattern+']
            pattern_tag['pattern'] = pattern
            pattern_tag['type'] = 'INCLUDE'


    def _CheckUnknownOptions(self, configuration_name, options_dict):
        if len(options_dict) > 0:
            raise RuntimeError('Received unknown %s options: %s' % (configuration_name, options_dict.keys()))



#===================================================================================================
# Utils
#===================================================================================================
def _AsXmlString(boolean):
    '''
    :param bool boolean:
        True or False

    :return unicode:
        `boolean` representation as a string used by Jenkins XML
    '''
    return unicode(boolean).lower()
xmls = _AsXmlString



#===================================================================================================
# JenkinsJobPublisher
#===================================================================================================
class JenkinsJobPublisher(object):
    '''
    Publishes `JenkinsJob`s
    '''
    # Times to retry on ProxyErrors
    RETRIES = 3

    # Times to sleep (seconds) between each retry
    RETRY_SLEEP = 1

    def __init__(self, repository, jobs):
        '''
        :param Repository repository:
            Repository used for these jobs. Used to find other jobs in the same url/branch to be
            updated or deleted.

        :param list(JenkinsJob) jobs:
            List of jobs to be published.
        '''
        for job in jobs:
            assert job.repository == repository, +\
                'All published jobs must belong to the given `repository`'

        self.repository = repository
        self.jobs = dict((job.name, job) for job in jobs)


    def PublishToUrl(self, url, username=None, password=None):
        '''
        Publishes new jobs, updated existing jobs, and delete jobs that belong to the same
        repository/branch but were not updated.

        :param unicode url:
            Jenkins instance URL where jobs will be uploaded to.

        :param unicode username:
            Jenkins username.

        :param unicode password:
            Jenkins password.

        :return tuple(list(unicode),list(unicode),list(unicode)):
            Tuple with lists of {new, updated, deleted} job names (sorted alphabetically)
        '''
        import jenkins
        jenkins_api = jenkins.Jenkins(url, username, password)

        # Get all jobs
        job_names = set(self.jobs.keys())
        matching_jobs = self._GetMatchingJobs(jenkins_api)

        # Find all new/updated/deleted jobs
        new_jobs = job_names.difference(matching_jobs)
        updated_jobs = job_names.intersection(matching_jobs)
        deleted_jobs = matching_jobs.difference(job_names)

        def retry(func, *args, **kwargs):
            from requests.exceptions import HTTPError
            for _ in range(self.RETRIES):
                try:
                    func(*args, **kwargs)
                    break
                except HTTPError as http_error:
                    if http_error.response.status_code == 403:  # Proxy error
                        # This happens sometimes for no apparent reason, and we want to retry.
                        from time import sleep
                        sleep(self.RETRY_SLEEP)
                    else:
                        raise http_error
            else:
                # If we got here, this mean we ran out of retries. Raise the last error we received.
                raise http_error

        # Process everything
        for job_name in new_jobs:
            retry(jenkins_api.job_create, job_name, self.jobs[job_name].xml)

        for job_name in updated_jobs:
            retry(jenkins_api.job_reconfigure, job_name, self.jobs[job_name].xml)

        for job_name in deleted_jobs:
            retry(jenkins_api.job_delete, job_name)

        return map(sorted, (new_jobs, updated_jobs, deleted_jobs))


    def PublishToDirectory(self, output_directory):
        '''
        Publishes jobs to a directory. Each job creates a file with its name and xml contents.

        :param unicode output_directory:
             Target directory for outputting job .xmls
        '''
        import os
        for job in self.jobs.values():
            with io.open(os.path.join(output_directory, job.name), 'w', encoding='utf-8') as f:
                f.write(job.xml)


    def _GetMatchingJobs(self, jenkins_api):
        '''
        Filter jobs that belong to the same repository/branch as a `job` being published

        :param jenkins_api:
            Configured Jenkins API that gives access to Jenkins data at a host.

        :return set(unicode):
            Names of all Jenkins jobs that match `job` repository name and branch
        '''
        matching_jobs = set()

        for jenkins_job in jenkins_api.jobnames:
            # Filter jobs that belong to this repository (this would be safer to do reading SCM
            # information, but a lot more expensive
            common_prefix = self.repository.name + '-' + self.repository.branch
            if not jenkins_job.startswith(common_prefix):
                continue

            jenkins_job_branch = self._GetJenkinsJobBranch(jenkins_api, jenkins_job)
            if jenkins_job_branch == self.repository.branch:
                matching_jobs.add(jenkins_job)

        return matching_jobs


    def _GetJenkinsJobBranch(self, jenkins_api, jenkins_job):
        '''
        :param jenkins.Jenkins jenkins_api:
            Configured Jenkins API that gives access to Jenkins data at a host.

        :param unicode jenkins_job:
            Name of a job in jenkins

        :return unicode:
            Name of `jenkins_job`s branch

        .. note::
            This function was separated to make use of Memoize cacheing, avoiding multiple queries
            to the same jenkins job config.xml
        '''
        from xml.etree import ElementTree

        # Read config to see if this job is in the same branch
        config = jenkins_api.job_config(jenkins_job)

        # We should be able to get this information from jenkins API, but it seems that git
        # plugin for Jenkins has a bug that prevents its data from being shown in the API
        # https://issues.jenkins-ci.org/browse/JENKINS-14588
        root = ElementTree.fromstring(config)

        # Try for single SCM
        name_element = root.find('scm/branches/hudson.plugins.git.BranchSpec/name')
        if name_element is not None:
            return name_element.text.strip()

        # If the above was not found, we might be dealing with multiple repositories
        scms = root.findall('scm/scms/hudson.plugins.git.GitSCM')

        # Process them all until we find the SCM for the correct repository
        for scm in scms:
            url = scm.find('userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url').text.strip()

            if url == self.repository.url:
                return scm.find('branches/hudson.plugins.git.BranchSpec/name').text.strip()

        raise RuntimeError(
            'Could not find SCM for repository "%s" in job "%s"' % (self.repository.url, jenkins_job)
        )



#===================================================================================================
# Actions for common uses of Jenkins classes
#===================================================================================================
def UploadJobsFromFile(repository, jobs_done_file_contents, url, username=None, password=None):
    '''
    :param repository:
        .. seealso:: GetJobsFromFile

    :param jobs_done_file_contents:
        .. seealso:: GetJobsFromFile

    :param unicode url:
        URL of a Jenkins sevrer instance where jobs will be uploaded

    :param unicode|None username:
        Username for Jenkins server.

    :param unicode|None password:
        Password for Jenkins server.

    :returns:
        .. seealso:: JenkinsJobPublisher.PublishToUrl

    '''
    jobs = GetJobsFromFile(repository, jobs_done_file_contents)
    publisher = JenkinsJobPublisher(repository, jobs)

    return publisher.PublishToUrl(url, username, password)



def GetJobsFromDirectory(directory='.'):
    '''
    Looks in a directory for a jobs_done file and git repository information to create jobs.

    :param directory:
        Directory where we'll extract information to generate `JenkinsJob`s

    :return tuple(Repository,set(JenkinsJob))
        Repository information for the given directory, and jobs obtained from this directory.

        .. seealso:: GetJobsFromFile
    '''
    from jobs_done10.jobs_done_job import JOBS_DONE_FILENAME
    from jobs_done10.repository import Repository
    import os

    from subprocess import check_output
    url = check_output('git config --local --get remote.origin.url', shell=True, cwd=directory).strip()
    branches = check_output('git branch', shell=True, cwd=directory).strip()
    for branch in branches.splitlines():
        branch = branch.strip()
        if '*' in branch:  # Current branch
            branch = branch.split(' ', 1)[1]
            break
    else:
        raise RuntimeError('Error parsing output from git branch')

    repository = Repository(url=url, branch=branch)
    try:
        with io.open(os.path.join(directory, JOBS_DONE_FILENAME), encoding='utf-8') as f:
            jobs_done_file_contents = f.read()
    except IOError:
        jobs_done_file_contents = None

    return repository, GetJobsFromFile(repository, jobs_done_file_contents)



def GetJobsFromFile(repository, jobs_done_file_contents):
    '''
    Creates jobs from repository information and a jobs_done file.

    :param Repository repository:
        .. seealso:: Repository

    :param unicode|None jobs_done_file_contents:
        .. seealso:: JobsDoneJob.CreateFromYAML

    :return set(JenkinsJob)
    '''
    from jobs_done10.job_generator import JobGeneratorConfigurator
    from jobs_done10.jobs_done_job import JobsDoneJob

    jenkins_generator = JenkinsXmlJobGenerator()

    jobs = []
    jobs_done_jobs = JobsDoneJob.CreateFromYAML(jobs_done_file_contents, repository)
    for jobs_done_job in jobs_done_jobs:
        JobGeneratorConfigurator.Configure(jenkins_generator, jobs_done_job)
        jobs.append(jenkins_generator.GetJob())

    return jobs



#===================================================================================================
# ConfigureCommandLineInterface
#===================================================================================================
def ConfigureCommandLineInterface(jobs_done_application):
    '''
    Configures additional command line commands to the jobs_done application.

    :param App jobs_done_application:
        Command line application we are registering commands to.
    '''
    @jobs_done_application
    def jenkins(console_, url, username=None, password=None):
        '''
        Creates jobs for Jenkins and push them to a Jenkins instance.

        If no parameters are given, this command will look for a configuration file that defines a
        target url/username/password.

        :param url: Jenkins instance URL where jobs will be uploaded to.

        :param username: Jenkins username.

        :param password: Jenkins password.
        '''
        console_.Print('Publishing jobs in "<white>%s</>"' % url)

        repository, jobs = GetJobsFromDirectory()
        publisher = JenkinsJobPublisher(repository, jobs)
        new_jobs, updated_jobs, deleted_jobs = publisher.PublishToUrl(url, username, password)

        for job in new_jobs:
            console_.Print('<green>NEW</> - ' + job)
        for job in updated_jobs:
            console_.Print('<yellow>UPD</> - ' + job)
        for job in deleted_jobs:
            console_.Print('<red>DEL</> - ' + job)


    @jobs_done_application
    def jenkins_test(console_, output_directory):
        '''
        Creates jobs for Jenkins and save the resulting .xml's in a directory

        :param output_directory: Directory to output job xmls instead of uploading to `url`.
        '''
        console_.Print('Saving jobs in "%s"' % output_directory)

        repository, jobs = GetJobsFromDirectory()
        publisher = JenkinsJobPublisher(repository, jobs)
        publisher.PublishToDirectory(output_directory)

        console_.ProgressOk()
