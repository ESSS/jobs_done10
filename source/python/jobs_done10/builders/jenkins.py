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


    @Implements(IJobBuilder.Build)
    def Build(self):
        '''
        :returns str:
            yaml contents used by jenkins-jobs
        '''
        # Common templates
        self._AddLogrotate()

        # Handle Publisher
        self._AddPulibshers()

        # Create and parse _JenkinsYaml
        jenkins_yaml = _JenkinsYaml(
            name=self.repository.name + '-' + self.repository.branch,
            node=self.repository.name,
            templates=self.templates[:],
            variables=self.variables,
        )
        return jenkins_yaml


    @Implements(IJobBuilder.AddVariables)
    def AddVariables(self, variables):
        self.variables = variables


    @Implements(IJobBuilder.AddRepository)
    def AddRepository(self, repository):
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
                    branches:
                    - "%(branch)s"
                ''' % locals()
            )
        )


    #===============================================================================================
    # Configurator functions (..seealso:: CIFile ivars for docs)
    #===============================================================================================
    def AddParameters(self, parameters):
        import yaml
        self.templates.append(yaml.dump({'parameters': parameters}, default_flow_style=False))


    def AddJunitPatterns(self, junit_patterns):
        self._junit_pattern = ' '.join(junit_patterns)


    def AddBoosttestPatterns(self, boosttest_patterns):
        self._boosttest_pattern = ' '.join(boosttest_patterns)


    def AddDescriptionRegex(self, description_regex):
        self._description_regex = description_regex


    def AddBuildBatchCommand(self, build_batch_command):
        self.templates.append(Dedent(
            '''
            builders:
            - batch: "%(build_batch_command)s"
            ''' % locals()
        ))


    def AddBuildShellCommand(self, build_shell_command):
        self.templates.append(Dedent(
            '''
            builders:
            - shell: "%(build_shell_command)s"
            ''' % locals()
        ))


    #===============================================================================================
    # Privates
    #===============================================================================================
    def _AddLogrotate(self, days_to_keep=7, num_to_keep=16):
        self.templates.append(Dedent(
            '''
            logrotate:
                daysToKeep: %(days_to_keep)d
                numToKeep: %(num_to_keep)d
                artifactDaysToKeep: -1
                artifactNumToKeep: -1
            ''' % locals()
        ))


    def _AddPulibshers(self):
        junit_pattern = self._junit_pattern
        boosttest_pattern = self._boosttest_pattern
        description_regex = self._description_regex

        if not any((junit_pattern, boosttest_pattern, description_regex)):
            return  # Need at least one publisher to do something

        # Write basic contents
        import yaml
        parsed_contents = yaml.load(Dedent(
            '''
            publishers:
            - xunit:
                thresholds:
                - failed:
                    unstable: '0' 
                    unstablenew: '0'
                types:
                - junit:
                    pattern: "%(junit_pattern)s"
                    requireupdate: 'false'
                    stoponerror: 'false'
                - boosttest:
                    pattern: "%(boosttest_pattern)s"
                    requireupdate: 'false'
                    stoponerror: 'false'
            - descriptionsetter:
                regexp: "%(description_regex)s"
            ''' % locals()
        ))

        # Remove description_regex if not given
        if not description_regex:
            del parsed_contents['publishers'][1]

        # Remove some types if no patterns were given
        if not junit_pattern and not boosttest_pattern:
            del parsed_contents['publishers'][0]
        else:
            if not boosttest_pattern:
                del parsed_contents['publishers'][0]['xunit']['types'][1]
            if not junit_pattern:
                del parsed_contents['publishers'][0]['xunit']['types'][0]

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
        from ben10.filesystem import ListFiles, GetFileContents
        from coilib50.filesystem import CreateTemporaryDirectory
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
    def __init__(self, name, node, templates=[], variables={}):
        '''
        :param name:
            Job name

        :param node:
            Node where job will run
            
        :param list(str) templates:
            List of templates to be included
            
        :param variables:
            .. seealso:: CIFile.variables
        '''
        self.name = name
        self.node = node
        self.templates = templates
        self.variables = variables


    def __str__(self):
        def Indented(text):
            return '\n'.join(['    ' + line for line in text.splitlines()]) + '\n'

        name = self.name

        template_parts = ['{%s}' % key for key in sorted(self.variables.keys())]
        template_name = '-'.join([name] + template_parts)
        node = '-'.join([self.node] + template_parts)

        template_contents = '\n'.join(map(str, self.templates))
        variable_contents = ''

        for variable_name, values in sorted(self.variables.iteritems()):
            variable_contents += variable_name + ':\n'
            for value in values:
                variable_contents += '- "%s"\n' % str(value)

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
        from sharedscripts10.shared_scripts.jenkins_job_builder_ import JenkinsJobBuilder
        import tempfile

        temp_filename = tempfile.mktemp(suffix='jobs_done', prefix='.yaml')

        CreateFile(temp_filename, str(self))
        try:
            CreateDirectory(output_directory)
            JenkinsJobBuilder().Execute(['test', temp_filename, '-o', output_directory])
        finally:
            DeleteFile(temp_filename)



#===================================================================================================
# ConfigureCommandLineInterface
#===================================================================================================
def ConfigureCommandLineInterface(jobs_done_application):
    @jobs_done_application
    def jenkins(console_, url, username=None, password=None):
        '''
        Creates jobs for jenkins and push them to a Jenkins instance
        
        :param url: Jenkins instance URL where jobs will be uploaded to.
     
        :param username: Jenkins username.
     
        :param password: Jenkins password.
        '''
        from jobs_done10.actions import BuildJobsInDirectory
        builder = JenkinsJobBuilderToUrl(url=url, username=username, password=password)
        BuildJobsInDirectory(builder, progress_callback=console_.Print)


    @jobs_done_application
    def jenkins_test(console_, output_directory):
        '''
        Creates jobs for jenkins and save the resulting .xml's in a directory
        
        :param output_directory: Directory to output job xmls instead of uploading to `url`.
        '''
        from jobs_done10.actions import BuildJobsInDirectory
        builder = JenkinsJobBuilderToOutputDirectory(output_directory=output_directory)
        BuildJobsInDirectory(builder, progress_callback=console_.Print)
