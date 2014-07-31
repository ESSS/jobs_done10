# Name of jobs_done file, repositories must contain this file in their root dir to be able to
# create jobs.
import yaml
JOBS_DONE_FILENAME = '.jobs_done.yaml'



#===================================================================================================
# JobsDoneJob
#===================================================================================================
class JobsDoneJob(object):
    '''
    Represents a jobs_done job, parsed from a jobs_done file.

    This is a generic representation, not related to any specific continuous integration tool.
    '''

    # Options that should be forwarded to generators. These are set in JobsDoneJob instances
    # after parsing (setattr(option_name, self, value)), and are available as object fields
    GENERATOR_OPTIONS = {
        # Additional repositories to be used in a job.
        'additional_repositories':list,

        # Patterns to match when looking for boosttest results.
        'boosttest_patterns':list,

        # Batch script commands used to build a project.
        'build_batch_commands':list,

        # Shell script commands used to build a project.
        'build_shell_commands':list,

        # Time based triggers for job (Jenkins)
        'cron':str,

        # Regex pattern to be matched from a job output and used as job description. (Jenkins)
        # Requires https://wiki.jenkins-ci.org/display/JENKINS/Description+Setter+Plugin
        'description_regex':str,

        # The format for the job display name.
        'display_name':str,

        # Emails to be sent out for failed builds
        'email_notification':(dict, str),

        # Additional git options.
        # Uses same options available for git repos under `additional_repositories`
        'git':dict,

        # List of patterns to match when looking for jsunit test results.
        # Requires https://wiki.jenkins-ci.org/display/JENKINS/JSUnit+plugin
        'jsunit_patterns':list,

        # List of patterns to match when looking for junit test results.
        'junit_patterns':list,

        # A "label expression" that is used to match slave nodes.
        'label_expression':str,

        # Notifies Stash when a build passes
        # Requires https://wiki.jenkins-ci.org/display/JENKINS/StashNotifier+Plugin
        # e.g.
        #    notify_stash = {'url' : 'stash.com', 'username' : 'user', 'password' : 'pass'}
        'notify_stash':(dict, str),

        # Definition of parameters available to this job.
        # Uses jenkins-job-builder syntax parsed by yaml.
        # .. seealso:: http://ci.openstack.org/jenkins-job-builder/parameters.html
        #
        # e.g.
        #     parameters = [{'choices' : ['1', '2'], 'name' : 'my_param'}]
        'parameters':list,

        # Poll SCM for changes and trigger jobs based on a schedule (Jenkins)
        'scm_poll':str,

        # Job timeout in minutes
        'timeout' : str
    }

    # All parsed options
    PARSEABLE_OPTIONS = GENERATOR_OPTIONS.copy()
    PARSEABLE_OPTIONS.update({
        # list(str) branch_patterns:
        #    A list of regexes to matcvh against branch names.
        #    Jobs for a branch will only be created if any of this pattern matches that name.
        #    .. note:: Uses python `re` syntax.
        'branch_patterns':list,

        # dict matrix:
        #     A dict that represents all possible job combinations created from this file.
        #
        #     When a jobs_done file is parsed, it can contain variables that form a matrix. For each
        #     possible combination of these variables, a JobsDoneJob class is created. They can be used
        #     for things such as creating jobs for multiple platforms from a single JobsDoneJob.
        #
        #     For example, if our file describes this matrix:
        #         matrix:
        #           planet:
        #           - earth
        #           - mars
        #
        #           moon:
        #           - europa
        #           - ganymede
        #
        #     This file's `matrix` will be:
        #         {'planet' : ['earth', 'mars], 'moon' : ['europa', 'ganymede']}
        #
        #     This file's `matrix_row` will have one of these values (one for each JobsDoneJob created):
        #         {'planet' : 'earth', 'moon' : 'europa'}
        #         {'planet' : 'earth', 'moon' : 'ganymede'}
        #         {'planet' : 'mars', 'moon' : 'europa'}
        #         {'planet' : 'mars', 'moon' : 'ganymede'}
        'matrix':dict,
    })


    def __init__(self):
        '''
        :ivar dict(str,str) matrix_row:
            A dict that represents a single row from this file's `matrix`.

            .. seealso:: `matrix`@PARSEABLE_OPTIONS
        '''
        self.matrix_row = None

        # Initialize known options with None
        for option_name in self.PARSEABLE_OPTIONS:
            setattr(self, option_name, None)


    @classmethod
    def CreateFromYAML(cls, yaml_contents, repository):
        '''
        Creates JobsDoneJob's from a jobs_done file in a repository.

        This method parses that file and returns as many jobs as necessary. This number may vary
        based on how big the job matrix is, and no jobs might be generated at all if the file is
        empty or the current repository branch does not match anything in `branch_patterns` defined
        in the file.

        Jobs parsed by this method can use a string replacement syntax in their contents, and
        those strings can be replaced by the current values in the matrix_row for that job, or a few
        special replacements available to all jobs:
        - name: Name of the repository for which we are creating jobs
        - branch: Name of the repository branch for which we are creating jobs

        :param str yaml_contents:
            Contents of a jobs_done file, in YAML format.

        :param Repository repository:
            Repository information for jobs created from `yaml_contents`

        :return list(JobsDoneJob):
            List of jobs created for parameters.

        .. seealso:: JobsDoneJob
            For known options accepted in yaml_contents

        Example:
            repository = Repository(url='http://space.git', branch='milky_way')
            yaml_contents =
                """
                junit_patterns:
                - "{planet}-{branch}.xml"

                matrix:
                    planet:
                    - earth
                    - mars
                """

            resulting JobsDoneJob's:
                JobsDoneJob(junit_patterns="earth-milky_way.xml", matrix_row={'planet': 'earth'}),
                JobsDoneJob(junit_patterns="mars-milky_way.xml", matrix_row={'planet': 'mars'}),

        .. seealso: pytest_jobs_done_job
            For other examples
        '''
        if yaml_contents is None:
            return []

        # Avoid errors with tabs at the end of file
        yaml_contents = yaml_contents.strip()

        # Load yaml
        jd_data = yaml.load(yaml_contents, Loader=cls._JobsDoneYamlLoader)
        if not jd_data:
            return []

        # Search for unknown options and type errors
        for option_name, option_value in jd_data.iteritems():
            option_name = option_name.rsplit(':', 1)[-1]
            if option_name not in JobsDoneJob.PARSEABLE_OPTIONS:
                raise UnknownJobsDoneFileOption(option_name)

            from ben10.foundation.types_ import AsList
            obtained_type = type(option_value)
            expected_types = AsList(JobsDoneJob.PARSEABLE_OPTIONS[option_name])
            if obtained_type not in expected_types:
                raise JobsDoneFileTypeError(option_name, obtained_type, expected_types)

        # List all possible matrix_rows
        matrix_rows = cls._MatrixRow.CreateFromDict(jd_data.get('matrix', {}))

        # Raise an error if a condition can never be matched
        for option_name, option_value in jd_data.iteritems():
            if ':' in option_name:
                conditions = option_name.split(':')[:-1]

                matches = []
                for row in matrix_rows:
                    matches.append(cls._MatchConditions(conditions, row.full_dict, branch=cls._MATCH_ANY))

                if not any(matches):
                    raise UnmatchableConditionError(option_name)

        import re
        jobs_done_jobs = []
        for matrix_row in matrix_rows:
            jobs_done_job = JobsDoneJob()

            jobs_done_job.repository = repository
            jobs_done_job.matrix_row = matrix_row.simple_dict

            # Re-read jd_data replacing all matrix variables with their values in the current
            # matrix_row and special replacement variables 'branch' and 'name', based on repository.
            format_dict = {
                'branch':repository.branch,
                'name':repository.name
            }
            format_dict.update(matrix_row.simple_dict)
            jd_string = (yaml.dump(jd_data, default_flow_style=False)[:-1])
            formatted_jd_string = jd_string.format(**format_dict)
            jd_formatted_data = yaml.load(formatted_jd_string)

            for option_name, option_value in jd_formatted_data.iteritems():

                # Check for option conditions
                if ':' in option_name:
                    conditions = option_name.split(':')[:-1]
                    option_name = option_name.split(':')[-1]

                    # Skip this option if any condition is not met
                    if not cls._MatchConditions(conditions, matrix_row.full_dict, branch=[repository.branch]):
                        continue

                # If all conditions are met, set this option in the job.
                setattr(jobs_done_job, option_name, option_value)

            # Only create this job if this branch is acceptable (matches anything in branch_patterns)
            branch_patterns = jobs_done_job.branch_patterns or ['.*']
            if any([re.match(pattern, repository.branch) for pattern in branch_patterns]):
                jobs_done_jobs.append(jobs_done_job)

        return jobs_done_jobs


    @classmethod
    def CreateFromFile(cls, filename, repository):
        '''
        :param str filename:
            Path to a jobs_done file

        :param repository:
            .. seealso:: CreateFromYAML
        '''
        from ben10.filesystem import GetFileContents
        return cls.CreateFromYAML(GetFileContents(filename), repository)


    _MATCH_ANY = object()
    @classmethod
    def _MatchConditions(cls, conditions, *fact_dicts, **extra_facts):
        '''
        Check if the given conditions matches a set of facts.

        e.g.:
            fact_dicts = {'planet' : ['terra', 'earth'], 'moon' : cls._MATCH_ANY}
            extra_facts = {'branch' : 'master'}

            There are multiple possible values for 'planet' because the user can define aliases.

            This would match for the given conditions:
                ['planet-terra']
                ['planet-terra', 'branch-master']
                ['planet-earth', 'branch-master']
                ['planet-earth', 'moon-doesnt_matter']

            And not match:
                ['planet-mars']
                ['planet-earth', 'branch-release']


        :param list(str) conditions:
            A list of conditions in the form 'name-value'.

        :param list(dict(str,list(str))) fact_dicts:
            A list of dictionary of facts, in the form {name:list(value)} or {name:cls._MATCH_ANY}

        :param dict(str,list(str)) extra_facts:
            Additional facts passed as kwargs that are appended to received `fact_dicts`

        :return boolean:
            Returns True if all the given conditions matches the given facts.
        '''
        import re
        # Assemble facts
        facts = {}
        for fact_dict in fact_dicts:
            facts.update(fact_dict)
        facts.update(extra_facts)

        def _Match(condition):
            variable_name, match_mask = condition.split('-', 1)
            fact_values = facts[variable_name]
            return fact_values is cls._MATCH_ANY or any(re.match(match_mask, fact) for fact in fact_values)

        return all(map(_Match, conditions))


    class _MatrixRow(object):
        '''
        Holds a combination of matrix values.

        :ivar dict(str,list(str)) full_dict:
            Maps names to a list of values.
            The first value represents the main value, all others are considered aliases

        :ivar dict(str,str) simple_dict:
            Maps names to the main value. .. seealso:: `full_dict`
        '''

        def __init__(self, names, values):
            '''
            Create a matrix-row instance from a matrix-dict and a value tuple.

            :param list(str) names:
                List of variables names.

            :param list(str) values:
                List of values assumed by this row.
                One value for each name in names parameter.
            '''
            values = tuple(i.split(',') for i in values)
            self.full_dict = dict(zip(names, values))
            self.simple_dict = dict((i, j[0]) for (i, j) in self.full_dict.iteritems())


        def __str__(self):
            '''
            String representation for tests.

            :return str:
            '''
            result = []
            for i_name, i_values in self.full_dict.iteritems():
                for j_value in i_values:
                    result.append('%s-%s' % (i_name, j_value))
            return '<MatrixRow %s>' % ' '.join(result)


        @classmethod
        def CreateFromDict(self, matrix_dict):
            '''
            Write up all matrix_rows from possible combinations of the job matrix

            Inspired on http://stackoverflow.com/a/3873734/1209622

            :param dict(str:tuple) matrix_dict:
                A dictionary mapping names to values.
            '''
            import itertools as it

            # Create all combinations of values available in the matrix
            names = matrix_dict.keys()
            value_combinations = it.product(*matrix_dict.values())
            return [JobsDoneJob._MatrixRow(names, v) for v in value_combinations]


    class _JobsDoneYamlLoader(yaml.loader.BaseLoader):
        '''
        Custom loader that treats everything as ascii strings
        '''
        def construct_scalar(self, *args, **kwargs):
            value = yaml.loader.BaseLoader.construct_scalar(self, *args, **kwargs)
            return value.encode('ascii')



