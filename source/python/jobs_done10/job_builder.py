from ben10.interface import Interface



#===================================================================================================
# IJobBuilder
#===================================================================================================
class IJobBuilder(Interface):
    '''
    Interface for job builders.

    These builders are responsible for creating continuous integration jobs for any particular
    tool, such as Jenkins or Bamboo.

    Builders must implement this interface, which represents the bare minimum of options available,
    but this is more than likely not enough to build a complete job. Configurations set in a
    builder come from a `JobBuilderConfigurator`, which itself extracts them from a `JobsDoneFile`.

    As new options can be easily added to `JobsDoneFile`, and some options might not make sense for
    different tools, not all of them are defined in this interface, but helpful error messages
    were added to guide development of builders.

    .. seealso::
        JobBuilderConfigurator

    .. seealso::
        http://en.wikipedia.org/wiki/Builder_pattern
    '''

    def Reset(self):
        '''
        Resets all configurations made to this builder.
        '''


    def Build(self):
        '''
        Actually build jobs. This might mean creating files in a directory, pushing content to a
        web API, or anything that represents the final purpose of jobs_done.
        '''


    def AddRepository(self, repository):
        '''
        Adds repository information to a build. This usually indicates what repository/url/branch
        should be used in a build/job.

        :param Repository repository:
            .. seealso:: Repository
        '''


    def AddVariables(self, variables):
        '''
        Adds variable information to a job.

        Variables are any option unknown to a JobsDoneFile, and are used to represent possible variations
        of a job. They can be used, for example, to create jobs for multiple platforms from a single
        JobsDoneFile.

        :param dict(str,list(str)) variables:
            Dictionary mapping 'variable_name' to a list of values.

        .. seealso::
            JobsDoneFile
        '''


#===================================================================================================
# JobBuilderConfigurator
#===================================================================================================
class JobBuilderConfigurator(object):
    '''
    Class used to configure `IJobBuilder`s using `JobsDoneFile` and `Repository` information.

    .. seealso:: IJobBuilder
    '''

    @classmethod
    def Configure(cls, builder, jobs_done_file, repository):
        '''
        This simply iterates over data and calls a series of functions in a Builder. Functions
        called are determined by options in `jobs_done_file` by converting the option names to camel case.
            e.g.: option 'junit_patterns' will trigger a call to builder.AddJunitPatterns

        :param IJobBuilder builder:
            Builder being configured.

        :param JobsDoneFile jobs_done_file:
            Will be used to extract options that must be configured in `builder`

        :param Repository repository:
            Repository related information used to configure `builder`

        '''
        builder.Reset()
        builder.AddRepository(repository)
        builder.AddVariables(jobs_done_file.variables)

        for option in jobs_done_file.GetKnownOptions():
            option_value = getattr(jobs_done_file, option)
            if option_value is None:
                continue  # Skip unset options

            builder_function_name = 'Add' + option.title().replace('_', '')

            try:
                builder_function = getattr(builder, builder_function_name)
            except AttributeError:
                raise JobBuilderAttributeError(
                    builder,
                    builder_function_name,
                    option
                )

            builder_function(option_value)

        return builder



#===================================================================================================
# JobBuilderAttributeError
#===================================================================================================
class JobBuilderAttributeError(AttributeError):
    '''
    Raised when trying to access a builder function that is not implemented.
    '''
    def __init__(self, builder, attribute, jobs_done_file_option):
        message = '%s "%s" cannot handle option "%s" (could not find function "%s").' % \
            (IJobBuilder.__name__, builder.__class__.__name__, jobs_done_file_option, attribute)

        AttributeError.__init__(self, message)
