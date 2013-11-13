


#===================================================================================================
# CIFile
#===================================================================================================
class CIFile(object):
    '''
    Represents a .ci file with descriptions used to create jobs.
    
    :ivar list(str) boosttest_patterns:
        List of patterns to match when looking for boosttest results.
    
    :ivar str build_batch_command:
        A batch script command used to build a project

    :ivar str build_shell_command:
        A shell script command used to build a project
    
    :ivar str description_regex:
        Regex pattern to be matched from a job output and used as job descirption.
        Used by Jenkins.

    :ivar list(str) junit_patterns:
        List of patterns to match when looking for junit test results.

    :ivar dict parameters:
        Definition of parameters available to this job.
        Uses jenkins-job-builder syntax parsed by yaml.
        .. seealso:: http://ci.openstack.org/jenkins-job-builder/parameters.html
        
        e.g.
            parameters = {'choices' : ['1', '2'], 'name' : 'my_param'} 
    
    :ivar dict variables:
        A dict that stores all other variables, that are not known options.
        
        Variables that contain multiple values (are lists) indicate variations of jobs described
        by this file, and one job will be generated for each possible combination of these
        variables. They can be used, for example, to create jobs for multiple platforms from a
        single CIFile.
    '''
    def __init__(self):
        # Known options (always default to None to indicate that no value was set)
        self.boosttest_patterns = None
        self.build_shell_command = None
        self.build_batch_command = None
        self.description_regex = None
        self.junit_patterns = None
        self.parameters = None

        # All other variable options (store job variations)
        self.variables = {}


    def GetKnownOptions(self):
        '''
        :return list(str):
            A list of all known options in a CI file.
            
            These options are determined from public members of this class.
            
            .. seealso:: CIFile.__init__
                For the definition of known options
        '''
        known_options = []
        for member in self.__dict__.keys():
            # 'variables' is a special member for all unknown options
            if member == 'variables':
                continue

            # Ignore private member of this class
            if member.startswith('_'):
                continue

            known_options.append(member)

        return known_options


    @classmethod
    def CreateFromYAML(cls, yaml_contents):
        '''
        :param str yaml_contents:
        
        :return CIFile:
        
        .. seealso:: CIFile
            For known options accepted in yaml_contents
            
        .. seealso: pytest_ci_file
            For examples
        
        YAML example:
            yaml_contents =
                """
                junit_patterns:
                    - "*.xml"
                   
                custom_variable:
                    - value_1
                    - value_2
                """
                
            resulting CIFile:
                CIFile(
                    junit_patterns="*.xml",
                    variables={'custom_variable': ['value_1', 'value_2']}
                )
        '''
        import yaml
        ci_data = yaml.load(yaml_contents) or {}

        ci_file = CIFile()
        known_options = ci_file.GetKnownOptions()

        for option_name, option_value in ci_data.iteritems():
            if option_name in known_options:
                setattr(ci_file, option_name, option_value)
            else:
                if isinstance(option_value, list):
                    ci_file.variables[option_name] = option_value
                else:
                    raise UnknownCIFileOption(option_name)
        return ci_file


    @classmethod
    def CreateFromFile(cls, filename):
        '''
        :param str filename:
            Path to a .ci file
        
        .. seealso:: CreateCIFileFromYAML
        '''
        from ben10.filesystem import GetFileContents
        return cls.CreateFromYAML(GetFileContents(filename))



#===================================================================================================
# UnknownCIFileOption
#===================================================================================================
class UnknownCIFileOption(RuntimeError):
    '''
    Raised when parsing an unknown option.
    '''
    def __init__(self, option_name):
        self.option_name = option_name
        RuntimeError.__init__(self, option_name)