#===================================================================================================
# UnknownJobsDoneJobOption
#===================================================================================================
class UnknownJobsDoneFileOption(RuntimeError):
    '''
    Raised when parsing an unknown option.

    :ivar str option_name:
        Name of the unknown option.
    '''
    def __init__(self, option_name):
        self.option_name = option_name
        RuntimeError.__init__(
            self,
            'Received unknown option "%s".\n\nAvailable options are:\n%s' % \
            (option_name, '\n'.join('- ' + o for o in sorted(JobsDoneJob.PARSEABLE_OPTIONS)))
        )



#===================================================================================================
# JobsDoneFileTypeError
#===================================================================================================
class JobsDoneFileTypeError(TypeError):
    '''
    Raised when parsing an option with a bad type.

    :ivar str option_name:
        Name of the option that was set with a bad type

    :ivar type obtained_type:
        Obtained (bad) type
        e.g.
            list, str

    :ivar iter(type) accepted_types:
        Accepted (good) types
        e.g.
            (list,)
            (dict, str)
    '''
    def __init__(self, option_name, obtained_type, accepted_types):
        self.option_name = option_name
        self.obtained_type = obtained_type
        self.accepted_types = accepted_types

        TypeError.__init__(
            self,
            'On option "%s". Expected one of "%s" but got "%s".' % \
            (option_name, accepted_types, obtained_type)
        )



#===================================================================================================
# UnmatchableConditionError
#===================================================================================================
class UnmatchableConditionError(ValueError):
    '''
    Raised when declaring a condition that can never be matches based on available matrix rows.

    :ivar str option:
        Option with a condition that can't be matched.
        e.g.:
            'planet-pluto:junit_patterns'
    '''
    def __init__(self, option):
        self.option = option

        ValueError.__init__(
            self,
            'Condition "%s" can never be matched based on possible matrix rows.' % option
        )
