from textwrap import dedent

import pytest

from jobs_done10.jobs_done_job import JobsDoneFileTypeError
from jobs_done10.jobs_done_job import JobsDoneJob
from jobs_done10.jobs_done_job import UnknownJobsDoneFileOption
from jobs_done10.jobs_done_job import UnmatchableConditionError
from jobs_done10.repository import Repository


_REPOSITORY = Repository(url="https://space.git", branch="milky_way")


def testCreateJobsDoneJobFromYAML():
    yaml_contents = dedent(
        """
        junit_patterns:
        - "junit*.xml"

        boosttest_patterns:
        - "cpptest*.xml"

        display_name: "[{branch}] {planet}-{moon} {name}"

        label_expression: "planet-{planet}&&moon-{moon}"

        parameters:
        - choice:
            name: "PARAM"
            choices:
            - "choice_1"
            - "choice_2"
            description: "Description"

        build_batch_commands:
        - "command on planet {planet} (repository '{name}' on '{branch}')"

        matrix:
          planet:
          - mercury
          - venus

          moon:
          - europa
        """
    )
    jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)

    # Two possible jobs based on matrix (mercury and venus)
    assert len(jobs_done_jobs) == 2

    def CheckCommonValues(jobs_done_job):
        assert jobs_done_job.matrix == {
            "moon": ["europa"],
            "planet": ["mercury", "venus"],
        }
        assert jobs_done_job.junit_patterns == ["junit*.xml"]
        assert jobs_done_job.boosttest_patterns == ["cpptest*.xml"]
        assert jobs_done_job.parameters == [
            {
                "choice": {
                    "name": "PARAM",
                    "choices": ["choice_1", "choice_2"],
                    "description": "Description",
                }
            }
        ]

    CheckCommonValues(jobs_done_jobs[0])
    CheckCommonValues(jobs_done_jobs[1])

    # Tests for specific jobs
    mercury_job = (
        jobs_done_jobs[0]
        if jobs_done_jobs[0].matrix_row["planet"] == "mercury"
        else jobs_done_jobs[1]
    )
    venus_job = (
        jobs_done_jobs[0]
        if jobs_done_jobs[0].matrix_row["planet"] == "venus"
        else jobs_done_jobs[1]
    )

    assert mercury_job.matrix == {"moon": ["europa"], "planet": ["mercury", "venus"]}
    assert mercury_job.matrix_row == {"moon": "europa", "planet": "mercury"}

    assert venus_job.matrix == {"moon": ["europa"], "planet": ["mercury", "venus"]}
    assert venus_job.matrix_row == {"moon": "europa", "planet": "venus"}

    # In this case, our commands use some replacement variables, including variables defined in
    # 'matrix', and special cases 'name' and 'branch' based on repository.
    assert mercury_job.build_batch_commands == [
        "command on planet mercury (repository 'space' on 'milky_way')"
    ]
    assert venus_job.build_batch_commands == [
        "command on planet venus (repository 'space' on 'milky_way')"
    ]

    # Check display_name
    assert mercury_job.display_name == "[milky_way] mercury-europa space"
    assert mercury_job.label_expression == "planet-mercury&&moon-europa"

    # Check labels
    assert venus_job.display_name == "[milky_way] venus-europa space"
    assert venus_job.label_expression == "planet-venus&&moon-europa"


def testExclude():
    key = lambda job: ":".join(
        j + "-" + job.matrix_row[j] for j in sorted(job.matrix_row.keys())
    )
    # Base case ------------------------------------------------------------------------------------
    yaml_contents = dedent(
        """
        matrix:
          planet:
          - mercury
          - venus

          moon:
          - europa
          - ganymede

        """
    )
    jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)
    assert sorted(map(key, jobs_done_jobs)) == [
        "moon-europa:planet-mercury",
        "moon-europa:planet-venus",
        "moon-ganymede:planet-mercury",
        "moon-ganymede:planet-venus",
    ]

    # Exclude everything matching planet-venus -----------------------------------------------------
    yaml_contents = dedent(
        """
        matrix:
          planet:
          - mercury
          - venus

          moon:
          - europa
          - ganymede

        planet-venus:exclude: yes
        """
    )
    jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)
    assert sorted(map(key, jobs_done_jobs)) == [
        "moon-europa:planet-mercury",
        "moon-ganymede:planet-mercury",
    ]

    # Exclude everything matching planet-venus and moon europa -------------------------------------
    yaml_contents = dedent(
        """
        matrix:
          planet:
          - mercury
          - venus

          moon:
          - europa
          - ganymede

        planet-venus:moon-europa:exclude: yes
        """
    )
    jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)
    assert sorted(map(key, jobs_done_jobs)) == [
        "moon-europa:planet-mercury",
        "moon-ganymede:planet-mercury",
        "moon-ganymede:planet-venus",
    ]

    # Exclude everything ---------------------------------------------------------------------------
    yaml_contents = dedent(
        """
        matrix:
          planet:
          - mercury
          - venus

          moon:
          - europa
          - ganymede

        exclude: yes
        """
    )
    jobs_done_jobs = JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)
    assert sorted(map(key, jobs_done_jobs)) == []


