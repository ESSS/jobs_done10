'''
Module containing everything related to Jenkins in jobs_done10.

This includes a generator, job publishers, constants and command line interface commands.
'''
from __future__ import absolute_import
from ben10.foundation.bunch import Bunch
from ben10.foundation.decorators import Implements
from ben10.foundation.memoize import Memoize
from ben10.interface import ImplementsInterface
from jobs_done10.job_generator import IJobGenerator



#===================================================================================================
# JenkinsJob
#===================================================================================================
class JenkinsJob(Bunch):
    '''
    Represents a Jenkins job.

    :cvar str name:
        Job name

    :cvar Repository repository:
        Repository that this job belongs to

    :cvar str xml:
        Job XML contents
    '''
    name = None
    repository = None
    xml = None



#===================================================================================================
# JenkinsXmlJobGenerator
#===================================================================================================
class JenkinsXmlJobGenerator(object):
    '''
    Generates Jenkins jobs.
    '''
    ImplementsInterface(IJobGenerator)

    def __init__(self):
        # Initialize some variables
        self.__jjgen = None
        self.__scm_plugin = None

        self.repository = None


    @Implements(IJobGenerator.Reset)
    def Reset(self):
        from pyjenkins import JenkinsJobGenerator as PyJenkinsJobGenerator

        self.__jjgen = PyJenkinsJobGenerator(self.repository.name)

        # Configure description
        self.__jjgen.description = "<!-- Managed by Job's Done -->"

        # Configure git SCM
        self.__scm_plugin = self.__jjgen.CreatePlugin(
            'git',
            url=self.repository.url,
            target_dir=self.repository.name,
            branch=self.repository.branch
        )


    @classmethod
    def GetJobGroup(cls, repository):
        '''
        A single repository/branch combination can create many jobs, depending on the job matrix.

        This variable is used to identify jobs within the same group.

        :param Repository repository:
            A repository that can contain jobs

        :returns str:
            Job group for the given repository
        '''
        return repository.name + '-' + repository.branch


    def GetJob(self):
        '''
        :return JenkinsJob:
            Job created by this generator.
        '''
        return JenkinsJob(
            name=self.__jjgen.job_name,
            repository=self.repository,
            xml=self.__jjgen.GetContent(),
        )


    #===============================================================================================
    # Configurator functions (.. seealso:: JobsDoneJob ivars for docs)
    #===============================================================================================
    @Implements(IJobGenerator.SetRepository)
    def SetRepository(self, repository):
        self.repository = repository


    @Implements(IJobGenerator.SetMatrix)
    def SetMatrix(self, matrix, matrix_row):
        self.__jjgen.label_expression = self.repository.name
        self.__jjgen.job_name = self.GetJobGroup(self.repository)

        if matrix_row:
            row_representation = '-'.join([
                value for key, value \
                in sorted(matrix_row.items()) \

                # Matrix rows with only one possible value do not affect the representation
                if len(matrix[key]) > 1
            ])

            if row_representation:  # Might be empty
                self.__jjgen.label_expression += '-' + row_representation
                self.__jjgen.job_name += '-' + row_representation


    def SetAdditionalRepositories(self, repositories):
        # Convert our default scm plugin to MultiSCM
        self.__scm_plugin.multi_scm = True

        for repo_options in repositories:
            if 'git' in repo_options:
                plugin = self.__jjgen.CreatePlugin('git')
                plugin.multi_scm = True
                self._SetGitOptions(plugin, repo_options['git'])


    def SetBoosttestPatterns(self, boosttest_patterns):
        xunit_plugin = self.__jjgen.ObtainPlugin("xunit")
        xunit_plugin.boost_patterns = boosttest_patterns

        workspace_cleanup_plugin = self.__jjgen.ObtainPlugin('workspace-cleanup')
        workspace_cleanup_plugin.include_patterns += boosttest_patterns


    def SetBuildBatchCommands(self, build_batch_commands):
        for command in build_batch_commands:
            self.__jjgen.CreatePlugin("batch", command)


    def SetBuildShellCommands(self, build_shell_commands):
        for command in build_shell_commands:
            self.__jjgen.CreatePlugin("shell", command)


    def SetCron(self, schedule):
        self.__jjgen.CreatePlugin("cron", schedule)


    def SetDescriptionRegex(self, description_regex):
        if description_regex:
            self.__jjgen.CreatePlugin("description-setter", description_regex)


    def SetDisplayName(self, display_name):
        self.__jjgen.display_name = display_name


    def SetEmailNotification(self, args):
        if isinstance(args, basestring):
            # If args is a single string, use default options and just set email
            self.__jjgen.CreatePlugin(
                "email-notification",
                recipients=args.split(),
                notify_every_build=False,
                notify_individuals=False
            )
        else:
            # We got a dict
            from ben10.foundation.types_ import Boolean
            self.__jjgen.CreatePlugin(
                "email-notification",
                recipients=args.get('recipients', '').split(),
                notify_every_build=Boolean(args.get('notify_every_build', 'false')),
                notify_individuals=Boolean(args.get('notify_individuals', 'false')),
            )


    def SetGit(self, git_options):
        self._SetGitOptions(self.__scm_plugin, git_options)


    def SetJunitPatterns(self, junit_patterns):
        xunit_plugin = self.__jjgen.ObtainPlugin("xunit")
        xunit_plugin.junit_patterns = junit_patterns

        workspace_cleanup_plugin = self.__jjgen.ObtainPlugin('workspace-cleanup')
        workspace_cleanup_plugin.include_patterns += junit_patterns


    def SetJsunitPatterns(self, jsunit_patterns):
        xunit_plugin = self.__jjgen.ObtainPlugin("xunit")
        xunit_plugin.jsunit_patterns = jsunit_patterns

        workspace_cleanup_plugin = self.__jjgen.ObtainPlugin('workspace-cleanup')
        workspace_cleanup_plugin.include_patterns += jsunit_patterns


    def SetLabelExpression(self, label_expression):
        self.__jjgen.label_expression = label_expression


    def SetNotifyStash(self, args):
        if isinstance(args, basestring):
            # Happens when no parameter is given, indicating we want to use the default
            # configuration set in the Jenkins server
            self.__jjgen.CreatePlugin("stash-notifier")
        else:  # dict
            # Using parameters
            self.__jjgen.CreatePlugin("stash-notifier", **args)


    def SetParameters(self, parameters):
        for i_parameter in parameters:
            for name, j_dict  in i_parameter.iteritems():
                if name == 'choice':
                    self.__jjgen.CreatePlugin(
                        "choice-parameter",
                        param_name=j_dict['name'],
                        description=j_dict['description'],
                        choices=j_dict['choices'],
                    )
                elif name == 'string':
                    self.__jjgen.CreatePlugin(
                        "string-parameter",
                        param_name=j_dict['name'],
                        description=j_dict['description'],
                        default=j_dict['default'],
                    )


    def SetScmPoll(self, schedule):
        self.__jjgen.CreatePlugin("scm-poll", schedule)


    def SetTimeout(self, timeout):
        self.__jjgen.CreatePlugin("timeout", timeout)


    # Internal functions ---------------------------------------------------------------------------
    def _SetGitOptions(self, plugin, git_options):
        # Try to construct a Repository option from `git_options`, but fallback to current plugin
        # configuration if those options are not available
        from ben10.foundation.types_ import Boolean
        from jobs_done10.repository import Repository

        repo = Repository(
            url=git_options.get('url', plugin.url),
            branch=git_options.get('branch', plugin.branch)
        )

        plugin.url = repo.url
        plugin.branch = repo.branch
        plugin.target_dir = git_options.get('target-dir', repo.name)
        plugin.shallow_clone = Boolean(git_options.get('shallow-clone', 'false'))
        plugin.recursive_submodules = Boolean(git_options.get('recursive-submodules', 'false'))



