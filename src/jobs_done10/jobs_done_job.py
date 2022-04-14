import io

import yaml


# Name of jobs_done file, repositories must contain this file in their root dir to be able to
# create jobs.
JOBS_DONE_FILENAME = ".jobs_done.yaml"


class JobsDoneJob(object):
    """
    Represents a jobs_done job, parsed from a jobs_done file.

    This is a generic representation, not related to any specific continuous integration tool.
    """

    # Options that should be forwarded to generators. These are set in JobsDoneJob instances
    # after parsing (setattr(option_name, self, value)), and are available as object fields
    #
    # NOTE TO DEVELOPERS: try to keep options in alphabetical order to simplify maintenance
    GENERATOR_OPTIONS = {
        # Additional repositories to be used in a job.
        "additional_repositories": list,
        # Job authentication token used to execute it remotely.
        "auth_token": str,
        # Patterns to match when looking for boosttest results.
        "boosttest_patterns": list,
        # Batch script commands used to build a project.
        "build_batch_commands": list,
        # Shell script commands used to build a project.
        "build_shell_commands": list,
        # Python commands used to build a project.
        "build_python_commands": list,
        # Process job output to handle ansi color escapes.
        # Should be one of xterm (default if empty), vga, css, gnome-terminal.
        # Requires https://wiki.jenkins-ci.org/display/JENKINS/AnsiColor+Plugin
        "console_color": str,
        # Configures coverage in a CI job
        #
        # On Jenkins, this requires [Cobertura Plugin](
        # https://wiki.jenkins-ci.org/display/JENKINS/Cobertura+Plugin) to work.
        #
        # Options:
        # * report_pattern: unicode
        #   File name pattern that can be used to locate the cobertura xml report files, for
        #   instance, `**/build/coverage/*.xml`
        # * healthy: dict|None
        #   Defines threshold necessary for build to be healthy. Can have keys `method`, `line` and
        #   `conditional`. If key is omitted it defaults to 80.
        # * unhealthy: dict|None
        #   Defines threshold necessary for build to be unhealthy. Can have keys `method`, `line`
        #   and `conditional`. If key is omitted it defaults to 0.
        # * failing: dict|None
        #   Defines threshold necessary for build to fail. Can have keys `method`, `line`
        #   and `conditional`. If key is omitted it defaults to 0.
        "coverage": dict,
        # Time based triggers for job (Jenkins)
        "cron": str,
        # Custom workspace. To maintain the same location as the default workspace prefix it with
        # "workspace/"
        "custom_workspace": str,
        # Regex pattern to be matched from a job output and used as job description. (Jenkins)
        # Requires https://wiki.jenkins-ci.org/display/JENKINS/Description+Setter+Plugin
        "description_regex": str,
        # The format for the job display name.
        "display_name": str,
        # Emails to be sent out for failed builds
        "email_notification": (dict, str),
        # Additional git options.
        # Uses same options available for git repos under `additional_repositories`
        "git": dict,
        # List of patterns to match when looking for jsunit test results.
        # Requires https://wiki.jenkins-ci.org/display/JENKINS/JSUnit+plugin
        "jsunit_patterns": list,
        # List of patterns to match when looking for junit test results.
        "junit_patterns": list,
        # A "label expression" that is used to match slave nodes.
        "label_expression": str,
        # Notification (HTTP/JSON)
        # https://wiki.jenkins-ci.org/display/JENKINS/Notification+Plugin
        # * protocol: HTTP (optional)
        # * format: JSON (optional)
        # * url: https://requestb.in/12345678
        "notification": dict,
        # Notifies Stash when a build passes
        # Requires https://wiki.jenkins-ci.org/display/JENKINS/StashNotifier+Plugin
        # e.g.
        #    notify_stash = {'url' : 'stash.com', 'username' : 'user', 'password' : 'pass'}
        "notify_stash": (dict, str),
        # Definition of parameters available to this job.
        # Uses jenkins-job-builder syntax parsed by yaml.
        # .. seealso:: http://ci.openstack.org/jenkins-job-builder/parameters.html
        #
        # e.g.
        #     parameters = [{'choices' : ['1', '2'], 'name' : 'my_param'}]
        "parameters": list,
        # Poll SCM for changes and trigger jobs based on a schedule (Jenkins)
        "scm_poll": str,
        # Slack notification
        # * room: general
        # * token: 123123123123123123123
        # * url: http://eden.esss.com.br/jenkins
        "slack": dict,
        # Job timeout in minutes
        "timeout": str,
        # Job timeout in seconds without console activity
        "timeout_no_activity": str,
        # Enable timestamps on the build output
        # https://wiki.jenkins-ci.org/display/JENKINS/Timestamper
        "timestamps": str,
        # Configures parsing of warnings and static analysis in a CI job
        #
        # On Jenkins, this requires [Warnings Plugin](
        # https://wiki.jenkins-ci.org/display/JENKINS/Warnings+Plugin) to work.
        #
        # Configuration Example:
        # ```yaml
        # warnings:
        #   console:
        #     - parser: Clang (LLCM based)
        #     - parser: PyLint
        #   file:
        #     - parser: CppLint
        #       file_pattern: *.cpplint
        #     - parser: CodeAnalysis
        #       file_pattern: *.codeanalysis
        # ```
        "warnings": dict,
        # Trigger other jobs after this jobs finishes
        # On Jenkins this requires the [Parameterized Trigger Plugin]
        # (https://wiki.jenkins.io/display/JENKINS/Parameterized+Trigger+Plugin) to work.
        #
        # Configuration example:
        # ```yaml
        # trigger_jobs:
        #   names:
        #     - myrepo-{branch}-synthetic-{platform}
        #   condition: SUCCESS  # can be one of: SUCCESS, UNSTABLE, FAILED, ALWAYS. Defaults to SUCCESS.
        #   parameters:  # optional
        #     - PARAM1=VALUE1
        #     - PARAM2=VALUE2
        # ```
        "trigger_jobs": dict,
    }

    # All parsed options
    PARSEABLE_OPTIONS = GENERATOR_OPTIONS.copy()
    PARSEABLE_OPTIONS.update(
        {
            # list(unicode) branch_patterns:
            #    A list of regexes to matcvh against branch names.
            #    Jobs for a branch will only be created if any of this pattern matches that name.
            #    .. note:: Uses python `re` syntax.
            "branch_patterns": list,
            # unicode exclude:
            #     Determines if a job should be excluded (usually used with matrix flags)
            #     Defaults to 'false'
            "exclude": str,
            # unicode ignore_unmatchable:
            #    If 'true', will not raise errors when an unmatchable condition is found.
            #    Defaults to 'false'
            "ignore_unmatchable": str,
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
            "matrix": dict,
        }
    )

    def __init__(self):
        """
        :ivar dict(unicode,unicode) matrix_row:
            A dict that represents a single row from this file's `matrix`.

            .. seealso:: `matrix`@PARSEABLE_OPTIONS
        """
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

        :param unicode yaml_contents:
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
        jd_data = yaml.load(yaml_contents, Loader=yaml.loader.BaseLoader)
        if not jd_data:
            raise ValueError("Could not parse anything from .yaml contents")

        # Search for unknown options and type errors
        for option_name, option_value in jd_data.items():
            option_name = option_name.rsplit(":", 1)[-1]
            if option_name not in JobsDoneJob.PARSEABLE_OPTIONS:
                raise UnknownJobsDoneFileOption(option_name)

            obtained_type = type(option_value)
            from jobs_done10.common import AsList

            expected_types = AsList(JobsDoneJob.PARSEABLE_OPTIONS[option_name])
            if obtained_type not in expected_types:
                raise JobsDoneFileTypeError(
                    option_name, obtained_type, expected_types, option_value
                )

        # List all possible matrix_rows
        matrix_rows = cls._MatrixRow.CreateFromDict(jd_data.get("matrix", {}))

        ignore_unmatchable = Boolean(jd_data.get("ignore_unmatchable", "false"))
        if not ignore_unmatchable:
            # Raise an error if a condition can never be matched
            for yaml_dict in cls._IterDicts(jd_data):
                for key, _value in yaml_dict.items():
                    if ":" in key:
                        conditions = key.split(":")[:-1]

                        for row in matrix_rows:
                            if cls._MatchConditions(
                                conditions, row.full_dict, branch=cls._MATCH_ANY
                            ):
                                break
                        else:
                            raise UnmatchableConditionError(key)

        import re

        jobs_done_jobs = []
        for matrix_row in matrix_rows:
            jobs_done_job = JobsDoneJob()

            jobs_done_job.repository = repository
            jobs_done_job.matrix_row = matrix_row.simple_dict

            # Re-read jd_data replacing all matrix variables with their values in the current
            # matrix_row and special replacement variables 'branch' and 'name', based on repository.
            format_dict = {"branch": repository.branch, "name": repository.name}
            format_dict.update(matrix_row.simple_dict)
            jd_formatted_data = cls._GetFormattedYAMLData(jd_data, format_dict)
            # Re-write formatted_data dict ignoring/replacing dict keys based on matrix
            for yaml_dict in cls._IterDicts(jd_formatted_data):
                matched_conditions = {}
                for key, option_value in list(yaml_dict.items()):
                    if ":" not in key:
                        continue

                    conditions = key.split(":")[:-1]
                    option_name = key.split(":")[-1]

                    # Remove the key with condition text
                    del yaml_dict[key]

                    # If the condition matches, add the new key (containing just the option_name)
                    if not cls._MatchConditions(
                        conditions, matrix_row.full_dict, branch=[repository.branch]
                    ):
                        continue

                    cls._CheckAmbiguousConditions(
                        yaml_dict,
                        matched_conditions,
                        option_name,
                        option_value,
                        conditions,
                    )

                    if cls._ShouldOverride(matched_conditions, option_name, conditions):
                        yaml_dict[option_name] = option_value
                        matched_conditions[option_name] = set(conditions)

            # Set surviving options in job.
            for option_name, option_value in jd_formatted_data.items():
                setattr(jobs_done_job, option_name, option_value)

            # Do not create a job if exclude=='yes'
            if jd_formatted_data.get("exclude", "no") == "yes":
                continue

            # Do not create a job if there is no match for this branch
            branch_patterns = jobs_done_job.branch_patterns or [".*"]
            if not any(
                [re.match(pattern, repository.branch) for pattern in branch_patterns]
            ):
                continue

            jobs_done_jobs.append(jobs_done_job)

        return jobs_done_jobs

    @classmethod
    def _GetFormattedYAMLData(cls, yaml_data, format_dict):
        if isinstance(yaml_data, str):
            return yaml_data.format(**format_dict)
        elif isinstance(yaml_data, list):
            return [cls._GetFormattedYAMLData(d, format_dict) for d in yaml_data]
        elif isinstance(yaml_data, dict):
            return {
                k.format(**format_dict): cls._GetFormattedYAMLData(v, format_dict)
                for k, v in yaml_data.items()
            }
        else:
            raise ValueError("Invalid yaml data type: {}".format(yaml_data.__class__))

    @classmethod
    def _CheckAmbiguousConditions(
        cls,
        yaml_dict,
        previous_matched_conditions,
        option_name,
        option_value,
        conditions,
    ):
        if option_name not in previous_matched_conditions:
            return
        # If the value is the same we don't care if the conditions are ambiguous
        if yaml_dict[option_name] == option_value:
            return

        previous_conditions = set(previous_matched_conditions[option_name])
        conditions = set(conditions)

        def _IsAmbiguous():
            return not previous_conditions.issubset(
                conditions
            ) and not conditions.issubset(previous_conditions)

        if _IsAmbiguous():
            import textwrap

            raise ValueError(
                textwrap.dedent(
                    """\
                Option {option_name} has ambiguous conditions and would be overridden
                Old value: {old_value}
                New value: {new_value}
                Old conditions: {old_conditions}
                New conditions: {new_conditions}"""
                ).format(
                    option_name=option_name,
                    old_value=yaml_dict[option_name],
                    new_value=option_value,
                    old_conditions=previous_conditions,
                    new_conditions=conditions,
                )
            )

    @classmethod
    def _ShouldOverride(cls, previous_matched_conditions, option_name, conditions):
        if option_name not in previous_matched_conditions:
            return True

        previous_conditions = set(previous_matched_conditions[option_name])
        conditions = set(conditions)
        return conditions.issuperset(previous_conditions)

    @classmethod
    def CreateFromFile(cls, filename, repository):
        """
        :param unicode filename:
            Path to a jobs_done file

        :param repository:
            .. seealso:: CreateFromYAML
        """
        with io.open(filename, encoding="utf-8") as f:
            contents = f.read()
        return cls.CreateFromYAML(contents, repository)

    _MATCH_ANY = object()

    @classmethod
    def _MatchConditions(cls, conditions, *fact_dicts, **extra_facts):
        """
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


        :param list(unicode) conditions:
            A list of conditions in the form 'name-value'.

        :param list(dict(unicode,list(unicode))) fact_dicts:
            A list of dictionary of facts, in the form {name:list(value)} or {name:cls._MATCH_ANY}

        :param dict(unicode,list(unicode)) extra_facts:
            Additional facts passed as kwargs that are appended to received `fact_dicts`

        :return boolean:
            Returns True if all the given conditions matches the given facts.
        """
        import re

        # Assemble facts
        facts = {}
        for fact_dict in fact_dicts:
            facts.update(fact_dict)
        facts.update(extra_facts)

        def _Match(condition):
            variable_name, match_mask = condition.split("-", 1)
            fact_values = facts[variable_name]
            return fact_values is cls._MATCH_ANY or any(
                re.match(match_mask, fact) for fact in fact_values
            )

        return all(map(_Match, conditions))

    class _MatrixRow(object):
        """
        Holds a combination of matrix values.

        :ivar dict(unicode,list(unicode)) full_dict:
            Maps names to a list of values.
            The first value represents the main value, all others are considered aliases

        :ivar dict(unicode,unicode) simple_dict:
            Maps names to the main value. .. seealso:: `full_dict`
        """

        def __init__(self, names, values):
            """
            Create a matrix-row instance from a matrix-dict and a value tuple.

            :param list(unicode) names:
                List of variables names.

            :param list(unicode) values:
                List of values assumed by this row.
                One value for each name in names parameter.
            """
            values = tuple(i.split(",") for i in values)
            self.full_dict = dict(zip(names, values))
            self.simple_dict = dict((i, j[0]) for (i, j) in self.full_dict.items())

        @classmethod
        def CreateFromDict(self, matrix_dict):
            """
            Write up all matrix_rows from possible combinations of the job matrix

            Inspired on http://stackoverflow.com/a/3873734/1209622

            :param dict(unicode:tuple) matrix_dict:
                A dictionary mapping names to values.
            """
            import itertools as it

            # Create all combinations of values available in the matrix
            names = list(matrix_dict.keys())
            value_combinations = it.product(*list(matrix_dict.values()))
            return [JobsDoneJob._MatrixRow(names, v) for v in value_combinations]

    @classmethod
    def _IterDicts(cls, obj):
        """
        Iterates over all dicts in an object.

        Works recursively for lists and dicts.

        :param object obj:

        :yield dict:
            Dicts found by iterating over `obj`
        """
        if isinstance(obj, dict):
            yield obj

            for sub_obj in obj.values():
                for x in cls._IterDicts(sub_obj):
                    yield x

        if isinstance(obj, list):
            for sub_obj in obj:
                for x in cls._IterDicts(sub_obj):
                    yield x


