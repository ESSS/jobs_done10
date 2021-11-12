"""
Module containing everything related to Jenkins in jobs_done10.

This includes a generator, job publishers, constants and command line interface commands.
"""
import io
from collections import namedtuple

from jobs_done10.common import AsList


#
# Represents a Jenkins job.
#
# :cvar unicode name:
#     Job name
#
# :cvar Repository repository:
#     Repository that this job belongs to
#
# :cvar unicode xml:
#     Job XML contents
JenkinsJob = namedtuple("JenkinsJob", "name repository xml")


class JenkinsXmlJobGenerator(object):
    """
    Generates Jenkins jobs.
    """

    def __init__(self):
        # Initialize some variables
        self.__jjgen = None
        self.__scm_plugin = None

        self.repository = None

    def Reset(self):
        from jobs_done10.xml_factory import XmlFactory

        self.xml = XmlFactory("project")
        self.xml["description"] = "<!-- Managed by Job's Done -->"
        self.xml["keepDependencies"] = xmls(False)
        self.xml["logRotator/daysToKeep"] = 7
        self.xml["logRotator/numToKeep"] = -1
        self.xml["logRotator/artifactDaysToKeep"] = -1
        self.xml["logRotator/artifactNumToKeep"] = -1
        self.xml["blockBuildWhenDownstreamBuilding"] = xmls(False)
        self.xml["blockBuildWhenUpstreamBuilding"] = xmls(False)
        self.xml["concurrentBuild"] = xmls(False)
        self.xml["canRoam"] = xmls(False)

        # Configure git SCM
        self.git = self.xml["scm"]
        self.git["@class"] = "hudson.plugins.git.GitSCM"

        self.SetGit(
            dict(
                url=self.repository.url,
                target_dir=self.repository.name,
                branch=self.repository.branch,
            )
        )

        self.job_name = None

    @classmethod
    def GetJobGroup(cls, repository):
        """
        A single repository/branch combination can create many jobs, depending on the job matrix.

        This variable is used to identify jobs within the same group.

        :param Repository repository:
            A repository that can contain jobs

        :returns unicode:
            Job group for the given repository
        """
        return repository.name + "-" + repository.branch

    def GetJob(self):
        """
        :return JenkinsJob:
            Job created by this generator.
        """
        # Mailer must always be at the end of the XML contents, otherwise Jenkins might try to
        # send emails before checking if tests passed.
        publishers = self.xml.root.find("publishers")
        if publishers is not None:
            mailer = publishers.find("hudson.tasks.Mailer")
            if mailer is not None:
                publishers.remove(mailer)
                publishers.append(mailer)

        return JenkinsJob(
            name=self.job_name,
            repository=self.repository,
            xml=self.xml.GetContents(xml_header=True),
        )

    # ===============================================================================================
    # Configurator functions (.. seealso:: JobsDoneJob ivars for docs)
    # ===============================================================================================
    def SetRepository(self, repository):
        self.repository = repository

    def SetMatrix(self, matrix, matrix_row):
        label_expression = self.repository.name
        self.job_name = self.GetJobGroup(self.repository)

        if matrix_row:
            row_representation = "-".join(
                [
                    value
                    for key, value in sorted(matrix_row.items())
                    # Matrix rows with only one possible value do not affect the representation
                    if len(matrix[key]) > 1
                ]
            )

            if row_representation:  # Might be empty
                label_expression += "-" + row_representation
                self.job_name += "-" + row_representation

        self.SetLabelExpression(label_expression)

    def SetAdditionalRepositories(self, repositories):
        # Remove current git configuration from xml
        self.xml.root.remove(self.git.root)

        # Create a MultiSCM block
        multi_scm = self.xml["scm"]
        multi_scm["@class"] = "org.jenkinsci.plugins.multiplescms.MultiSCM"

        # Add the current git implementation to multi_scm
        self.git.root.attrib = {}
        self.git.root.tag = "hudson.plugins.git.GitSCM"
        multi_scm["scms"].root.append(self.git.root)

        # Replace main git with the one inside multi_scm
        self.git = multi_scm["scms/hudson.plugins.git.GitSCM"]

        # Add additional repositories
        for repo in repositories:
            self.SetGit(
                repo["git"], git_xml=multi_scm["scms/hudson.plugins.git.GitSCM+"]
            )

    def SetAuthToken(self, auth_token):
        self.xml["authToken"] = auth_token

    def SetBoosttestPatterns(self, boosttest_patterns):
        self._SetXunit("BoostTestJunitHudsonTestType", boosttest_patterns)

    def SetBuildBatchCommands(self, build_batch_commands):
        for command in build_batch_commands:
            if isinstance(command, list):
                self.SetBuildBatchCommands(command)
            else:
                # batch files must have \r\n as EOL or weird bugs happen (jenkins web ui add \r).
                self.xml["builders/hudson.tasks.BatchFile+/command"] = command.replace(
                    "\n", "\r\n"
                )

    def SetBuildShellCommands(self, build_shell_commands):
        for command in build_shell_commands:
            if isinstance(command, list):
                self.SetBuildShellCommands(command)
            else:
                self.xml["builders/hudson.tasks.Shell+/command"] = command

    def SetBuildPythonCommands(self, build_shell_commands):
        for command in build_shell_commands:
            if isinstance(command, list):
                self.SetBuildPythonCommands(command)
            else:
                self.xml["builders/hudson.plugins.python.Python+/command"] = command

    def SetCron(self, schedule):
        self.xml["triggers/hudson.triggers.TimerTrigger/spec"] = schedule

    def SetDescriptionRegex(self, description_regex):
        description_setter = self.xml[
            "publishers/hudson.plugins.descriptionsetter.DescriptionSetterPublisher"
        ]
        description_setter["regexp"] = description_regex
        description_setter["regexpForFailed"] = description_regex
        description_setter["setForMatrix"] = xmls(False)

    def SetDisplayName(self, display_name):
        self.xml["displayName"] = display_name

    def SetEmailNotification(self, notification_info):
        mailer = self.xml["publishers/hudson.tasks.Mailer"]

        # Handle short mode where user only gives a list of recipients
        if isinstance(notification_info, str):
            notification_info = {"recipients": notification_info}

        mailer["recipients"] = notification_info.pop("recipients")

        notify_every_build = notification_info.pop("notify_every_build", xmls(False))
        if notify_every_build in ["False", "false"]:
            mailer["dontNotifyEveryUnstableBuild"] = xmls(True)
        else:
            mailer["dontNotifyEveryUnstableBuild"] = xmls(False)
        mailer["sendToIndividuals"] = xmls(
            notification_info.pop("notify_individuals", xmls(False))
        )

        self._CheckUnknownOptions("email_notification", notification_info)

    def SetGit(self, git_options, git_xml=None):
        """
        Sets git options

        :param dict git_options:
            Options that will be set in git

        :param None|xml_factory._xml_factory.XmlFactory git_xml:
            Target XmlFactory object to set options.
            If None, will use the main project's Xml (`self.git`)
        """
        if git_xml is None:
            git_xml = self.git

        git_xml["configVersion"] = "2"

        def _Set(option, xml_path, default=None):
            value = git_options.pop(option, default)
            if value is not None:
                for xml_path in AsList(xml_path):
                    git_xml[xml_path] = value

        # Git branch option is set in many places
        branch_paths = [
            "branches/hudson.plugins.git.BranchSpec/name",  # Branch being built
            "extensions/hudson.plugins.git.extensions.impl.LocalBranch/localBranch",  # Checkout to local branch (GitPlugin 2.0+)
            "localBranch",  # Checkout to local branch (GitPlugin 1.5)
        ]

        # Set all options --------------------------------------------------------------------------
        # Try to obtain a default target_dir based on repository name
        if "url" in git_options:
            from jobs_done10.repository import Repository

            repository = Repository(url=git_options["url"])
            _Set("target_dir", "relativeTargetDir", default=repository.name)
        else:
            _Set("target_dir", "relativeTargetDir")

        _Set("remote", "userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/name")
        _Set("refspec", "userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/refspec")
        _Set("url", "userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url")
        _Set("branch", branch_paths)
        _Set(
            "recursive_submodules",
            "extensions/hudson.plugins.git.extensions.impl.SubmoduleOption/recursiveSubmodules",
        )
        _Set(
            "shallow_clone",
            "extensions/hudson.plugins.git.extensions.impl.CloneOption/shallow",
        )
        tags = git_options.pop("tags", "false")
        git_xml["extensions/hudson.plugins.git.extensions.impl.CloneOption/noTags"] = (
            "false" if tags == "true" else "true"
        )
        _Set(
            "reference",
            "extensions/hudson.plugins.git.extensions.impl.CloneOption/reference",
        )
        _Set(
            "timeout",
            "extensions/hudson.plugins.git.extensions.impl.CloneOption/timeout",
        )

        # just accessing attribute tag in the xml object will create a tag without text
        bool_options = [
            (
                "clean_checkout",
                "extensions/hudson.plugins.git.extensions.impl.CleanCheckout",
                "true",
            ),
            ("lfs", "extensions/hudson.plugins.git.extensions.impl.GitLFSPull", "true"),
        ]
        for option_name, tag_path, default_value in bool_options:
            value = git_options.pop(option_name, default_value)
            if value == "true":
                # noinspection PyStatementEffect
                git_xml[tag_path]

        self._CheckUnknownOptions("git", git_options)

    def SetJunitPatterns(self, junit_patterns):
        self._SetXunit("JUnitType", junit_patterns)

    def SetJsunitPatterns(self, jsunit_patterns):
        self._SetXunit("JSUnitPluginType", jsunit_patterns)

    def SetLabelExpression(self, label_expression):
        self.xml["assignedNode"] = label_expression

    def SetNotifyStash(self, args):
        notifier = self.xml[
            "publishers/org.jenkinsci.plugins.stashNotifier.StashNotifier"
        ]

        if isinstance(args, str):
            # Happens when no parameter is given, we just set the URL and assume that
            # username/password if the default configuration set in Jenkins server
            notifier["stashServerBaseUrl"] = args
        else:  # dict
            notifier["stashServerBaseUrl"] = args.pop("url")
            notifier["stashUserName"] = args.pop("username", "")
            notifier["stashUserPassword"] = args.pop("password", "")

            self._CheckUnknownOptions("notify_stash", args)

    def SetParameters(self, parameters):
        parameters_xml = self.xml[
            "properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions"
        ]
        for i_parameter in parameters:
            for name, j_dict in i_parameter.items():
                if name == "choice":
                    p = parameters_xml["hudson.model.ChoiceParameterDefinition+"]
                    p["choices@class"] = "java.util.Arrays$ArrayList"
                    p["choices/a@class"] = "string-array"
                    for k_choice in j_dict["choices"]:
                        p["choices/a/string+"] = k_choice

                elif name == "string":
                    p = parameters_xml["hudson.model.StringParameterDefinition+"]
                    if j_dict["default"]:
                        p["defaultValue"] = j_dict["default"]

                # Common options
                p["name"] = j_dict["name"]
                p["description"] = j_dict["description"]

    def SetScmPoll(self, schedule):
        self.xml["triggers/hudson.triggers.SCMTrigger/spec"] = schedule

    def SetTimeout(self, timeout):
        timeout_xml = self.xml[
            "buildWrappers/hudson.plugins.build__timeout.BuildTimeoutWrapper"
        ]
        timeout_xml["timeoutMinutes"] = str(timeout)
        timeout_xml["failBuild"] = xmls(True)

    def SetTimeoutNoActivity(self, timeout):
        timeout_xml = self.xml[
            "buildWrappers/hudson.plugins.build__timeout.BuildTimeoutWrapper"
        ]
        timeout_xml[
            "strategy@class"
        ] = "hudson.plugins.build_timeout.impl.NoActivityTimeOutStrategy"
        timeout_xml["strategy/timeoutSecondsString"] = timeout
        timeout_xml[
            "operationList/hudson.plugins.build__timeout.operations.FailOperation"
        ]

    def SetCustomWorkspace(self, custom_workspace):
        self.xml["customWorkspace"] = custom_workspace

    def SetSlack(self, options):
        room = options.get("room", "general")

        properties = self.xml[
            "properties/jenkins.plugins.slack.SlackNotifier_-SlackJobProperty"
        ]
        properties["@plugin"] = "slack@1.2"
        properties["room"] = "#" + room
        properties["startNotification"] = "true"
        properties["notifySuccess"] = "true"
        properties["notifyAborted"] = "true"
        properties["notifyNotBuilt"] = "true"
        properties["notifyUnstable"] = "true"
        properties["notifyFailure"] = "true"
        properties["notifyBackToNormal"] = "true"

        publisher = self.xml["publishers/jenkins.plugins.slack.SlackNotifier"]
        publisher["@plugin"] = "slack@1.2"
        publisher["teamDomain"] = options["team"]
        publisher["authToken"] = options["token"]
        publisher["buildServerUrl"] = options["url"]
        publisher["room"] = "#" + room

    def SetNotification(self, options):
        properties = self.xml[
            "properties/com.tikal.hudson.plugins.notification.HudsonNotificationProperty"
        ]
        properties["@plugin"] = "notification@1.9"
        endpoint = properties[
            "endpoints/com.tikal.hudson.plugins.notification.Endpoint"
        ]
        endpoint["protocol"] = options.get("protocol", "HTTP")
        endpoint["format"] = options.get("format", "JSON")
        endpoint["url"] = options["url"]
        endpoint["event"] = "all"
        endpoint["timeout"] = "30000"
        endpoint["loglines"] = "1"

    def SetConsoleColor(self, option):
        wrapper_xpath = "buildWrappers/hudson.plugins.ansicolor.AnsiColorBuildWrapper"
        ansi_color_wrapper = self.xml[wrapper_xpath]

        option = option.strip()
        if option not in ("", "xterm", "vga", "css", "gnome-terminal"):
            msg = [
                "Received unknown console_color option.",
                "Received %s but expected one of xterm, vga, css, gnome-terminal.",
                "(case sensitive, empty string ins interpreted as xterm)",
            ]
            raise RuntimeError("\n".join(msg))
        if len(option) == 0:
            option = "xterm"

        ansi_color_wrapper["@plugin"] = "ansicolor@0.4.2"
        ansi_color_wrapper["colorMapName"] = option

    def SetTimestamps(self, ignored):
        wrapper_xpath = (
            "buildWrappers/hudson.plugins.timestamper.TimestamperBuildWrapper"
        )
        wrapper = self.xml[wrapper_xpath]
        wrapper["@plugin"] = "timestamper@1.7.4"

    def SetCoverage(self, options):
        report_pattern = options.get("report_pattern")
        if not report_pattern:
            raise ValueError("Report pattern is required by coverage")

        cobertura_publisher = self.xml[
            "publishers/hudson.plugins.cobertura.CoberturaPublisher"
        ]
        cobertura_publisher["@plugin"] = "cobertura@1.9.7"
        # This is a file name pattern that can be used to locate the cobertura xml report files
        # (for example with Maven2 use **/target/site/cobertura/coverage.xml). The path is relative
        # to the module root unless you have configured your SCM with multiple modules, in which
        # case it is relative to the workspace root. Note that the module root is SCM-specific,
        # and may not be the same as the workspace root. Cobertura must be configured to generate
        # XML reports for this plugin to function.
        cobertura_publisher["coberturaReportFile"] = report_pattern
        cobertura_publisher[
            "onlyStable"
        ] = "false"  # Include only stable builds, i.e. exclude unstable and failed ones.
        cobertura_publisher[
            "failUnhealthy"
        ] = "true"  # fail builds if No coverage reports are found.
        cobertura_publisher[
            "failUnstable"
        ] = "true"  # Unhealthy projects will be failed.
        cobertura_publisher[
            "autoUpdateHealth"
        ] = "false"  # Unstable projects will be failed.
        cobertura_publisher[
            "autoUpdateStability"
        ] = "false"  # Auto update threshold for health on successful build.
        cobertura_publisher[
            "autoUpdateStability"
        ] = "false"  # Auto update threshold for stability on successful build.
        cobertura_publisher[
            "zoomCoverageChart"
        ] = "false"  # Zoom the coverage chart and crop area below the minimum and above the maximum coverage of the past reports.
        cobertura_publisher[
            "maxNumberOfBuilds"
        ] = "0"  # Only graph the most recent N builds in the coverage chart, 0 disables the limit.
        cobertura_publisher["sourceEncoding"] = "UTF_8"  # Encoding when showing files.

        def FormatMetricValue(metric):
            # It seems to use more places for precision reasons
            return str(int(metric) * 100000)

        def WriteMetrics(target_name, metrics_options, default):
            metrics = cobertura_publisher["{}".format(target_name)]
            targets = metrics["targets"]
            targets["@class"] = "enum-map"
            targets["@enum-type"] = "hudson.plugins.cobertura.targets.CoverageMetric"
            entry = targets["entry+"]
            entry["hudson.plugins.cobertura.targets.CoverageMetric"] = "METHOD"
            entry["int"] = FormatMetricValue(metrics_options.get("method", default))

            entry = targets["entry+"]
            entry["hudson.plugins.cobertura.targets.CoverageMetric"] = "LINE"
            entry["int"] = FormatMetricValue(metrics_options.get("line", default))

            entry = targets["entry+"]
            entry["hudson.plugins.cobertura.targets.CoverageMetric"] = "CONDITIONAL"
            entry["int"] = FormatMetricValue(
                metrics_options.get("conditional", default)
            )

        healthy_options = options.get("healthy", {})
        WriteMetrics("healthyTarget", healthy_options, default=80)

        unhealthy_options = options.get("unhealthy", {})
        WriteMetrics("unhealthyTarget", unhealthy_options, default=0)

        failing_options = options.get("failing", {})
        WriteMetrics("failingTarget", failing_options, default=0)

    def SetWarnings(self, options):
        known_options = {"console", "file"}
        unknown_options = set(options) - known_options
        if unknown_options != set():
            msg = [
                "Received unknown 'warnings' options: %s." % ", ".join(unknown_options),
                "Expected at least one of these: %s." % ", ".join(known_options),
            ]
            raise ValueError("\n".join(msg))
        if len(options) == 0:
            raise ValueError(
                "Empty 'warnings' options. Expected at least one of these: %s."
                % (", ".join(known_options))
            )

        warnings_xml = self.xml["publishers/hudson.plugins.warnings.WarningsPublisher"]
        warnings_xml["@plugin"] = "warnings@4.59"
        warnings_xml["healthy"]
        warnings_xml["unHealthy"]
        warnings_xml["thresholdLimit"] = "low"
        warnings_xml["pluginName"] = "[WARNINGS]"
        warnings_xml["defaultEncoding"]
        warnings_xml["canRunOnFailed"] = "true"
        warnings_xml["usePreviousBuildAsReference"] = "false"
        warnings_xml["useStableBuildAsReference"] = "false"
        warnings_xml["useDeltaValues"] = "false"

        thresholds_xml = warnings_xml["thresholds"]
        thresholds_xml["@plugin"] = "analysis-core@1.82"
        thresholds_xml["unstableTotalAll"]
        thresholds_xml["unstableTotalHigh"]
        thresholds_xml["unstableTotalNormal"]
        thresholds_xml["unstableTotalLow"]
        thresholds_xml["unstableNewAll"]
        thresholds_xml["unstableNewHigh"]
        thresholds_xml["unstableNewNormal"]
        thresholds_xml["unstableNewLow"]
        thresholds_xml["failedTotalAll"]
        thresholds_xml["failedTotalHigh"]
        thresholds_xml["failedTotalNormal"]
        thresholds_xml["failedTotalLow"]
        thresholds_xml["failedNewAll"]
        thresholds_xml["failedNewHigh"]
        thresholds_xml["failedNewNormal"]
        thresholds_xml["failedNewLow"]

        warnings_xml["shouldDetectModules"] = "false"
        warnings_xml["dontComputeNew"] = "true"
        warnings_xml["doNotResolveRelativePaths"] = "false"
        warnings_xml["includePattern"]
        warnings_xml["excludePattern"]
        warnings_xml["messagesPattern"]

        file_parsers_xml = warnings_xml["parserConfigurations"]
        for parser_options in options.get("file", []):
            parser_xml = file_parsers_xml[
                "hudson.plugins.warnings.ParserConfiguration+"
            ]
            parser_xml["pattern"] = parser_options.get("file_pattern")
            parser_xml["parserName"] = parser_options.get("parser")

        console_parsers_xml = warnings_xml["consoleParsers"]
        for parser_options in options.get("console", []):
            parser_xml = console_parsers_xml["hudson.plugins.warnings.ConsoleParser+"]
            parser_xml["parserName"] = parser_options.get("parser")

    def SetTriggerJobs(self, options):
        condition = options.get("condition", "SUCCESS")
        valid_conditions = ("SUCCESS", "UNSTABLE", "FAILED", "ALWAYS")
        if condition not in valid_conditions:
            msg = "Invalid value for condition: {!r}, expected one of {!r}"
            raise RuntimeError(msg.format(condition, valid_conditions))
        xml_trigger = self.xml[
            "publishers/hudson.plugins.parameterizedtrigger.BuildTrigger"
        ]
        xml_trigger["@plugin"] = "parameterized-trigger@2.33"
        xml_config = xml_trigger[
            "configs/hudson.plugins.parameterizedtrigger.BuildTriggerConfig"
        ]
        parameters = options.get("parameters", [])
        xml_configs = xml_config["configs"]
        if parameters:
            xml_configs[
                "hudson.plugins.parameterizedtrigger.PredefinedBuildParameters/properties"
            ] = " ".join(parameters)
        else:
            xml_configs["@class"] = "empty-list"
        xml_config["projects"] = ", ".join(options["names"])
        xml_config["condition"] = condition

        xml_config["triggerWithNoParameters"] = "true" if not parameters else "false"
        xml_config["triggerFromChildProjects"] = "false"

    # Internal functions ---------------------------------------------------------------------------
    def _SetXunit(self, xunit_type, patterns):
        # Set common xunit patterns
        xunit = self.xml["publishers/xunit"]
        xunit[
            "thresholds/org.jenkinsci.plugins.xunit.threshold.FailedThreshold/unstableThreshold"
        ] = "0"
        xunit[
            "thresholds/org.jenkinsci.plugins.xunit.threshold.FailedThreshold/unstableNewThreshold"
        ] = "0"
        xunit["thresholdMode"] = "1"

        # Set patterns for the given type
        xunit_type_xml = xunit["tools/" + xunit_type]
        xunit_type_xml["pattern"] = ",".join(patterns)
        xunit_type_xml["skipNoTestFiles"] = xmls(True)
        xunit_type_xml["failIfNotNew"] = xmls(False)
        xunit_type_xml["deleteOutputFiles"] = xmls(True)
        xunit_type_xml["stopProcessingIfError"] = xmls(True)

        # Add a cleanup sequence to delete all test results when a build starts
        cleanup = self.xml["buildWrappers/hudson.plugins.ws__cleanup.PreBuildCleanup"]
        for pattern in patterns:
            pattern_tag = cleanup["patterns/hudson.plugins.ws__cleanup.Pattern+"]
            pattern_tag["pattern"] = pattern
            pattern_tag["type"] = "INCLUDE"

    def _CheckUnknownOptions(self, configuration_name, options_dict):
        if len(options_dict) > 0:
            raise RuntimeError(
                "Received unknown %s options: %s"
                % (configuration_name, list(options_dict.keys()))
            )