#===================================================================================================
# JenkinsJobPublisher
#===================================================================================================
class JenkinsJobPublisher(object):
    '''
    Publishes `JenkinsJob`s
    '''
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

        :param str url:
            Jenkins instance URL where jobs will be uploaded to.

        :param str username:
            Jenkins username.

        :param str password:
            Jenkins password.

        :return tuple(list(str),list(str),list(str)):
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

        # Process everything
        for job_name in new_jobs:
            jenkins_api.create_job(job_name, self.jobs[job_name].xml)

        for job_name in updated_jobs:
            jenkins_api.reconfig_job(job_name, self.jobs[job_name].xml)

        for job_name in deleted_jobs:
            jenkins_api.delete_job(job_name)

        return map(sorted, (new_jobs, updated_jobs, deleted_jobs))


    def PublishToDirectory(self, output_directory):
        '''
        Publishes jobs to a directory. Each job creates a file with its name and xml contents.

        :param str output_directory:
             Target directory for outputting job .xmls
        '''
        from ben10.filesystem import CreateFile
        import os
        for job in self.jobs.values():
            CreateFile(
                filename=os.path.join(output_directory, job.name),
                contents=job.xml
            )


    def _GetMatchingJobs(self, jenkins_api):
        '''
        Filter jobs that belong to the same repository/branch as a `job` being published

        :param jenkins_api:
            Configured API from python_jenkins that give access to Jenkins data at a host.

        :return set(str):
            Names of all Jenkins jobs that match `job` repository name and branch
        '''
        jenkins_jobs = set([str(job['name']) for job in jenkins_api.get_jobs()])

        matching_jobs = set()

        for jenkins_job in jenkins_jobs:
            # Filter jobs that belong to this repository (this would be safer to do reading SCM
            # information, but a lot more expensive
            common_prefix = self.repository.name + '-' + self.repository.branch
            if not jenkins_job.startswith(common_prefix):
                continue

            jenkins_job_branch = self._GetJenkinsJobBranch(jenkins_api, jenkins_job)
            if jenkins_job_branch == self.repository.branch:
                matching_jobs.add(jenkins_job)

        return matching_jobs


    @Memoize
    def _GetJenkinsJobBranch(self, jenkins_api, jenkins_job):
        '''
        :param jenkins.Jenkins jenkins_api:
            Configured API from python_jenkins that give access to Jenkins data at a host.

        :param str jenkins_job:
            Name of a job in jenkins

        :return str:
            Name of `jenkins_job`s branch

        .. note::
            This function was separated to make use of Memoize cacheing, avoiding multiple queries
            to the same jenkins job config.xml
        '''
        from xml.etree import ElementTree

        # Read config to see if this job is in the same branch
        config = jenkins_api.get_job_config(jenkins_job)

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
        else:
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

    :param str url:
        URL of a Jenkins sevrer instance where jobs will be uploaded

    :param str|None username:
        Username for Jenkins server.

    :param str|None password:
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
    from ben10.filesystem import FileNotFoundError, GetFileContents
    from gitit.git import Git
    from jobs_done10.jobs_done_job import JOBS_DONE_FILENAME
    from jobs_done10.repository import Repository
    import os

    git = Git()
    repository = Repository(
        url=git.GetRemoteUrl(repo_path=directory),
        branch=git.GetCurrentBranch(repo_path=directory)
    )

    try:
        jobs_done_file_contents = GetFileContents(os.path.join(directory, JOBS_DONE_FILENAME))
    except FileNotFoundError:
        jobs_done_file_contents = None

    return repository, GetJobsFromFile(repository, jobs_done_file_contents)



def GetJobsFromFile(repository, jobs_done_file_contents):
    '''
    Creates jobs from repository information and a jobs_done file.

    :param Repository repository:
        .. seealso:: Repository

    :param str|None jobs_done_file_contents:
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
