'''
Module containing everything related to Jenkins in jobs_done10.

This includes a generator, job publishers, constants and command line interface commands.
'''
from __future__ import absolute_import, with_statement
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
# JenkinsJobGenerator
#===================================================================================================
class JenkinsJobGenerator(object):
    '''
    Generates Jenkins jobs.
    '''
    ImplementsInterface(IJobGenerator)

    @Implements(IJobGenerator.__init__)
    def __init__(self, repository):
        self.repository = repository
        self.job_group = repository.name + '-' + repository.branch


    @Implements(IJobGenerator.Reset)
    def Reset(self):
        self.templates = []

        self._junit_pattern = None
        self._boosttest_pattern = None
        self._description_regex = None
        self._variation = {}


    @Implements(IJobGenerator.GenerateJobs)
    def GenerateJobs(self):
        '''
        :returns JenkinsJob:
            A job built by this generator based on its configuration.
        '''
        # Handle Publishers (must be done after all of them have been set)
        self._SetPulibshers()

        # Create jenkins job builder yaml
        def Indented(text):
            return '\n'.join(['    ' + line for line in text.splitlines()]) + '\n'

        # >>> Define some local vars to replace in template
        template_parts = [value for (key, value) in sorted(self._variation.items())]
        job_name = '-'.join([self.job_group] + template_parts)
        node = '-'.join([self.repository.name] + template_parts)
        url = self.repository.url
        branch = self.repository.branch
        basedir = self.repository.name

        # >>> Basic template
        from ben10.foundation.string import Dedent
        jenkins_job_builder_yaml_contents = Dedent(
            '''
            - job:
                name: "%(job_name)s"
                node: "%(node)s"

                scm:
                - git:
                    url: "%(url)s"
                    basedir: "%(basedir)s"
                    wipe-workspace: false
                    branches:
                    - "%(branch)s"

                logrotate:
                    daysToKeep: 7
                    numToKeep: 16
                    artifactDaysToKeep: -1
                    artifactNumToKeep: -1

            '''
        )

        # >>> Include additional options set in this generator
        template_contents = '\n'.join(map(str, self.templates))
        jenkins_job_builder_yaml_contents += Indented(template_contents)

        # >>> Format strings
        jenkins_job_builder_yaml_contents %= locals()

        # Parse jenkins job builder yaml to create job XML
        from jenkins_jobs.builder import YamlParser
        parser = YamlParser()
        parser.parseContents(jenkins_job_builder_yaml_contents)
        parser.generateXML()

        # The way we create jobs should only generate one job per yaml
        assert len(parser.jobs) == 1

        return JenkinsJob(
            name=parser.jobs[0].name,
            xml=str(parser.jobs[0].output()),
        )


    #===============================================================================================
    # Configurator functions (..seealso:: JobsDoneFile ivars for docs)
    #===============================================================================================
    @Implements(IJobGenerator.SetVariation)
    def SetVariation(self, variation):
        self._variation = variation


    def SetParameters(self, parameters):
        import yaml
        self.templates.append(
            yaml.dump(
                {'parameters': parameters},
                allow_unicode=False,
                default_flow_style=False,
            )[:-1]
        )


    def SetJunitPatterns(self, junit_patterns):
        self._junit_pattern = ' '.join(junit_patterns)


    def SetBoosttestPatterns(self, boosttest_patterns):
        self._boosttest_pattern = ' '.join(boosttest_patterns)


    def SetDescriptionRegex(self, description_regex):
        self._description_regex = description_regex


    def SetBuildBatchCommand(self, build_batch_command):
        from ben10.foundation.types_ import AsList

        # We accept either a single command, or a list of commands
        batch_builders = [
            {'batch':command} for command in AsList(build_batch_command)
        ]

        import yaml
        self.templates.append(yaml.dump({'builders': batch_builders}, default_flow_style=False)[:-1])


    def SetBuildShellCommand(self, build_shell_command):
        from ben10.foundation.types_ import AsList

        # We accept either a single command, or a list of commands
        shell_builders = [
            {'shell':command} for command in AsList(build_shell_command)
        ]

        import yaml
        self.templates.append(yaml.dump({'builders': shell_builders}, default_flow_style=False)[:-1])


    def _SetPulibshers(self):
        '''
        Sets "publisher" information in job (includes test results and build description)
        '''
        junit_pattern = self._junit_pattern
        boosttest_pattern = self._boosttest_pattern
        description_regex = self._description_regex

        if not any((junit_pattern, boosttest_pattern, description_regex)):
            return  # Need at least one publisher to do something

        parsed_contents = {'publishers' : []}

        if junit_pattern or boosttest_pattern:
            xunit = {
                'thresholds' : [{'failed' : {'unstable' : '0', 'unstablenew' : '0'}}],
                'types' : []
            }

            if junit_pattern:
                xunit['types'].append({'junit': {
                    'pattern' : junit_pattern,
                    'requireupdate' : 'false',
                    'skipnotestfiles' : 'true',
                    'stoponerror' : 'true',
                }})
            if boosttest_pattern:
                xunit['types'].append({'boosttest': {
                    'pattern' : boosttest_pattern,
                    'requireupdate' : 'false',
                    'skipnotestfiles' : 'true',
                    'stoponerror' : 'true',
                }})

            parsed_contents['publishers'].append({'xunit' : xunit})

        if description_regex:
            parsed_contents['publishers'].append({'descriptionsetter' : {
                'regexp' : description_regex,
                'regexp-for-failed' : description_regex,
            }})

        import yaml
        template = yaml.dump(parsed_contents, default_flow_style=False)
        self.templates.append(template)



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
        import os
        from ben10.filesystem import CreateFile
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
        ..seealso:: GetJobsFromFile

    :param jobs_done_file_contents:
        ..seealso:: GetJobsFromFile

    :param str url:
        URL of a Jenkins sevrer instance where jobs will be uploaded

    :param str|None username:
        Username for Jenkins server.

    :param str|None password:
        Password for Jenkins server.

    :returns:
        ..seealso:: JenkinsJobPublisher.PublishToUrl

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
    from ben10.filesystem import GetFileContents, FileNotFoundError
    from jobs_done10.jobs_done_file import JOBS_DONE_FILENAME
    from jobs_done10.repository import Repository
    from sharedscripts10.shared_scripts.git_ import Git
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
        ..seealso:: Repository

    :param str|None jobs_done_file_contents:
        ..seealso:: JobsDoneFile.CreateFromYAML

    :return set(JenkinsJob)
    '''
    from jobs_done10.job_generator import JobGeneratorConfigurator
    from jobs_done10.jobs_done_file import JobsDoneFile
    import re

    jenkins_generator = JenkinsJobGenerator(repository)

    jobs = []
    jobs_done_files = JobsDoneFile.CreateFromYAML(jobs_done_file_contents)
    for jobs_done_file in jobs_done_files:
        # If jobs_done file defines patterns for acceptable branches to create jobs, compare those
        # against the current branch, to determine if we should generate jobs or not.
        if jobs_done_file.branch_patterns is not None:
            if not any([re.match(pattern, repository.branch) for pattern in jobs_done_file.branch_patterns]):
                continue

        JobGeneratorConfigurator.Configure(jenkins_generator, jobs_done_file)
        jobs.append(jenkins_generator.GenerateJobs())

    return jenkins_generator.job_group, jobs



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
        jobs = GetJobsFromDirectory(directory)

        console_.Print('Saving jobs in "%s"' % output_directory)
        JenkinsJobPublisher(jobs).PublishToDirectory(output_directory)
        console_.ProgressOk()
