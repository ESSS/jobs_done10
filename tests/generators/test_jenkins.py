import os
from subprocess import check_call
from textwrap import dedent
from typing import Tuple
from typing import Union

import jenkins
import pytest

from jobs_done10.generators.jenkins import GetJobsFromDirectory
from jobs_done10.generators.jenkins import GetJobsFromFile
from jobs_done10.generators.jenkins import JenkinsJob
from jobs_done10.generators.jenkins import JenkinsJobPublisher
from jobs_done10.generators.jenkins import JenkinsXmlJobGenerator
from jobs_done10.generators.jenkins import UploadJobsFromFile
from jobs_done10.job_generator import JobGeneratorConfigurator
from jobs_done10.jobs_done_job import JOBS_DONE_FILENAME
from jobs_done10.jobs_done_job import JobsDoneFileTypeError
from jobs_done10.jobs_done_job import JobsDoneJob
from jobs_done10.repository import Repository


class TestJenkinsXmlJobGenerator:

    # ===============================================================================================
    # Tests
    # ===============================================================================================
    def testEmpty(self):
        with pytest.raises(ValueError) as e:
            self._GenerateJob(yaml_contents="")
        assert str(e.value) == "Could not parse anything from .yaml contents"

    def testChoiceParameters(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=(
                """\
                parameters:
                  - choice:
                      name: "PARAM"
                      choices:
                      - "choice_1"
                      - "choice_2"
                      description: "Description"
                """
            ),
            boundary_tags="properties",
        )

    def testMultipleChoiceParameters(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=(
                """
                parameters:
                  - choice:
                      name: "PARAM"
                      choices:
                      - "choice_1"
                      - "choice_2"
                      description: "Description"
                  - choice:
                      name: "PARAM_2"
                      choices:
                      - "choice_1"
                      - "choice_2"
                      description: "Description"
                """
            ),
            boundary_tags="properties",
        )

    def testStringParameters(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=(
                """
                parameters:
                  - string:
                      name: "PARAM_VERSION"
                      default: "Default"
                      description: "Description"
                """
            ),
            boundary_tags="properties",
        )

    def testMultipleStringParameters(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=(
                """
                parameters:
                  - string:
                      name: "PARAM_VERSION"
                      default: "Default"
                      description: "Description"
                  - string:
                      name: "PARAM_VERSION_2"
                      default: "Default"
                      description: "Description"
                """
            ),
            boundary_tags="properties",
        )

    def testParametersMaintainOrder(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=(
                """
                parameters:
                  - choice:
                      name: "PARAM"
                      choices:
                      - "choice_1"
                      - "choice_2"
                      description: "Description"
                  - string:
                      name: "PARAM_VERSION"
                      default: "Default"
                      description: "Description"
                """
            ),
            boundary_tags="properties",
        )

    def testJUnitPatterns(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                junit_patterns:
                - "junit*.xml"
                - "others.xml"
                """
            ),
            boundary_tags=("publishers", "buildWrappers"),
        )

    def testTimeoutAbsolute(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                timeout: 60
                """
            ),
            boundary_tags="buildWrappers",
        )

    def testTimeoutNoActivity(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                timeout_no_activity: 600
                """
            ),
            boundary_tags="buildWrappers",
        )

    def testCustomWorkspace(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                custom_workspace: workspace/WS
                """
            ),
            boundary_tags="project",
        ),

    def testAuthToken(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                auth_token: my_token
                """
            ),
            boundary_tags="project",
        )

    def testBoosttestPatterns(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                boosttest_patterns:
                - "boost*.xml"
                """
            ),
            boundary_tags=("publishers", "buildWrappers"),
        )

    def testJSUnitPatterns(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                jsunit_patterns:
                - "jsunit*.xml"
                """
            ),
            boundary_tags=("publishers", "buildWrappers"),
        )

    def testMultipleTestResults(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=(
                """
                junit_patterns:
                - "junit*.xml"

                boosttest_patterns:
                - "boosttest*.xml"
                """
            ),
            boundary_tags=("publishers", "buildWrappers"),
        )

    @pytest.mark.parametrize(
        "job_done_key, xml_key",
        [
            ("build_batch_commands", "hudson.tasks.BatchFile"),
            ("build_shell_commands", "hudson.tasks.Shell"),
            ("build_python_commands", "hudson.plugins.python.Python"),
        ],
    )
    def testBuildCommandsExpandNestedLists(
        self, file_regression, job_done_key, xml_key
    ):

        # sanity: no ref
        self.Check(
            file_regression,
            yaml_contents=dedent(
                f"""
                branch-foo:{job_done_key}:
                - someone else command
                {job_done_key}:
                - my_command
                """
            ),
            boundary_tags="builders",
            basename=f"testBuildCommandsExpandNestedLists-noref-{xml_key}",
        )

        # expand refs (after)
        self.Check(
            file_regression,
            yaml_contents=dedent(
                f"""
                branch-foo:{job_done_key}: &ref_a
                - someone else command
                {job_done_key}:
                - my_command
                - *ref_a
                """
            ),
            boundary_tags="builders",
            basename=f"testBuildCommandsExpandNestedLists-expand-refs-after-{xml_key}",
        )

        # expand refs (before)
        self.Check(
            file_regression,
            yaml_contents=dedent(
                f"""
                branch-foo:{job_done_key}: &ref_a
                - someone else command
                {job_done_key}:
                - *ref_a
                - my_command
                """
            ),
            boundary_tags="builders",
            basename=f"testBuildCommandsExpandNestedLists-expand-refs-before-{xml_key}",
        )

    def testBuildBatchCommand(self, file_regression):
        # works with a single command
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                build_batch_commands:
                - my_command
                """
            ),
            boundary_tags="builders",
            basename="testBuildBatchCommand-single",
        )

        # Works with multi line commands
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                build_batch_commands:
                - |
                  multi_line
                  command
                """
            ),
            boundary_tags="builders",
            basename="testBuildBatchCommand-multi",
        )

        # Works with multiple commands
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                build_batch_commands:
                - command_1
                - command_2
                """
            ),
            boundary_tags="builders",
            basename="testBuildBatchCommand-multi-commands",
        )

    def testBuildPythonCommand(self, file_regression):
        # works with a single command
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                build_python_commands:
                - print 'hello'
                """
            ),
            boundary_tags="builders",
        )

    def testBuildShellCommand(self, file_regression):
        # works with a single command
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                build_shell_commands:
                - my_command
                """
            ),
            boundary_tags="builders",
            basename="testBuildShellCommand-single",
        )

        # Works with multi line commands
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                build_shell_commands:
                - |
                  multi_line
                  command
                """
            ),
            boundary_tags="builders",
            basename="testBuildShellCommand-multi",
        )

        # Works with multiple commands
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                build_shell_commands:
                - command_1
                - command_2
                """
            ),
            boundary_tags="builders",
            basename="testBuildShellCommand-multi-commands",
        )

    def testDescriptionRegex(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                r"""
                description_regex: "JENKINS DESCRIPTION\\: (.*)"
                """
            ),
            boundary_tags="publishers",
        )

    def testNotifyStash(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                r"""
                notify_stash:
                  url: stash.com
                  username: user
                  password: pass
                """
            ),
            boundary_tags="publishers",
        )

    def testNotifyStashServerDefault(self, file_regression):
        """
        When given no parameters, use the default Stash configurations set in the Jenkins server
        """
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                notify_stash: stash.com
                """
            ),
            boundary_tags="publishers",
        )

    def testNotifyStashWithTests(self, file_regression):
        """
        When we have both notify_stash, and some test pattern, we have to make sure that the output
        jenkins job xml places the notify_stash publisher AFTER the test publisher, otherwise builds
        with failed tests might be reported as successful to Stash
        """
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                notify_stash:
                  url: stash.com
                  username: user
                  password: pass

                jsunit_patterns:
                - "jsunit*.xml"
                """
            ),
            boundary_tags=("publishers", "buildWrappers"),
        )

    def testMatrix(self, file_regression):
        yaml_contents = dedent(
            """
            planet-earth:build_shell_commands:
            - earth_command

            planet-mars:build_shell_commands:
            - mars_command

            matrix:
                planet:
                - earth
                - mars

                moon:
                - europa
            """
        )
        repository = Repository(url="http://fake.git", branch="not_master")

        # This test should create two jobs based on the given matrix
        jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository)

        job_generator = JenkinsXmlJobGenerator()

        for jd_file in jobs_done_jobs:
            JobGeneratorConfigurator.Configure(job_generator, jd_file)
            jenkins_job = job_generator.GetJob()

            planet = jd_file.matrix_row["planet"]

            # Matrix affects the jobs name, but single value rows are left out
            assert jenkins_job.name == f"fake-not_master-{planet}"
            file_regression.check(
                jenkins_job.xml, extension=".xml", basename=f"testMatrix-{planet}"
            )

    def testMatrixSingleValueOnly(self, file_regression):
        yaml_contents = dedent(
            """
            matrix:
                planet:
                - earth

                moon:
                - europa
            """
        )
        repository = Repository(url="http://fake.git", branch="not_master")

        # This test should create two jobs based on the given matrix
        jd_file = JobsDoneJob.CreateFromYAML(yaml_contents, repository)[0]
        job_generator = JenkinsXmlJobGenerator()

        JobGeneratorConfigurator.Configure(job_generator, jd_file)
        jenkins_job = job_generator.GetJob()

        # Matrix usually affects the jobs name, but single value rows are left out
        assert jenkins_job.name == "fake-not_master"

        # XML should have no diff too, because single values do not affect label_expression
        new_content = self.ExtractTagBoundaries(jenkins_job.xml, "project")
        file_regression.check(new_content, extension=".xml")

    def testDisplayName(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                display_name: "{name}-{branch}"
                """
            ),
            boundary_tags="project",
        )

    def testLabelExpression(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                label_expression: "win32&&dist-12.0"
                """
            ),
            boundary_tags="project",
        )

    def testCron(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                cron: |
                       # Everyday at 22 pm
                       0 22 * * *
                """
            ),
            boundary_tags="triggers",
        )

    def testSCMPoll(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                scm_poll: |
                       # Everyday at 22 pm
                       0 22 * * *
                """
            ),
            boundary_tags="triggers",
        )

    def testAdditionalRepositories(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                additional_repositories:
                - git:
                    url: http://some_url.git
                    branch: my_branch
                """
            ),
            boundary_tags="scm",
        )

    def testGitAndAdditionalRepositories(self, file_regression):
        """
        Make sure that everything works just fine when we mix 'git' and 'additional_repositories'
        """
        # Test git -> additional
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                git:
                  branch: custom_main

                additional_repositories:
                - git:
                    url: http://additional.git
                    branch: custom_additional
                """
            ),
            boundary_tags="scm",
        )

        # Test additional -> git
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                additional_repositories:
                - git:
                    url: http://additional.git
                    branch: custom_additional

                git:
                  branch: custom_main
                """
            ),
            boundary_tags="scm",
        )

    def testUnknownGitOptions(self):
        with pytest.raises(RuntimeError) as e:
            self._GenerateJob(
                yaml_contents=dedent(
                    """
                    git:
                      unknown: ""
                    """
                ),
            )
        assert str(e.value) == "Received unknown git options: ['unknown']"

    def testGitOptions(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                git:
                  recursive_submodules: true
                  reference: "/home/reference.git"
                  target_dir: "main_application"
                  timeout: 30
                  clean_checkout: false
                  tags: true
                """
            ),
            boundary_tags="scm",
        )

    def testEmailNotificationDict(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                email_notification:
                  recipients: user@company.com other@company.com
                  notify_every_build: true
                  notify_individuals: true

                """
            ),
            boundary_tags="publishers",
        )

    def testEmailNotificationString(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                email_notification: user@company.com other@company.com
                """
            ),
            boundary_tags="publishers",
        )

    def testEmailNotificationWithTests(self, file_regression):
        """
        When we have both email_notification, and some test pattern, we have to make sure that the
        output jenkins job xml places the email_notification publisher AFTER the test publisher,
        otherwise builds with failed tests might be reported as successful via email
        """
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                email_notification:
                  recipients: user@company.com other@company.com
                  notify_every_build: true
                  notify_individuals: true

                jsunit_patterns:
                - "jsunit*.xml"
                """
            ),
            boundary_tags=("publishers", "buildWrappers"),
        )

    def testNotification(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                notification:
                  protocol: ALPHA
                  format: BRAVO
                  url: https://bravo
                """
            ),
            boundary_tags="properties",
        )

    def testSlack(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                slack:
                  team: esss
                  room: zulu
                  token: ALPHA
                  url: https://bravo
                """
            ),
            boundary_tags=("properties", "publishers"),
        )

    @pytest.mark.parametrize(
        "conf_value, expected_name",
        [
            ("", "xterm"),
            ("xterm", "xterm"),
            ("vga", "vga"),
        ],
    )
    def testAnsiColor(self, conf_value, expected_name, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                f"""
                console_color: {conf_value}
                """
            ),
            boundary_tags="buildWrappers",
            basename=f"testAnsiColor-{conf_value}-{expected_name}",
        )

    def testTimestamps(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                timestamps:
                """
            ),
            boundary_tags="buildWrappers",
        )

    @pytest.mark.parametrize("condition", ("SUCCESS", "UNSTABLE", "FAILED", "ALWAYS"))
    def testTriggerJobNoParameters(self, condition, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                f"""
                trigger_jobs:
                  names:
                    - etk-master-linux64-27
                    - etk-master-linux64-36
                  condition: {condition}
                """
            ),
            boundary_tags="publishers",
            basename=f"testTriggerJobNoParameters-{condition}",
        )

    def testTriggerJobInvalidCondition(self):
        with pytest.raises(
            RuntimeError,
            match=r"Invalid value for condition: u?'UNKNOWN', expected one of .*",
        ):
            self._GenerateJob(
                yaml_contents=dedent(
                    """
                    trigger_jobs:
                      names:
                        - etk-master-linux64-27
                        - etk-master-linux64-36
                      condition: UNKNOWN
                    """
                ),
            )

    def testTriggerJobParameters(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                trigger_jobs:
                  names:
                    - etk-master-linux64-27
                    - etk-master-linux64-36
                  parameters:
                    - KEY1=VALUE1
                    - KEY2=VALUE2
                """
            ),
            boundary_tags="publishers",
        )

    def testAnsiColorUnknowOption(self):
        with pytest.raises(
            RuntimeError, match="Received unknown console_color option."
        ):
            self._GenerateJob(
                yaml_contents=dedent(
                    """
                    console_color: unknown-value
                    """
                ),
            )

    @pytest.mark.parametrize(
        "scenario",
        [
            "complete",
            "incomplete_metrics",
            "incomplete_values",
        ],
    )
    def testCoverage(self, scenario, file_regression):
        if scenario == "complete":
            healthy_method = 100
            healthy_line = 100
            healthy_conditional = 90

            unhealthy_method = 70
            unhealthy_line = 70
            unhealthy_conditional = 60

            failing_method = 60
            failing_line = 60
            failing_conditional = 50
            contents = dedent(
                rf"""
                coverage:
                  report_pattern: "**/build/coverage/*.xml"
                  healthy:
                    method: {healthy_method}
                    line: {healthy_line}
                    conditional: {healthy_conditional}
                  unhealthy:
                    method: {unhealthy_method}
                    line: {unhealthy_line}
                    conditional: {unhealthy_conditional}
                  failing:
                    method: {failing_method}
                    line: {failing_line}
                    conditional: {failing_conditional}
                """
            )
        elif scenario == "incomplete_metrics":
            healthy_method = 100
            healthy_line = 100
            healthy_conditional = 90

            contents = dedent(
                rf"""
                coverage:
                  report_pattern: "**/build/coverage/*.xml"
                  healthy:
                    method: {healthy_method}
                    line: {healthy_line}
                    conditional: {healthy_conditional}
                """
            )
        else:
            assert scenario == "incomplete_values", "Unknown scenario"
            healthy_method = 100
            healthy_line = 100

            contents = dedent(
                rf"""
                coverage:
                  report_pattern: "**/build/coverage/*.xml"
                  healthy:
                    method: {healthy_method}
                    line: {healthy_line}
                """
            )

        self.Check(
            file_regression,
            contents,
            boundary_tags="publishers",
            basename=f"testCoverage-{scenario}",
        )

    def testCoverageFailWhenMissingReportPattern(self):
        with pytest.raises(
            ValueError, match="Report pattern is required by coverage"
        ) as e:
            self._GenerateJob(
                yaml_contents=dedent(
                    r"""
                coverage:
                  healthy:
                    method: 100
                    line: 100
                """
                )
            )

    def testWarnings(self, file_regression):
        self.Check(
            file_regression,
            yaml_contents=dedent(
                """
                warnings:
                  console:
                    - parser: Clang (LLVM based)
                    - parser: PyLint
                  file:
                    - parser: CppLint
                      file_pattern: "*.cpplint"
                    - parser: CodeAnalysis
                      file_pattern: "*.codeanalysis"
                """
            ),
            boundary_tags="publishers",
        )

    def testWarningsEmpty(self):
        with pytest.raises(JobsDoneFileTypeError):
            self._GenerateJob(yaml_contents="warnings:")
        with pytest.raises(ValueError, match="Empty 'warnings' options.*"):
            self._GenerateJob(yaml_contents="warnings: {}")

    def testWarningsWrongOption(self):
        with pytest.raises(
            ValueError, match="Received unknown 'warnings' options: zucchini."
        ):
            self._GenerateJob(
                yaml_contents=dedent(
                    """\
                warnings:
                  zucchini:
                    - parser: Pizza
                  file:
                    - parser: CppLint
                      file_pattern: "*.cpplint"
                """
                )
            )

    def _GenerateJob(self, yaml_contents):
        repository = Repository(url="http://fake.git", branch="not_master")
        jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository)

        job_generator = JenkinsXmlJobGenerator()
        JobGeneratorConfigurator.Configure(job_generator, jobs_done_jobs[0])
        return job_generator.GetJob()

    def Check(self, file_regression, yaml_contents, boundary_tags, *, basename=None):
        """
        Given the yaml contents of a jobs done file, generate the corresponding XML, extracting
        the text between the tag(s) given, and use file_regression to compare it.
        """
        __tracebackhide__ = True
        jenkins_job = self._GenerateJob(yaml_contents=dedent(yaml_contents))
        new_content = self.ExtractTagBoundaries(jenkins_job.xml, boundary_tags)
        file_regression.check(new_content, extension=".xml", basename=basename)

    def ExtractTagBoundaries(
        self, text: str, boundary_tags: Union[str, Tuple[str, ...]]
    ) -> str:
        """Given a XML text, extract the lines containing between the given tags (including them)."""
        if isinstance(boundary_tags, str):
            boundary_tags = (boundary_tags,)
        lines = text.splitlines(True)
        new_lines = []
        for tag in boundary_tags:
            start = None
            end = None
            for index, line in enumerate(lines):
                line = line.strip()
                if line == f"<{tag}>" or line.startswith(f"<{tag} "):
                    start = index
                elif line == f"</{tag}>":
                    end = index
                    break
            assert start is not None
            assert end is not None
            new_lines += lines[start : end + 1]
        return dedent("".join(new_lines))


class TestJenkinsActions(object):
    """
    Integration tests for Jenkins actions
    """

    _JOBS_DONE_FILE_CONTENTS = dedent(
        """
        junit_patterns:
        - "junit*.xml"

        boosttest_patterns:
        - "cpptest*.xml"

        parameters:
          - choice:
              name: "PARAM"
              choices:
              - "choice_1"
              - "choice_2"
              description: "Description"

        build_batch_commands:
        - "command"

        matrix:
            planet:
            - mercury
            - venus
            - jupiter

        """
    )

    _REPOSITORY = Repository(url="http://space.git", branch="branch")

    def testGetJobsFromFile(self):
        jobs = GetJobsFromFile(self._REPOSITORY, self._JOBS_DONE_FILE_CONTENTS)
        assert len(jobs) == 3

    def testGetJobsFromDirectory(self, tmpdir):
        repo_path = tmpdir / "git_repository"
        repo_path.mkdir()

        # Prepare git repository
        with repo_path.as_cwd():
            check_call("git init", shell=True)
            check_call("git config user.name Bob", shell=True)
            check_call("git config user.email bob@example.com", shell=True)
            check_call("git remote add origin %s" % self._REPOSITORY.url, shell=True)
            check_call("git checkout -b %s" % self._REPOSITORY.branch, shell=True)
            repo_path.join(".gitignore").write("")
            check_call("git add .", shell=True)
            check_call('git commit -a -m "First commit"', shell=True)

            # If there is no jobs_done file, we should get zero jobs
            _repository, jobs = GetJobsFromDirectory(str(repo_path))
            assert len(jobs) == 0

            # Create jobs_done file
            repo_path.join(JOBS_DONE_FILENAME).write(self._JOBS_DONE_FILE_CONTENTS)
            check_call("git add .", shell=True)
            check_call('git commit -a -m "Added jobs_done file"', shell=True)

            _repository, jobs = GetJobsFromDirectory(str(repo_path))
            assert len(jobs) == 3

    def testUploadJobsFromFile(self, monkeypatch):
        """
        Tests that UploadJobsFromFile correctly calls JenkinsJobPublisher (already tested elsewhere)
        """

        def MockPublishToUrl(self, url, username, password):
            assert url == "jenkins_url"
            assert username == "jenkins_user"
            assert password == "jenkins_pass"

            assert set(self.jobs.keys()) == {
                "space-branch-venus",
                "space-branch-jupiter",
                "space-branch-mercury",
            }

            return "mock publish result"

        monkeypatch.setattr(JenkinsJobPublisher, "PublishToUrl", MockPublishToUrl)

        result = UploadJobsFromFile(
            repository=self._REPOSITORY,
            jobs_done_file_contents=self._JOBS_DONE_FILE_CONTENTS,
            url="jenkins_url",
            username="jenkins_user",
            password="jenkins_pass",
        )
        assert result == "mock publish result"


class TestJenkinsPublisher(object):
    def testPublishToDirectory(self, tmpdir):
        self._GetPublisher().PublishToDirectory(str(tmpdir))

        assert set(os.path.basename(str(x)) for x in tmpdir.listdir()) == {
            "space-milky_way-jupiter",
            "space-milky_way-mercury",
            "space-milky_way-venus",
        }

        assert tmpdir.join("space-milky_way-jupiter").read() == "jupiter"
        assert tmpdir.join("space-milky_way-mercury").read() == "mercury"
        assert tmpdir.join("space-milky_way-venus").read() == "venus"

    def testPublishToUrl(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        new_jobs, updated_jobs, deleted_jobs = self._GetPublisher().PublishToUrl(
            url="jenkins_url",
            username="jenkins_user",
            password="jenkins_pass",
        )
        assert (
            set(new_jobs)
            == mock_jenkins.NEW_JOBS
            == {"space-milky_way-venus", "space-milky_way-jupiter"}
        )
        assert (
            set(updated_jobs)
            == mock_jenkins.UPDATED_JOBS
            == {"space-milky_way-mercury"}
        )
        assert (
            set(deleted_jobs) == mock_jenkins.DELETED_JOBS == {"space-milky_way-saturn"}
        )

    def testPublishToUrlProxyErrorOnce(self, monkeypatch):
        # Do not actually sleep during tests
        monkeypatch.setattr(JenkinsJobPublisher, "RETRY_SLEEP", 0)

        # Tell mock jenkins to raise a proxy error, our retry should catch it and continue
        mock_jenkins = self._MockJenkinsAPI(monkeypatch, proxy_errors=1)
        new_jobs, updated_jobs, deleted_jobs = self._GetPublisher().PublishToUrl(
            url="jenkins_url",
            username="jenkins_user",
            password="jenkins_pass",
        )
        assert (
            set(new_jobs)
            == mock_jenkins.NEW_JOBS
            == {"space-milky_way-venus", "space-milky_way-jupiter"}
        )
        assert (
            set(updated_jobs)
            == mock_jenkins.UPDATED_JOBS
            == {"space-milky_way-mercury"}
        )
        assert (
            set(deleted_jobs) == mock_jenkins.DELETED_JOBS == {"space-milky_way-saturn"}
        )

    def testPublishToUrlProxyErrorTooManyTimes(self, monkeypatch):
        # Do not actually sleep during tests
        monkeypatch.setattr(JenkinsJobPublisher, "RETRY_SLEEP", 0)
        monkeypatch.setattr(JenkinsJobPublisher, "RETRIES", 3)

        # Tell mock jenkins to raise 5 proxy errors in a row, this should bust our retry limit
        self._MockJenkinsAPI(monkeypatch, proxy_errors=5)

        from requests.exceptions import HTTPError

        with pytest.raises(HTTPError):
            self._GetPublisher().PublishToUrl(
                url="jenkins_url",
                username="jenkins_user",
                password="jenkins_pass",
            )

    def testPublishToUrl2(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        publisher = self._GetPublisher()
        publisher.jobs = {}

        new_jobs, updated_jobs, deleted_jobs = publisher.PublishToUrl(
            url="jenkins_url",
            username="jenkins_user",
            password="jenkins_pass",
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == set()
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == set()
        assert (
            set(deleted_jobs)
            == mock_jenkins.DELETED_JOBS
            == {"space-milky_way-mercury", "space-milky_way-saturn"}
        )

    def _GetPublisher(self):
        repository = Repository(url="http://server/space.git", branch="milky_way")
        jobs = [
            JenkinsJob(
                name="space-milky_way-jupiter", xml="jupiter", repository=repository
            ),
            JenkinsJob(
                name="space-milky_way-mercury", xml="mercury", repository=repository
            ),
            JenkinsJob(
                name="space-milky_way-venus", xml="venus", repository=repository
            ),
        ]

        return JenkinsJobPublisher(repository, jobs)

    def _MockJenkinsAPI(self, monkeypatch, proxy_errors=0):
        class MockJenkins(object):
            NEW_JOBS = set()
            UPDATED_JOBS = set()
            DELETED_JOBS = set()

            def __init__(self, url, username, password):
                assert url == "jenkins_url"
                assert username == "jenkins_user"
                assert password == "jenkins_pass"
                self.proxy_errors_raised = 0

            def get_jobs(self):
                return [
                    {"name": "space-milky_way-mercury"},
                    {"name": "space-milky_way-saturn"},
                ]

            def get_job_config(self, job_name):
                # Test with single, and multiple scms
                if job_name == "space-milky_way-mercury":
                    return dedent(
                        """
                        <project>
                          <scm>
                            <userRemoteConfigs>
                              <hudson.plugins.git.UserRemoteConfig>
                                <url>
                                  http://server/space.git
                                </url>
                              </hudson.plugins.git.UserRemoteConfig>
                            </userRemoteConfigs>
                            <branches>
                              <hudson.plugins.git.BranchSpec>
                                <name>milky_way</name>
                              </hudson.plugins.git.BranchSpec>
                            </branches>
                          </scm>
                        </project>
                        """
                    )
                elif job_name == "space-milky_way-saturn":
                    return dedent(
                        """
                        <project>
                          <scm>
                            <scms>
                              <!-- One of the SCMs is the one for space -->
                              <hudson.plugins.git.GitSCM>
                                <userRemoteConfigs>
                                  <hudson.plugins.git.UserRemoteConfig>
                                    <url>
                                      <!-- An uppercase url without .git extension to test resilience -->
                                      http://SERVER/space
                                    </url>
                                  </hudson.plugins.git.UserRemoteConfig>
                                </userRemoteConfigs>
                                <branches>
                                  <hudson.plugins.git.BranchSpec>
                                    <name>milky_way</name>
                                  </hudson.plugins.git.BranchSpec>
                                </branches>
                              </hudson.plugins.git.GitSCM>

                              <!-- But a job might have multiple SCMs, we don't care about those -->
                              <hudson.plugins.git.GitSCM>
                                <userRemoteConfigs>
                                  <hudson.plugins.git.UserRemoteConfig>
                                    <url>
                                      http://server/space_dependencie.git
                                    </url>
                                  </hudson.plugins.git.UserRemoteConfig>
                                </userRemoteConfigs>
                                <branches>
                                  <hudson.plugins.git.BranchSpec>
                                    <name>other_branch</name>
                                  </hudson.plugins.git.BranchSpec>
                                </branches>
                              </hudson.plugins.git.GitSCM>
                            </scms>
                          </scm>
                        </project>
                        """
                    )
                else:
                    assert 0, f"unknown job name: {job_name}"

            def create_job(self, name, xml):
                assert type(xml) is str
                self.NEW_JOBS.add(name)

            def reconfig_job(self, name, xml):
                self.UPDATED_JOBS.add(name)

            def delete_job(self, name):
                if self.proxy_errors_raised < proxy_errors:
                    self.proxy_errors_raised += 1
                    from unittest.mock import Mock
                    from requests.exceptions import HTTPError

                    response = Mock()
                    response.status_code = 403
                    raise HTTPError(response=response)

                self.DELETED_JOBS.add(name)

        monkeypatch.setattr(jenkins, "Jenkins", MockJenkins)

        return MockJenkins