def testBranchFlags():
    yaml_contents = dedent(
        """
        branch-master:build_shell_commands:
        - "master.sh"

        branch-milky_way:build_batch_commands:
        - "milky_way.bat"

        branch-with-hyphens-in-name:build_batch_commands:
        - "crazy.bat"
        """
    )

    jd_file = JobsDoneJob.CreateFromYAML(
        yaml_contents,
        repository=Repository(url="https://space.git", branch="milky_way"),
    )[0]
    assert jd_file.build_shell_commands is None
    assert jd_file.build_batch_commands == ["milky_way.bat"]

    jd_file = JobsDoneJob.CreateFromYAML(
        yaml_contents, repository=Repository(url="https://space.git", branch="master")
    )[0]
    assert jd_file.build_shell_commands == ["master.sh"]
    assert jd_file.build_batch_commands is None


def testMatrixAndFlags():
    yaml_contents = dedent(
        """
        platform-windows:junit_patterns:
        - "junit*.xml"

        platform-linux:build_shell_commands:
        - "{platform} command"

        platform-windows:build_batch_commands:
        - "{platform} command"

        matrix:
            platform:
            - linux
            - windows
        """
    )
    for jd_file in JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY):
        if jd_file.matrix_row["platform"] == "linux":
            assert jd_file.junit_patterns is None
            assert jd_file.build_batch_commands is None
            assert jd_file.build_shell_commands == ["linux command"]
        else:
            assert jd_file.junit_patterns == ["junit*.xml"]
            assert jd_file.build_batch_commands == ["windows command"]
            assert jd_file.build_shell_commands is None


def testMatrixAndRegexFlags():
    yaml_contents = dedent(
        """
        platform-win.*:junit_patterns:
        - "junit*.xml"

        platform-(?!windows):build_shell_commands:
        - "{platform} command"

        matrix:
            platform:
            - linux
            - windows
        """
    )
    for jd_file in JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY):
        if jd_file.matrix_row["platform"] == "linux":
            assert jd_file.junit_patterns is None
            assert jd_file.build_batch_commands is None
            assert jd_file.build_shell_commands == ["linux command"]
        else:
            assert jd_file.junit_patterns == ["junit*.xml"]
            assert jd_file.build_shell_commands is None


def testMatrixAndExtraFlags():
    yaml_contents = dedent(
        """
        platform-windows:junit_patterns:
        - "junit*.xml"

        platform-linux:build_shell_commands:
        - "linux command: {platform}"

        platform-windows:build_batch_commands:
        - "windows command: {platform}"

        matrix:
            platform:
            - win32,windows
            - win64,windows
            - linux64,linux
        """
    )
    for jd_file in JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY):
        if jd_file.matrix_row["platform"] == "linux64":
            assert jd_file.junit_patterns is None
            assert jd_file.build_batch_commands is None
            assert jd_file.build_shell_commands == ["linux command: linux64"]
        if jd_file.matrix_row["platform"] == "win32":
            assert jd_file.junit_patterns == ["junit*.xml"]
            assert jd_file.build_batch_commands == ["windows command: win32"]
            assert jd_file.build_shell_commands is None