def _AsXmlString(boolean):
    """
    :param bool boolean:
        True or False

    :return unicode:
        `boolean` representation as a string used by Jenkins XML
    """
    return str(boolean).lower()


xmls = _AsXmlString


class JenkinsJobPublisher(object):
    """
    Publishes `JenkinsJob`s
    """

    # Times to retry on ProxyErrors
    RETRIES = 3

    # Times to sleep (seconds) between each retry
    RETRY_SLEEP = 1

    def __init__(self, repository, jobs):
        """
        :param Repository repository:
            Repository used for these jobs. Used to find other jobs in the same url/branch to be
            updated or deleted.

        :param list(JenkinsJob) jobs:
            List of jobs to be published.
        """
        for job in jobs:
            assert (
                job.repository == repository
            ), +"All published jobs must belong to the given `repository`"

        self.repository = repository
        self.jobs = dict((job.name, job) for job in jobs)

    def PublishToUrl(self, url, username=None, password=None):
        """
        Publishes new jobs, updated existing jobs, and delete jobs that belong to the same
        repository/branch but were not updated.

        :param unicode url:
            Jenkins instance URL where jobs will be uploaded to.

        :param unicode username:
            Jenkins username.

        :param unicode password:
            Jenkins password.

        :return tuple(list(unicode),list(unicode),list(unicode)):
            Tuple with lists of {new, updated, deleted} job names (sorted alphabetically)
        """
        import jenkins

        jenkins_api = jenkins.Jenkins(url, username, password)

        # Get all jobs
        job_names = set(self.jobs.keys())
        matching_jobs = self._GetMatchingJobs(jenkins_api)

        # Find all new/updated/deleted jobs
        new_jobs = job_names.difference(matching_jobs)
        updated_jobs = job_names.intersection(matching_jobs)
        deleted_jobs = matching_jobs.difference(job_names)

        def retry(func, *args, **kwargs):
            from requests.exceptions import HTTPError

            for _ in range(self.RETRIES):
                try:
                    func(*args, **kwargs)
                    break
                except HTTPError as e:
                    http_error = e
                    if http_error.response.status_code in (
                        403,
                        502,
                    ):  # 403 Forbidden, 502 Proxy error
                        # This happens sometimes for no apparent reason, and we want to retry.
                        from time import sleep

                        sleep(self.RETRY_SLEEP)
                    else:
                        raise
            else:
                # If we got here, this mean we ran out of retries. Raise the last error we received.
                raise http_error

        # Process everything
        for job_name in new_jobs:
            retry(jenkins_api.create_job, job_name, self.jobs[job_name].xml)

        for job_name in updated_jobs:
            retry(jenkins_api.reconfig_job, job_name, self.jobs[job_name].xml)

        for job_name in deleted_jobs:
            retry(jenkins_api.delete_job, job_name)

        return list(map(sorted, (new_jobs, updated_jobs, deleted_jobs)))

    def PublishToDirectory(self, output_directory):
        """
        Publishes jobs to a directory. Each job creates a file with its name and xml contents.

        :param unicode output_directory:
             Target directory for outputting job .xmls
        """
        import os

        for job in self.jobs.values():
            with io.open(
                os.path.join(output_directory, job.name), "w", encoding="utf-8"
            ) as f:
                f.write(job.xml)

    def _GetMatchingJobs(self, jenkins_api):
        """
        Filter jobs that belong to the same repository/branch as a `job` being published

        :param jenkins_api:
            Configured Jenkins API that gives access to Jenkins data at a host.

        :return set(unicode):
            Names of all Jenkins jobs that match `job` repository name and branch
        """
        matching_jobs = set()

        common_prefix = self.repository.name + "-" + self.repository.branch
        for jenkins_job in (x["name"] for x in jenkins_api.get_jobs()):
            # Filter jobs that belong to this repository (this would be safer to do reading SCM
            # information, but a lot more expensive
            if not jenkins_job.startswith(common_prefix):
                continue

            jenkins_job_branch = self._GetJenkinsJobBranch(jenkins_api, jenkins_job)
            if jenkins_job_branch == self.repository.branch:
                matching_jobs.add(jenkins_job)

        return matching_jobs

    def _GetJenkinsJobBranch(self, jenkins_api, jenkins_job):
        """
        :param jenkins.Jenkins jenkins_api:
            Configured Jenkins API that gives access to Jenkins data at a host.

        :param unicode jenkins_job:
            Name of a job in jenkins

        :return unicode:
            Name of `jenkins_job`s branch

        .. note::
            This function was separated to make use of Memoize cacheing, avoiding multiple queries
            to the same jenkins job config.xml
        """
        from xml.etree import ElementTree

        # Read config to see if this job is in the same branch
        config = jenkins_api.get_job_config(jenkins_job)

        # We should be able to get this information from jenkins API, but it seems that git
        # plugin for Jenkins has a bug that prevents its data from being shown in the API
        # https://issues.jenkins-ci.org/browse/JENKINS-14588
        root = ElementTree.fromstring(config)

        # Try for single SCM
        name_element = root.find("scm/branches/hudson.plugins.git.BranchSpec/name")
        if name_element is not None:
            return name_element.text.strip()

        # If the above was not found, we might be dealing with multiple repositories
        scms = root.findall("scm/scms/hudson.plugins.git.GitSCM")

        checked_urls = []

        # Account for case-differences
        repo_lower = self.repository.url.lower()
        repo_urls = [repo_lower]

        # Account for the fact that ssh://example.com/repo and ssh://example.com/repo.git
        # refer to the same repo
        if not repo_lower.endswith(".git"):
            repo_urls.append(repo_lower + ".git")

        # Process them all until we find the SCM for the correct repository
        for scm in scms:
            url = scm.find(
                "userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url"
            ).text.strip()
            checked_urls.append(url)

            urls = [url.lower()]
            # Same as above (account for urls ending with '.git')
            if not url.endswith(".git"):
                urls.append(url.lower() + ".git")

            if any(url in repo_urls for url in urls):
                return scm.find(
                    "branches/hudson.plugins.git.BranchSpec/name"
                ).text.strip()

        error_msg = [
            'Could not find SCM for repository "%s" in job "%s"'
            % (self.repository.url, jenkins_job),
            'The local repository origin is set to "%s".' % (self.repository.url,),
            "And the possible matches are:",
        ]
        error_msg.extend([" - %s" % (url,) for url in checked_urls])
        error_msg.extend(
            [
                "",
                'If needed a repository origin url can be set with "git remote set-url origin <URL>".',
            ]
        )
        raise RuntimeError("\n".join(error_msg))


