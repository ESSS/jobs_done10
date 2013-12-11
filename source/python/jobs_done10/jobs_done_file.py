# Name of jobs_done file, repositories must contain this file in their root dir to be able to
# create jobs.
import itertools
JOBS_DONE_FILENAME = '.jobs_done.yaml'



#===================================================================================================
# JobsDoneFile
#===================================================================================================
class JobsDoneFile(object):
    '''
    Represents a jobs_done file with descriptions used to create jobs.
    This is a generic representation, not related to any specific continuous integration tool.

    :ivar list(str) boosttest_patterns:
        List of patterns to match when looking for boosttest results.

    :ivar str|list(str) build_batch_commands:
        A batch script command (or list of commands) used to build a project.

    :ivar str|list(str) build_shell_commands:
        A shell script command (or list of commands) used to build a project.

    :ivar str description_regex:
        Regex pattern to be matched from a job output and used as job description.
        Used by Jenkins.

    :ivar list(str) junit_patterns:
        List of patterns to match when looking for junit test results.

    :ivar dict parameters:
        Definition of parameters available to this job.
        Uses jenkins-job-builder syntax parsed by yaml.
        .. seealso:: http://ci.openstack.org/jenkins-job-builder/parameters.html

        e.g.
            parameters = {'choices' : ['1', '2'], 'name' : 'my_param'}

    :ivar dict variation:
        A dict that stores the current variation for this file.

        When a jobs_done file is parsed, it can contain 'variables':

            Variables are unknown options that contain multiple values (lists), which indicate
            variations of possible jobs described by this file. For each possible combination of
            these variables, a JobsDoneFile class is created. They can be used, for example, to
            create jobs for multiple platforms from a single JobsDoneFile.

        `variation` represents one of those variations.

        For example, if our file describes these variables:
            planet:
            - earth
            - mars

            moon:
            - europa
            - ganymede

        This variation will have one of these values (one for each JobsDoneFile created from it):
            {'planet' : 'earth', 'moon' : 'europa'}
            {'planet' : 'earth', 'moon' : 'ganymede'}
            {'planet' : 'mars', 'moon' : 'europa'}
            {'planet' : 'mars', 'moon' : 'ganymede'}
    '''
    # Options that will be set in generators
    GENERATOR_OPTIONS = {
        'boosttest_patterns':list,
        'build_shell_commands':list,
        'build_batch_commands':list,
        'description_regex':str,
        'junit_patterns':list,
        'parameters':list,
    }

    # All options that are parsed
    PARSED_OPTIONS = {
        'branch_patterns':list,
    }
    PARSED_OPTIONS.update(GENERATOR_OPTIONS)


    def __init__(self):
        # Initialize known options with None
        for option_name in self.PARSED_OPTIONS:
            setattr(self, option_name, None)

        # All other variable options (store job variations)
        self.variation = {}


    @classmethod
    def CreateFromYAML(cls, yaml_contents):
        '''
        :param str yaml_contents:

        :return list(JobsDoneFile):

        .. seealso:: JobsDoneFile
            For known options accepted in yaml_contents

        .. seealso: pytest_jobs_done_file
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

            resulting JobsDoneFiles:
                JobsDoneFile(junit_patterns="*.xml", variation={'custom_variable': 'value_1'}),
                JobsDoneFile(junit_patterns="*.xml", variation={'custom_variable': 'value_2'}),
        '''
        if yaml_contents is None:
            return []

        # User custom loader that treats everything as strings
        import yaml
        class MyLoader(yaml.loader.BaseLoader):
            def construct_scalar(self, *args, **kwargs):
                value = yaml.loader.BaseLoader.construct_scalar(self, *args, **kwargs)
                try:
                    return value.encode('ascii')
                except:
                    return value

        # Load yaml
        jd_data = yaml.load(yaml_contents, Loader=MyLoader) or {}

        # Search for unknown options
        parseable_options = JobsDoneFile.PARSED_OPTIONS.keys()
        for option_name, option_value in jd_data.iteritems():
            option_name = option_name.rsplit(':', 1)[-1]
            if option_name not in parseable_options and not isinstance(option_value, list):
                raise UnknownJobsDoneFileOption(option_name)

        # List any possible variations, and remove then from jd_data
        variables = {}
        for option_name, option_value in jd_data.items():
            option_name = option_name.rsplit(':', 1)[-1]
            if option_name not in parseable_options:
                variables[option_name] = option_value
                del jd_data[option_name]

        if variables:
            # Write up all possible variations of those variables
            # Stolen from http://stackoverflow.com/a/3873734/1209622
            import itertools as it
            variations = [
                dict(zip(variables, p)) for p in it.product(*(variables[v] for v in variables))
            ]
        else:
            # If there are no variation, we have one possible variation, with no values
            variations = [{}]

        # Finally, create all jobs_done files (only known options remain in jd_data)
        def ConditionMatch(variation, conditions):
            variable_name, variable_value = condition.split('-')
            return variation[variable_name] == variable_value

        jobs_done_files = []

        for variation in variations:
            jobs_done_file = JobsDoneFile()
            jobs_done_files.append(jobs_done_file)

            jobs_done_file.variation = variation.copy()

            if not jd_data:
                # Handling for empty jobs, they still are valid since we don't know what builder
                # will do with them, maybe fill it with defaults
                continue

            # Re-read jd_data replacing all variation with their values in the current variation
            jd_string = (yaml.dump(jd_data, default_flow_style=False)[:-1])
            jd_string = jd_string.format(**variation)
            jd_formatted_data = yaml.load(jd_string)

            for option_name, option_value in jd_formatted_data.iteritems():

                # Check for option conditions
                if ':' in option_name:
                    conditions = option_name.split(':')[:-1]
                    option_name = option_name.split(':')[-1]

                    # Skip this option if any condition is not met
                    if not all([ConditionMatch(variation, condition) for condition in conditions]):
                        continue

                # Check for type errors
                obtained_type = type(option_value)
                expected_type = cls.PARSED_OPTIONS[option_name]

                if obtained_type != expected_type:
                    raise JobsDoneFileTypeError(option_name, obtained_type, expected_type)

                setattr(jobs_done_file, option_name, option_value)

        return jobs_done_files


    @classmethod
    def CreateFromFile(cls, filename):
        '''
        :param str filename:
            Path to a jobs_done file

        .. seealso:: CreateFromYAML
        '''
        from ben10.filesystem import GetFileContents
        return cls.CreateFromYAML(GetFileContents(filename))



#===================================================================================================
# UnknownJobsDoneFileOption
#===================================================================================================
class UnknownJobsDoneFileOption(RuntimeError):
    '''
    Raised when parsing an unknown option.
    '''
    def __init__(self, option_name):
        self.option_name = option_name
        RuntimeError.__init__(self, option_name)



#===================================================================================================
# JobsDoneFileTypeError
#===================================================================================================
class JobsDoneFileTypeError(TypeError):
    '''
    Raised when parsing an option with a bad type.
    '''
    def __init__(self, option_name, obtained_type, expected_type):
        self.option_name = option_name
        self.obtained_type = obtained_type
        self.expected_type = expected_type
        self.option_name = option_name

        TypeError.__init__(
            self,
            'On option "%s". Expected "%s" but got "%s".' % \
            (option_name, expected_type, obtained_type)
        )