def testMatrixAndFlagsForSubDicts():
    yaml_contents = dedent(
        """
        git:
          platform-windows:shallow: true
          platform-linux:shallow: false

        additional_repositories:
        - git:
              platform-windows:shallow: true
              platform-linux:shallow: false

        matrix:
            platform:
            - linux
            - windows
        """
    )
    for jd_file in JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY):
        if jd_file.matrix_row["platform"] == "linux":
            assert jd_file.git == {"shallow": "false"}
            assert jd_file.additional_repositories == [{"git": {"shallow": "false"}}]
        else:
            assert jd_file.git == {"shallow": "true"}
            assert jd_file.additional_repositories == [{"git": {"shallow": "true"}}]


def testRaiseWithAmbiguousConditionsAndDifferentValues():
    """
    When we match more than one line for the same key, we need to choose only one of them
    consistently regardless of the order in which they appear.
    To do that the conditions present on one line should be a superset of other one. In the end
    the largest superset will be chosen.

    For example, for "platform=linux" and "slave=slave2" the following lines would be ambiguous:

        platform-linux:display_name: "Linux job"
        slave-slave2:display_name: "slave2 job"

    In this case, there are some matrix combinations that will match both lines and there is no
    obvious rule we can apply to choose one of them. Which one has priority: platform or slave?

    For the above example to work we need to make one line a superset of the other:

        platform-linux:display_name: "Linux job"
        platform-linux:slave-slave2:display_name: "slave2 job"

    And the second line would be chosen.


    NOTE:

    These rules are only relevant when multiple lines match. For example, if we have two
    exclusive lines like:

        platform-linux:display_name: "Linux job"
        platform-windows:display_name: "slave2 job"

    They are not ambiguous as only one will match for every matrix combination.
    """
    yaml_contents = dedent(
        """
        matrix:
            platform:
            - linux
            - windows

            slave:
            - slave1
            - slave2

        platform-linux:display_name: "Linux job"
        slave-slave2:display_name: "slave2 job"
        """
    )
    with pytest.raises(ValueError):
        JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)


def testIgnoreAmbiguousConditionsWithEqualValues():
    """
    ..see: `testRaiseWithAmbiguousConditionsAndDifferentValues` for more details

    Even though we should raise when there are multiple matched lines with ambiguous conditions, we
    should ignore when the value does not change. This is very useful when you have a large matrix
    and need to set the same value for a lot of them.
    """
    yaml_contents = dedent(
        """
        matrix:
            platform:
            - linux
            - windows

            slave:
            - slave1
            - slave2

        platform-linux:display_name: "Foo job"
        slave-slave2:display_name: "Foo job"
        """
    )
    for jd_file in JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY):
        if (
            jd_file.matrix_row["platform"] == "linux"
            or jd_file.matrix_row["slave"] == "slave2"
        ):
            assert jd_file.display_name == "Foo job"
        else:
            assert jd_file.display_name is None


def testAllowOverridingConditions():
    """
    ..see: `testRaiseWithAmbiguousConditionsAndDifferentValues` for more details
    """
    yaml_contents = dedent(
        """
        matrix:
            platform:
            - linux
            - windows

            slave:
            - slave1
            - slave2

        display_name: "Generic job"
        platform-linux:display_name: "Linux job"
        platform-linux:slave-slave2:display_name: "slave2 job"
        """
    )
    for jd_file in JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY):
        if jd_file.matrix_row["platform"] == "linux":
            if jd_file.matrix_row["slave"] == "slave1":
                assert jd_file.display_name == "Linux job"
            else:
                assert jd_file.display_name == "slave2 job"
        else:
            assert jd_file.display_name == "Generic job"


def testBranchPatterns():
    base_contents = dedent(
        """
        matrix:
            planet:
            - mars
            - earth
            - venus

        """
    )
    # Using a pattern that does not match our branch will prevent jobs from being generated
    jd_file_contents = base_contents + dedent(
        """
        branch_patterns:
        - feature-.*
        """
    )
    jobs = JobsDoneJob.CreateFromYAML(jd_file_contents, repository=_REPOSITORY)
    assert len(jobs) == 0

    # Matching patterns work as usual
    jd_file_contents = base_contents + dedent(
        """
        branch_patterns:
        - milky_way
        """
    )
    jobs = JobsDoneJob.CreateFromYAML(jd_file_contents, repository=_REPOSITORY)
    assert len(jobs) == 3

    # Also works with several patterns and regexes
    jd_file_contents = base_contents + dedent(
        """
        branch_patterns:
        - master
        - milky.*
        """
    )
    jobs = JobsDoneJob.CreateFromYAML(jd_file_contents, repository=_REPOSITORY)
    assert len(jobs) == 3

    # Branch patterns can also be filtered using matrix
    # e.g., mars only has jobs in master
    jd_file_contents = base_contents + dedent(
        """
        planet-mars:branch_patterns:
        - "master"

        planet-earth:branch_patterns:
        - ".*"

        planet-venus:branch_patterns:
        - ".*"
        """
    )
    jobs = JobsDoneJob.CreateFromYAML(jd_file_contents, repository=_REPOSITORY)
    assert len(jobs) == 2