class UnknownJobsDoneFileOption(RuntimeError):
    """
    Raised when parsing an unknown option.

    :ivar unicode option_name:
        Name of the unknown option.
    """

    def __init__(self, option_name):
        self.option_name = option_name
        RuntimeError.__init__(
            self,
            'Received unknown option "%s".\n\nAvailable options are:\n%s'
            % (
                str(option_name),
                "\n".join("- " + str(o) for o in sorted(JobsDoneJob.PARSEABLE_OPTIONS)),
            ),
        )


class JobsDoneFileTypeError(TypeError):
    """
    Raised when parsing an option with a bad type.

    :ivar unicode option_name:
        Name of the option that was set with a bad type

    :ivar type obtained_type:
        Obtained (bad) type
        e.g.
            list, unicode

    :ivar iter(type) accepted_types:
        Accepted (good) types
        e.g.
            (list,)
            (dict, unicode)
    """

    def __init__(self, option_name, obtained_type, accepted_types, option_value):
        self.option_name = option_name
        self.obtained_type = obtained_type
        self.accepted_types = accepted_types
        self.option_value = option_value

        TypeError.__init__(
            self,
            'On option "%s". Expected one of "%s" but got "%s". Value:\n%r'
            % (option_name, accepted_types, obtained_type, option_value),
        )


class UnmatchableConditionError(ValueError):
    """
    Raised when declaring a condition that can never be matches based on available matrix rows.

    :ivar unicode option:
        Option with a condition that can't be matched.
        e.g.:
            'planet-pluto:junit_patterns'
    """

    def __init__(self, option):
        self.option = option

        ValueError.__init__(
            self,
            'Condition "%s" can never be matched based on possible matrix rows.'
            % option,
        )


_TRUE_VALUES = ["TRUE", "YES", "1"]
_FALSE_VALUES = ["FALSE", "NO", "0"]
_TRUE_FALSE_VALUES = _TRUE_VALUES + _FALSE_VALUES


def Boolean(text):
    """
    :param unicode text:
        A text semantically representing a boolean value.

    :rtype: bool
    :returns:
        Returns a boolean represented by the given text.
    """
    text_upper = text.upper()
    if text_upper not in _TRUE_FALSE_VALUES:
        raise ValueError(
            "The value does not match any known value (case insensitive): %s (%s)"
            % (text, _TRUE_FALSE_VALUES)
        )
    return text_upper in _TRUE_VALUES
