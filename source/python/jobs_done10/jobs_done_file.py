# Name of jobs_done file, repositories must contain this file in their root dir to be able to
# create jobs.
import yaml
JOBS_DONE_FILENAME = '.jobs_done.yaml'



#===================================================================================================
# JobsDoneFile
#===================================================================================================
class JobsDoneFile(object):
    '''
    Represents a jobs_done file with descriptions used to create jobs.
    This is a generic representation, not related to any specific continuous integration tool.

    :ivar list(str) branch_patterns:
        pass

    :ivar dict matrix:
        A dict that represents all possible job combinations created from this file.

        When a jobs_done file is parsed, it can contain variables that form a matrix. For each
        possible combination of these variables, a JobsDoneFile class is created. They can be used
        for things such as creating jobs for multiple platforms from a single JobsDoneFile.

        For example, if our file describes this matrix:
            matrix:
              planet:
              - earth
              - mars

              moon:
              - europa
              - ganymede

        This file's `matrix` will be:
            {'planet' : ['earth', 'mars], 'moon' : ['europa', 'ganymede']}

        This file's `matrix_row` will have one of these values (one for each JobsDoneFile created):
            {'planet' : 'earth', 'moon' : 'europa'}
            {'planet' : 'earth', 'moon' : 'ganymede'}
            {'planet' : 'mars', 'moon' : 'europa'}
            {'planet' : 'mars', 'moon' : 'ganymede'}

    :ivar dict matrix_row:
        A dict that represents a single row from this file's `matrix`.

        .. seealso:: `matrix`

    '''
    # Options that should be forwarded to generators. These are set in JobsDoneFile instances
    # after parsing (setattr(option_name, self, value)), and are available as object fields
    GENERATOR_OPTIONS = {
        # list(str): Patterns to match when looking for boosttest results.
        'boosttest_patterns':list,

        # list(str): Shell script commands used to build a project.
        'build_shell_commands':list,


        # list(str): Batch script commands used to build a project.
        'build_batch_commands':list,


        # str: Regex pattern to be matched from a job output and used as job description. (Jenkins)
        'description_regex':str,

        # list(str): List of patterns to match when looking for junit test results.
        'junit_patterns':list,

        # Definition of parameters available to this job.
        # Uses jenkins-job-builder syntax parsed by yaml.
        # .. seealso:: http://ci.openstack.org/jenkins-job-builder/parameters.html
        #
        # e.g.
        #     parameters = {'choices' : ['1', '2'], 'name' : 'my_param'}
        'parameters':list,
    }

    # All parsed options (..seealso:: class docs)
    PARSED_OPTIONS = {
        'branch_patterns':list,
        'matrix':dict,
    }
    PARSED_OPTIONS.update(GENERATOR_OPTIONS)


    def __init__(self):
        self.matrix_row = None

        # Initialize known options with None
        for option_name in self.PARSED_OPTIONS:
            setattr(self, option_name, None)


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
                JobsDoneFile(junit_patterns="*.xml", matrix_row={'custom_variable': 'value_1'}),
                JobsDoneFile(junit_patterns="*.xml", matrix_row={'custom_variable': 'value_2'}),
        '''
        if yaml_contents is None:
            return []


        # Load yaml
        jd_data = yaml.load(yaml_contents, Loader=cls._JobsDoneYamlLoader) or {}

        # Search for unknown options and type errors
        parseable_options = JobsDoneFile.PARSED_OPTIONS.keys()
        for option_name, option_value in jd_data.iteritems():
            option_name = option_name.rsplit(':', 1)[-1]
            if option_name not in parseable_options:
                raise UnknownJobsDoneFileOption(option_name)

            obtained_type = type(option_value)
            expected_type = cls.PARSED_OPTIONS[option_name]
            if obtained_type != expected_type:
                raise JobsDoneFileTypeError(option_name, obtained_type, expected_type)


        # List combinations based on job matrix defined by file
        if 'matrix' in jd_data.keys():
            matrix = jd_data['matrix']

            # Write up all possible combinations of the job matrix
            # Stolen from http://stackoverflow.com/a/3873734/1209622
            import itertools as it
            matrix_rows = [
                dict(zip(matrix, p)) for p in it.product(*(matrix[v] for v in matrix))
            ]
        else:
            # If there is no job matrix, we have a single 'row', with no values
            matrix_rows = [{}]


        # Finally, create all jobs_done files (only known options remain in jd_data)
        def ConditionMatch(matrix_row, conditions):
            variable_name, variable_value = condition.split('-')
            return matrix_row[variable_name] == variable_value

        jobs_done_files = []
        for matrix_row in matrix_rows:
            jobs_done_file = JobsDoneFile()
            jobs_done_files.append(jobs_done_file)

            jobs_done_file.matrix_row = matrix_row.copy()

            if not jd_data:
                # Handling for empty jobs, they still are valid since we don't know what builder
                # will do with them, maybe fill it with defaults
                continue

            # Re-read jd_data replacing all matrix variables with their values in the current matrix_row
            jd_string = (yaml.dump(jd_data, default_flow_style=False)[:-1])
            formatted_jd_string = jd_string.format(**matrix_row)
            jd_formatted_data = yaml.load(formatted_jd_string)

            for option_name, option_value in jd_formatted_data.iteritems():

                # Check for option conditions
                if ':' in option_name:
                    conditions = option_name.split(':')[:-1]
                    option_name = option_name.split(':')[-1]

                    # Skip this option if any condition is not met
                    if not all([ConditionMatch(matrix_row, condition) for condition in conditions]):
                        continue

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


    class _JobsDoneYamlLoader(yaml.loader.BaseLoader):
        '''
        Custom loader that treats everything as strings
        '''
        def construct_scalar(self, *args, **kwargs):
            value = yaml.loader.BaseLoader.construct_scalar(self, *args, **kwargs)
            try:
                return value.encode('ascii')
            except:
                return value



#===================================================================================================
# UnknownJobsDoneFileOption
#===================================================================================================
class UnknownJobsDoneFileOption(RuntimeError):
    '''
    Raised when parsing an unknown option.
    '''
    def __init__(self, option_name):
        self.option_name = option_name
        RuntimeError.__init__(
            self,
            'Received unknown option "%s".\n\nAvailable options are:\n%s' % \
            (option_name, '\n'.join('- ' + o for o in sorted(JobsDoneFile.PARSED_OPTIONS)))
        )



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
