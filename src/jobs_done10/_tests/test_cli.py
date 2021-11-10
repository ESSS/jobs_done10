import pytest
from _pytest.pytester import LineMatcher
from click.testing import CliRunner

from jobs_done10.cli import jobs_done


@pytest.fixture
def cli_runner():
    """
    Fixture used to test click applications.
    :rtype: click.testing.CliRunner
    """
    return CliRunner()


def test_help(cli_runner):
    """
    :type cli_runner: click.testing.CliRunner
    """
    result = cli_runner.invoke(jobs_done, ["--help"])
    assert result.exit_code == 0, result.output
    matcher = LineMatcher(result.output.splitlines())
    matcher.fnmatch_lines(
        [
            "Usage: jobs_done10*",
            "*",
            "Options:",
            "*",
            "Commands:",
            "*",
        ]
    )
