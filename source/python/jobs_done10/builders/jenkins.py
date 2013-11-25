'''
Module containing everything related to Jenkins in jobs_done10.

This includes builders (and any implementation details of them), constants and command line
interfaces
'''
from __future__ import absolute_import, with_statement
from ben10.foundation.decorators import Implements
from ben10.foundation.string import Dedent
from ben10.interface import ImplementsInterface
from jobs_done10.job_builder import IJobBuilder



#===================================================================================================
# JenkinsJobBuilder
#===================================================================================================
class JenkinsJobBuilder(object):
    '''
    Base class for Jenkins builders.

    `self.Build` simply returns a jenkins-job-builder format yaml to be used by subclasses.
    '''
    ImplementsInterface(IJobBuilder)

    def __init__(self):
        self.Reset()


    @Implements(IJobBuilder.Reset)
    def Reset(self):
        self.templates = []

        self._junit_pattern = None
        self._boosttest_pattern = None
        self._description_regex = None
        self._variation = {}


    @Implements(IJobBuilder.Build)
    def Build(self):
        '''
        :returns str:
            yaml contents used by jenkins-jobs
        '''
        # Common templates
        self._SetLogrotate()

        # Handle Publisher
        self._SetPulibshers()

        # Create and parse _JenkinsYaml
        jenkins_yaml = _JenkinsYaml(
            name=self.repository.name + '-' + self.repository.branch,
            node=self.repository.name,
            templates=self.templates[:],
            variation=self._variation,
        )
        return jenkins_yaml


    @Implements(IJobBuilder.SetVariation)
    def SetVariation(self, variation):
        self._variation = variation


    @Implements(IJobBuilder.SetRepository)
    def SetRepository(self, repository):
        self.repository = repository

        url = repository.url
        branch = repository.branch
        basedir = repository.name

        self.templates.append(
            Dedent(
                '''
                scm:
                - git:
                    url: "%(url)s"
                    basedir: "%(basedir)s"
                    wipe-workspace: false
                    branches:
                    - "%(branch)s"
                ''' % locals()
            )
        )


    #===============================================================================================
    # Configurator functions (..seealso:: JobsDoneFile ivars for docs)
    #===============================================================================================
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
        import yaml
        self.templates.append(
            yaml.dump({'builders': [{'batch':build_batch_command}]}, default_flow_style=False)[:-1]
        )


    def SetBuildShellCommand(self, build_shell_command):
        import yaml
        self.templates.append(
            yaml.dump({'builders': [{'shell':build_shell_command}]}, default_flow_style=False)[:-1]
        )


    #===============================================================================================
    # Privates
    #===============================================================================================
    def _SetLogrotate(self, days_to_keep=7, num_to_keep=16):
        '''
        Sets log rotation to Job (indicates how long we want to keep console logs for builds).

        After a certain number of days or builds, old logs are deleted.

        :param int days_to_keep:
            Maximum amount of days to keep build logs.

        :param int num_to_keep:
            Maximum of build logs to keep.
        '''
        self.templates.append(Dedent(
            '''
            logrotate:
                daysToKeep: %(days_to_keep)d
                numToKeep: %(num_to_keep)d
                artifactDaysToKeep: -1
                artifactNumToKeep: -1
            ''' % locals()
        ))


    def _SetPulibshers(self):
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
                    'stoponerror' : 'false',
                }})
            if boosttest_pattern:
                xunit['types'].append({'boosttest': {
                    'pattern' : boosttest_pattern,
                    'requireupdate' : 'false',
                    'stoponerror' : 'false',
                }})

            parsed_contents['publishers'].append({'xunit' : xunit})

        if description_regex:
            parsed_contents['publishers'].append({'descriptionsetter' : {'regexp' : description_regex}})

        import yaml
        template = yaml.dump(parsed_contents, default_flow_style=False)
        self.templates.append(template)