def testUnknownOption():
    # Unknown options should fail
    yaml_contents = dedent(
        """
        bad_option: value
        """
    )
    with pytest.raises(UnknownJobsDoneFileOption) as e:
        JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)

    assert e.value.option_name == "bad_option"


def testTypeChecking():
    # List is the correct type for build_batch_commands
    yaml_contents = dedent(
        """
        build_batch_commands:
        - "list item 1"
        """
    )
    JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)

    # Trying to set a different value, should raise an error
    yaml_contents = dedent(
        """
        build_batch_commands: "string item"
        """
    )
    with pytest.raises(JobsDoneFileTypeError) as e:
        JobsDoneJob.CreateFromYAML(yaml_contents, repository=_REPOSITORY)

    assert e.value.option_name == "build_batch_commands"
    assert e.value.accepted_types == [
        JobsDoneJob.PARSEABLE_OPTIONS["build_batch_commands"]
    ]
    assert e.value.obtained_type == str
    assert e.value.option_value == "string item"


def testCreateFromFile(tmpdir):
    contents = dedent(
        """
        matrix:
            planet:
            - mars
            - earth
            - venus

        """
    )
    f = tmpdir / ".jobs_done.yaml"
    f.write(contents)

    jobs = JobsDoneJob.CreateFromFile(str(f), repository=_REPOSITORY)

    assert len(jobs) == 3


def testStringConversion():
    """
    Asserts that our YAML parser converts all basic values to strings (non unicode)
    """
    contents = dedent(
        """
        junit_patterns:
            - 1
        """
    )
    jobs = JobsDoneJob.CreateFromYAML(contents, repository=_REPOSITORY)

    assert jobs[0].junit_patterns != [1]
    assert jobs[0].junit_patterns == ["1"]


def testIgnoreUnmatchable():
    """
    Asserts that using a condition that can never be matched will not raise an error if
    'ignore_unmatchable' is enabled.
    """
    contents = dedent(
        """
        ignore_unmatchable: true

        planet-pluto:junit_patterns:
            - '*.xml'

        matrix:
            planet:
            - earth
        """
    )
    JobsDoneJob.CreateFromYAML(contents, repository=_REPOSITORY)


def testUnmatchableCondition():
    """
    Asserts that using a condition that can never be matched will raise an error.
    """
    contents = dedent(
        """
        planet-pluto:junit_patterns:
            - '*.xml'

        matrix:
            planet:
            - earth
        """
    )
    with pytest.raises(UnmatchableConditionError) as e:
        JobsDoneJob.CreateFromYAML(contents, repository=_REPOSITORY)

    assert e.value.option == "planet-pluto:junit_patterns"


def testUnmatchableSubCondition():
    contents = dedent(
        """
        git:
            planet-pluto:shallow: true

        matrix:
            planet:
            - earth
        """
    )
    with pytest.raises(UnmatchableConditionError) as e:
        JobsDoneJob.CreateFromYAML(contents, repository=_REPOSITORY)
    assert e.value.option == "planet-pluto:shallow"

    contents = dedent(
        """
        additional_repositories:
        - git:
            planet-pluto:shallow: true

        matrix:
            planet:
            - earth
        """
    )
    with pytest.raises(UnmatchableConditionError) as e:
        JobsDoneJob.CreateFromYAML(contents, repository=_REPOSITORY)
    assert e.value.option == "planet-pluto:shallow"


def testStripFile():
    """
    Asserts that we can handle empty spaces and tabs in .yaml files, without having parse errors
    """
    contents = dedent(
        """
        junit_patterns:
            - 1
        """
    )
    contents += "\t"
    JobsDoneJob.CreateFromYAML(contents, repository=_REPOSITORY)
