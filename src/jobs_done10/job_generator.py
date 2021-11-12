class IJobGenerator(object):
    """
    Interface for job generators.

    These generators are responsible for creating continuous integration jobs for any particular
    tool, such as Jenkins or Bamboo.

    Generators must implement this interface, which represents the bare minimum of options
    available, but this is more than likely not enough to build a complete job. Configurations set
    in a generators come from a `JobGeneratorConfigurator`, which itself extracts them from a
    `JobsDoneJob`.

    As new options can be easily added to `JobsDoneJob`, and some options might not make sense for
    different tools, not all of them are defined in this interface, but helpful error messages
    were added to guide development of generators.

    .. seealso::
        JobGeneratorConfigurator

    .. seealso::
        http://en.wikipedia.org/wiki/Builder_pattern
    """

    def Reset(self):
        """
        Resets all configurations made to this generator.
        """

    def SetRepository(self, repository):
        """
        :param Repository repository:
            Repository information for jobs created by this generator.
        """

    def SetMatrix(self, matrix, matrix_row):
        """
        Sets current matrix and matrix_row of this job.

        :param dict(unicode,list(unicode)) matrix:
            .. seealso::
                JobsDoneJob

        :param dict(unicode,unicode) matrix_row:
            .. seealso::
                JobsDoneJob
        """


class JobGeneratorConfigurator(object):
    """
    Class used to configure `IJobGenerator`s using `JobsDoneJob`.

    .. seealso:: IJobGenerator
    """

    @classmethod
    def Configure(cls, generator, jobs_done_job):
        """
        This simply iterates over data and calls a series of functions in a generator. Functions
        called are determined by options in `jobs_done_job` by converting the option names to camel case.
            e.g.: option 'junit_patterns' will trigger a call to generator.SetJunitPatterns

        :param IJobGenerator generator:
            Generator being configured.

        :param JobsDoneJob jobs_done_job:
            Will be used to extract options that must be configured in `generator`
        """
        generator.SetRepository(jobs_done_job.repository)
        generator.Reset()
        generator.SetMatrix(jobs_done_job.matrix, jobs_done_job.matrix_row)

        for option in jobs_done_job.GENERATOR_OPTIONS:
            option_value = getattr(jobs_done_job, option)
            if option_value is None:
                continue  # Skip unset options

            # Find function name associated with the option being processed
            generator_function_name = "Set" + option.title().replace("_", "")

            # Obtain and call that function with the option value
            try:
                generator_function = getattr(generator, generator_function_name)
            except AttributeError:
                raise JobGeneratorAttributeError(
                    generator, generator_function_name, option
                )

            generator_function(option_value)

        return generator


class JobGeneratorAttributeError(AttributeError):
    """
    Raised when trying to access a generator function that is not implemented.
    """

    def __init__(self, generator, attribute, jobs_done_job_option):
        message = (
            '%s "%s" cannot handle option "%s" (could not find function "%s").'
            % (
                IJobGenerator.__name__,
                generator.__class__.__name__,
                jobs_done_job_option,
                attribute,
            )
        )

        AttributeError.__init__(self, message)
