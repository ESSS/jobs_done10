from ben10.interface import Interface



#===================================================================================================
# IJobGenerator
#===================================================================================================
class IJobGenerator(Interface):
    '''
    Interface for job generators.

    These generators are responsible for creating continuous integration jobs for any particular
    tool, such as Jenkins or Bamboo.

    Generators must implement this interface, which represents the bare minimum of options
    available, but this is more than likely not enough to build a complete job. Configurations set
    in a generators come from a `JobGeneratorConfigurator`, which itself extracts them from a
    `JobsDoneFile`.

    As new options can be easily added to `JobsDoneFile`, and some options might not make sense for
    different tools, not all of them are defined in this interface, but helpful error messages
    were added to guide development of builders.

    .. seealso::
        JobGeneratorConfigurator

    .. seealso::
        http://en.wikipedia.org/wiki/Builder_pattern
    '''

    def __init__(self, repository):
        '''
        :param Repository repository:
            Repository information for jobs created by this generator.
        '''

    def Reset(self):
        '''
        Resets all configurations made to this builder.
        '''


    def GenerateJobs(self):
        '''
        Generate jobs. This might mean creating files in a directory, pushing content to a
        web API, or anything that represents the final purpose of jobs_done.
        '''

    def SetMatrixRow(self, matrix_row):
        '''
        Sets current matrix_row of this job.

        Variations are any option unknown to a JobsDoneFile, and are used to represent possible
        variations of a job. They can be used, for example, to create jobs for multiple platforms
        from a single JobsDoneFile.

        This will set a single build variation, with the values for the current variation being
        built.

        :param dict(str,str) variation:
            Dictionary mapping variation name to value.
            e.g.
                variation = {'planet' : 'earth'}

        .. seealso::
            JobsDoneFile
        '''


#===================================================================================================
# JobGeneratorConfigurator
#===================================================================================================
class JobGeneratorConfigurator(object):
    '''
    Class used to configure `IJobGenerator`s using `JobsDoneFile` and `Repository` information.

    .. seealso:: IJobGenerator
    '''

    @classmethod
    def Configure(cls, builder, jobs_done_file):
        '''
        This simply iterates over data and calls a series of functions in a Builder. Functions
        called are determined by options in `jobs_done_file` by converting the option names to camel case.
            e.g.: option 'junit_patterns' will trigger a call to builder.AddJunitPatterns

        :param IJobGenerator builder:
            Builder being configured.

        :param JobsDoneFile jobs_done_file:
            Will be used to extract options that must be configured in `builder`
        '''
        builder.Reset()
        builder.SetMatrixRow(jobs_done_file.matrix_row)

        for option in jobs_done_file.GENERATOR_OPTIONS:
            option_value = getattr(jobs_done_file, option)
            if option_value is None:
                continue  # Skip unset options

            # Find function name associated with the option being processed
            builder_function_name = 'Set' + option.title().replace('_', '')

            # Obtain and call that function with the option value
            try:
                builder_function = getattr(builder, builder_function_name)
            except AttributeError:
                raise JobGeneratorAttributeError(
                    builder,
                    builder_function_name,
                    option
                )

            builder_function(option_value)

        return builder



#===================================================================================================
# JobGeneratorAttributeError
#===================================================================================================
class JobGeneratorAttributeError(AttributeError):
    '''
    Raised when trying to access a builder function that is not implemented.
    '''
    def __init__(self, builder, attribute, jobs_done_file_option):
        message = '%s "%s" cannot handle option "%s" (could not find function "%s").' % \
            (IJobGenerator.__name__, builder.__class__.__name__, jobs_done_file_option, attribute)

        AttributeError.__init__(self, message)