#===================================================================================================
# JenkinsJobBuilderToUrl
#===================================================================================================
class JenkinsJobBuilderToUrl(JenkinsJobBuilder):
    '''
    Uploads created jobs to a Jenkins instance
    '''
    def __init__(self, url, username=None, password=None):
        '''
        :param str url:
            Jenkins instance URL where jobs will be uploaded to.

        :param str username:
            Jenkins username.

        :param str password:
            Jenkins password.
        '''
        JenkinsJobBuilder.__init__(self)
        self.url = url
        self.username = username
        self.password = password


    @Implements(IJobBuilder.Build)
    def Build(self):
        from ben10.filesystem import ListFiles, GetFileContents, CreateTemporaryDirectory
        import jenkins
        import os

        jenkins_yaml = JenkinsJobBuilder.Build(self)

        # Push to url
        jenkins = jenkins.Jenkins(self.url, self.username, self.password)
        with CreateTemporaryDirectory() as temp_dir:
            jenkins_yaml.Parse(temp_dir)
            for job_name in ListFiles(temp_dir):
                xml = GetFileContents(os.path.join(temp_dir, job_name))
                if jenkins.job_exists(job_name):
                    jenkins.reconfig_job(job_name, xml)
                else:
                    jenkins.create_job(job_name, xml)

        return jenkins_yaml



#===================================================================================================
# JenkinsJobBuilderToOutputDirectory
#===================================================================================================
class JenkinsJobBuilderToOutputDirectory(JenkinsJobBuilder):
    '''
    Saves created .xmls to a directory.
    '''
    def __init__(self, output_directory):
        '''
        :param str output_directory:
             Target directory for outputting job .xmls created by this builder.
        '''
        JenkinsJobBuilder.__init__(self)
        self.output_directory = output_directory


    @Implements(IJobBuilder.Build)
    def Build(self):
        jenkins_yaml = JenkinsJobBuilder.Build(self)
        jenkins_yaml.Parse(self.output_directory)
        return jenkins_yaml



#===================================================================================================
# _JenkinsYaml
#===================================================================================================
class _JenkinsYaml(object):
    '''
    Representation of a yaml file that can be parsed by jenkins-job-builder.

    This is basically a helper class for constructing those yaml files from a series of templates.
    '''

    def __init__(self, name, node, templates=[], variation={}):
        '''
        :param name:
            Job name

        :param node:
            Node where job will run

        :param list(str) templates:
            List of templates to be included

        :param variation:
            .. seealso:: JobsDoneFile
        '''
        self.name = name
        self.node = node
        self.templates = templates
        self._variation = variation


    def __str__(self):
        def Indented(text):
            return '\n'.join(['    ' + line for line in text.splitlines()]) + '\n'

        name = self.name

        template_parts = [value for (key, value) in sorted(self._variation.items())]
        template_name = '-'.join([name] + template_parts)
        node = '-'.join([self.node] + template_parts)

        template_contents = '\n'.join(map(str, self.templates))
        variable_contents = ''


        contents = Dedent(
            '''
            - job-template:
                name: "%(template_name)s"
                node: "%(node)s"

            '''
        )
        contents += Indented(template_contents)
        contents += Dedent(
            '''

            - project:
                name: %(name)s
                jobs:
                - "%(template_name)s"

            '''
        )
        contents += Indented(variable_contents)
        return contents % locals()


    def Parse(self, output_directory):
        '''
        Processes this yaml using jenkins-jobs, and save the resulting files in `output_directory`

        :param str output_directory:
        '''
        from ben10.filesystem import CreateDirectory, DeleteFile, CreateFile
        import tempfile

        temp_filename = tempfile.mktemp(suffix='.yaml', prefix='jobs_done_')

        CreateFile(temp_filename, str(self))
        try:
            CreateDirectory(output_directory)

            import jenkins_jobs.builder
            builder = jenkins_jobs.builder.Builder(
                jenkins_url='fake_url',  # API requires this even if it's not used
                jenkins_user=None,
                jenkins_password=None,
                ignore_cache=True,
            )
            builder.update_job(temp_filename, output_dir=output_directory)
        except Exception, e:
            from ben10.foundation.reraise import Reraise
            Reraise(e, 'Handling YAML:\n\n' + str(self))
        finally:
            DeleteFile(temp_filename)



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
        builder = JenkinsJobBuilderToUrl(url=url, username=username, password=password)

        console_.Print('Pushing jobs to ' + builder.url)
        from jobs_done10.actions import BuildJobsInDirectory
        BuildJobsInDirectory(builder)
        console_.ProgressOk()


    @jobs_done_application
    def jenkins_test(console_, output_directory):
        '''
        Creates jobs for Jenkins and save the resulting .xml's in a directory

        :param output_directory: Directory to output job xmls instead of uploading to `url`.
        '''
        from jobs_done10.actions import BuildJobsInDirectory
        builder = JenkinsJobBuilderToOutputDirectory(output_directory=output_directory)
        BuildJobsInDirectory(builder)
        console_.ProgressOk()
