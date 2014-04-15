'''
Module containing everything related to Jenkins in jobs_done10.

This includes a generator, job publishers, constants and command line interface commands.
'''
from __future__ import absolute_import
from ben10.foundation.bunch import Bunch
from ben10.foundation.decorators import Implements
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

    :cvar str xml:
        Job XML contents
    '''
    name = None
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
        self.repository = None


    @Implements(IJobGenerator.Reset)
    def Reset(self):
        from pyjenkins import JenkinsJobGenerator as PyJenkinsJobGenerator

        self.__jjgen = PyJenkinsJobGenerator(self.repository.name)

        # Configure description
        self.__jjgen.description = "<!-- Managed by Job's Done -->"

        # Configure git SCM
        self.__jjgen.CreatePlugin(
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


    def GetJobs(self):
        return JenkinsJob(name=self.__jjgen.job_name, xml=self.__jjgen.GetContent())


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

            if row_representation: # Might be empty
                self.__jjgen.label_expression += '-' + row_representation
                self.__jjgen.job_name += '-' + row_representation


    def SetBoosttestPatterns(self, boosttest_patterns):
        xunit_plugin = self.__jjgen.ObtainPlugin("xunit")
        xunit_plugin.boost_patterns = boosttest_patterns


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


    def SetJunitPatterns(self, junit_patterns):
        xunit_plugin = self.__jjgen.ObtainPlugin("xunit")
        xunit_plugin.junit_patterns = junit_patterns


    def SetJsunitPatterns(self, jsunit_patterns):
        xunit_plugin = self.__jjgen.ObtainPlugin("xunit")
        xunit_plugin.jsunit_patterns = jsunit_patterns


    def SetLabelExpression(self, label_expression):
        self.__jjgen.label_expression = label_expression


    def SetNotifyStash(self, args):
        assert isinstance(args, (basestring, dict)), '"args" must be a string or dict.'

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


    def SetTimeout(self, timeout):
        self.__jjgen.CreatePlugin("timeout", timeout)



#===================================================================================================
# JenkinsJobPublisher
#===================================================================================================
class JenkinsJobPublisher(object):
    '''
    Publishes `JenkinsJob`s
    '''
    def __init__(self, job_group, jobs):
        '''
        :param str job_group:
            Group to which these jobs belong to.

            This is used find and delete/update jobs that belong to the same group during upload.

        :param list(JenkinsJob) jobs:
            List of jobs to be published. They must all belong to the same `job_group` (name must
            start with `job_group`)
        '''
        self.job_group = job_group
        self.jobs = dict((job.name, job) for job in jobs)

        for job_name in self.jobs.keys():
            assert job_name.startswith(job_group)


    def PublishToUrl(self, url, username=None, password=None):
        '''
        Publishes new jobs, updated existing jobs, and delete jobs that belong to the same
        `self.job_group` but were not updated.

        :param str url:
            Jenkins instance URL where jobs will be uploaded to.

        :param str username:
            Jenkins username.

        :param str password:
            Jenkins password.

        :return tuple(list(str),list(str),list(str)):
            Tuple with lists of {new, updated, deleted} job names (sorted alphabetically)
        '''
        # Push to url using jenkins_api
        import jenkins
        jenkins = jenkins.Jenkins(url, username, password)

        job_names = set(self.jobs.keys())

        all_jobs = set([str(job['name']) for job in jenkins.get_jobs()])
        matching_jobs = set([job for job in all_jobs if job.startswith(self.job_group)])

        new_jobs = job_names.difference(matching_jobs)
        updated_jobs = job_names.intersection(matching_jobs)
        deleted_jobs = matching_jobs.difference(job_names)

        for job_name in new_jobs:
            jenkins.create_job(job_name, self.jobs[job_name].xml)

        for job_name in updated_jobs:
            jenkins.reconfig_job(job_name, self.jobs[job_name].xml)

        for job_name in deleted_jobs:
            jenkins.delete_job(job_name)

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
    job_group, jobs = GetJobsFromFile(repository, jobs_done_file_contents)
    publisher = JenkinsJobPublisher(job_group, jobs)

    return publisher.PublishToUrl(url, username, password)



def GetJobsFromDirectory(directory='.'):
    '''
    Looks in a directory for a jobs_done file and git repository information to create jobs.

    :param directory:
        Directory where we'll extract information to generate `JenkinsJob`s

    :return set(JenkinsJob)
    '''
    from ben10.filesystem import FileNotFoundError, GetFileContents
    from jobs_done10.git import Git
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

    return GetJobsFromFile(repository, jobs_done_file_contents)



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
    job_group = jenkins_generator.GetJobGroup(repository)

    jobs = []
    jobs_done_jobs = JobsDoneJob.CreateFromYAML(jobs_done_file_contents, repository)
    for jobs_done_job in jobs_done_jobs:
        JobGeneratorConfigurator.Configure(jenkins_generator, jobs_done_job)
        jobs.append(jenkins_generator.GetJobs())

    return job_group, jobs



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
        directory = '.'

        job_group, jobs = GetJobsFromDirectory(directory)

        console_.Print('Publishing jobs in "<white>%s</>"' % url)

        new_jobs, updated_jobs, deleted_jobs = JenkinsJobPublisher(job_group, jobs).PublishToUrl(
            url, username, password)

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
        directory = '.'
        job_group, jobs = GetJobsFromDirectory(directory)

        console_.Print('Saving jobs in "%s"' % output_directory)
        publisher = JenkinsJobPublisher(job_group, jobs)
        publisher.PublishToDirectory(output_directory)
        console_.ProgressOk()