def UploadJobsFromFile(
    repository, jobs_done_file_contents, url, username=None, password=None
):
    """
    :param repository:
        .. seealso:: GetJobsFromFile

    :param jobs_done_file_contents:
        .. seealso:: GetJobsFromFile

    :param unicode url:
        URL of a Jenkins sevrer instance where jobs will be uploaded

    :param unicode|None username:
        Username for Jenkins server.

    :param unicode|None password:
        Password for Jenkins server.

    :returns:
        .. seealso:: JenkinsJobPublisher.PublishToUrl

    """
    jobs = GetJobsFromFile(repository, jobs_done_file_contents)
    publisher = JenkinsJobPublisher(repository, jobs)

    return publisher.PublishToUrl(url, username, password)


def GetJobsFromDirectory(directory="."):
    """
    Looks in a directory for a jobs_done file and git repository information to create jobs.

    :param directory:
        Directory where we'll extract information to generate `JenkinsJob`s

    :return tuple(Repository,set(JenkinsJob))
        Repository information for the given directory, and jobs obtained from this directory.

        .. seealso:: GetJobsFromFile
    """
    from jobs_done10.jobs_done_job import JOBS_DONE_FILENAME
    from jobs_done10.repository import Repository
    import os

    from subprocess import check_output

    url = (
        check_output(
            "git config --local --get remote.origin.url", shell=True, cwd=directory
        )
        .strip()
        .decode("UTF-8")
    )
    branches = (
        check_output("git branch", shell=True, cwd=directory).strip().decode("UTF-8")
    )
    for branch in branches.splitlines():
        branch = branch.strip()
        if "*" in branch:  # Current branch
            branch = branch.split(" ", 1)[1]
            break
    else:
        raise RuntimeError("Error parsing output from git branch")

    repository = Repository(url=url, branch=branch)
    try:
        with io.open(
            os.path.join(directory, JOBS_DONE_FILENAME), encoding="utf-8"
        ) as f:
            jobs_done_file_contents = f.read()
    except IOError:
        jobs_done_file_contents = None

    return repository, GetJobsFromFile(repository, jobs_done_file_contents)


def GetJobsFromFile(repository, jobs_done_file_contents):
    """
    Creates jobs from repository information and a jobs_done file.

    :param Repository repository:
        .. seealso:: Repository

    :param unicode|None jobs_done_file_contents:
        .. seealso:: JobsDoneJob.CreateFromYAML

    :return set(JenkinsJob)
    """
    from jobs_done10.job_generator import JobGeneratorConfigurator
    from jobs_done10.jobs_done_job import JobsDoneJob

    jenkins_generator = JenkinsXmlJobGenerator()

    jobs = []
    jobs_done_jobs = JobsDoneJob.CreateFromYAML(jobs_done_file_contents, repository)
    for jobs_done_job in jobs_done_jobs:
        JobGeneratorConfigurator.Configure(jenkins_generator, jobs_done_job)
        jobs.append(jenkins_generator.GetJob())

    return jobs
