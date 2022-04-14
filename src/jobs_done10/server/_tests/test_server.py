# mypy: disallow-untyped-defs
import json
from pathlib import Path
from textwrap import dedent
from typing import Any
from typing import Dict
from typing import Iterator

import pytest
import requests_mock
from flask.testing import FlaskClient
from pytest_mock import MockerFixture

from jobs_done10.repository import Repository
from jobs_done10.server.app import JobsDoneRequest


@pytest.fixture(name="client")
def client_(monkeypatch: pytest.MonkeyPatch) -> FlaskClient:
    from jobs_done10.server.app import app

    test_env = {
        "JD_JENKINS_URL": "https://example.com/jenkins",
        "JD_JENKINS_USERNAME": "jenkins_user",
        "JD_JENKINS_PASSWORD": "jenkins_password",
        "JD_STASH_URL": "https://example.com/stash",
        "JD_STASH_USERNAME": "stash_user",
        "JD_STASH_PASSWORD": "stash_password",
        "JD_EMAIL_SERVER": "smtp.example.com",
        "JD_EMAIL_FROM": "JobsDone Bot <jobsdone@example.com>",
        "JD_EMAIL_PORT": "5900",
        "JD_EMAIL_USER": "email_user",
        "JD_EMAIL_PASSWORD": "email_password",
    }
    for env_var, value in test_env.items():
        monkeypatch.setenv(env_var, value)

    return app.test_client()


@pytest.fixture(name="stash_post_data")
def stash_post_data_(datadir: Path) -> Dict[str, Any]:
    """
    Return the json data which posted by Stash/BitBucket Server. Obtained from the webhooks page configuration:

        https://eden.esss.com.br/stash/plugins/servlet/webhooks/projects/ESSS/repos/eden

    There's a "View details" link which you can inspect the body of the post.
    """
    return json.loads(datadir.joinpath("stash-post.json").read_text(encoding="UTF-8"))


@pytest.fixture(name="repo_info_json_data")
def repo_info_json_data_(datadir: Path) -> Dict[str, Any]:
    """
    Return json data that results from a call to the project/slug endpoint.

    Taken from manually doing the query on our live server.
    """
    return json.loads(
        datadir.joinpath("stash-repo-info.json").read_text(encoding="UTF-8")
    )


@pytest.fixture(name="github_post_data")
def github_post_data_(datadir: Path) -> Dict[str, Any]:
    """
    Return the json data posted by GitHub on push events.

    Docs:

        https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#push

    The contents were obtained by configuring the webhook in a repo to post to https://requestbin.com.
    """
    return json.loads(datadir.joinpath("github-post.json").read_text(encoding="UTF-8"))


@pytest.fixture
def mock_stash_repo_requests(repo_info_json_data: Dict[str, Any]) -> Iterator[None]:
    with requests_mock.Mocker() as m:
        stash_url = "https://example.com/stash"
        project_key = "ESSS"
        slug = "eden"
        path = ".jobs_done.yaml"
        ref = "8522b06a7c330008814a522d0342be9a997a1460"
        m.get(
            f"{stash_url}/projects/{project_key}/repos/{slug}/raw/{path}?at={ref}",
            text="jobs_done yaml contents",
        )

        m.get(
            f"{stash_url}/rest/api/1.0/projects/{project_key}/repos/{slug}",
            json=repo_info_json_data,
        )
        yield


def test_stash_post(
    client: FlaskClient,
    stash_post_data: Dict[str, Any],
    mocker: MockerFixture,
    repo_info_json_data: Dict[str, Any],
    mock_stash_repo_requests: None,
) -> None:
    new_jobs = ["new1-eden-master", "new2-eden-master"]
    updated_jobs = ["upd1-eden-master", "upd2-eden-master"]
    deleted_jobs = ["del1-eden-master", "del2-eden-master"]

    upload_mock = mocker.patch(
        "jobs_done10.generators.jenkins.UploadJobsFromFile",
        autospec=True,
        return_value=(new_jobs, updated_jobs, deleted_jobs),
    )

    response = client.post(json=stash_post_data)
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert (
        response.data.decode("UTF-8")
        == dedent(
            """
                NEW - new1-eden-master
                NEW - new2-eden-master
                UPD - upd1-eden-master
                UPD - upd2-eden-master
                DEL - del1-eden-master
                DEL - del2-eden-master
            """
        ).strip()
    )

    assert upload_mock.call_count == 1
    args, kwargs = upload_mock.call_args
    assert args == ()
    assert kwargs == dict(
        repository=Repository(
            "ssh://git@eden.fln.esss.com.br:7999/esss/eden.git", "stable-pwda11-master"
        ),
        jobs_done_file_contents="jobs_done yaml contents",
        url="https://example.com/jenkins",
        username="jenkins_user",
        password="jenkins_password",
    )


def test_version(client: FlaskClient) -> None:
    import pkg_resources

    version = pkg_resources.get_distribution("jobs_done10").version
    response = client.post(json={"test": True})
    assert response.data.decode("UTF-8") == f"jobs_done10 ver. {version}"


def test_error_handling(
    client: FlaskClient,
    stash_post_data: Dict[str, Any],
    mocker: MockerFixture,
    mock_stash_repo_requests: None,
) -> None:
    import mailer

    mocker.patch.object(mailer.Mailer, "send", autospec=True)
    mocker.spy(mailer.Mailer, "__init__")

    mocker.patch(
        "jobs_done10.generators.jenkins.UploadJobsFromFile",
        autospec=True,
        side_effect=RuntimeError("Error processing JobsDone"),
    )

    response = client.post(json=stash_post_data)
    assert response.status_code == 500
    assert response.mimetype == "text/html"
    obtained_message = response.data.decode("UTF-8")
    assert (
        "ERROR processing request: <Request 'http://localhost/' [POST]>"
        in obtained_message
    )
    assert "JSON data:" in obtained_message
    assert "Traceback (most recent call last):" in obtained_message
    assert "Email sent to bugreport+jenkins@esss.co" in obtained_message

    assert mailer.Mailer.__init__.call_count == 1
    assert mailer.Mailer.send.call_count == 1
    args, kwargs = mailer.Mailer.__init__.call_args
    assert kwargs == dict(
        host="smtp.example.com",
        port=5900,
        use_tls=True,
        usr="email_user",
        pwd="email_password",
    )
    args, kwargs = mailer.Mailer.send.call_args
    assert len(args) == 2  # (self, message)
    message = args[-1]
    assert message.To == ["bugreport+jenkins@esss.co"]
    assert message.From == "JobsDone Bot <jobsdone@example.com>"
    assert (
        message.Subject
        == "JobsDone failure during push to ESSS/eden (stable-pwda11-master @ 8522b06)"
    )
    assert message.charset == "UTF-8"
    assert "An error happened when processing your push" in message.Body


@pytest.mark.parametrize("file_not_found", [True, False])
def test_iter_jobs_done_requests_for_github_payload(
    github_post_data: Dict[str, Any], file_not_found: bool
) -> None:
    from jobs_done10.server.app import iter_jobs_done_requests_for_github_payload

    file_contents = "jobs_done yaml contents"

    with requests_mock.Mocker() as m:
        username = "my-username"
        token = "MY-TOKEN"
        owner_name = "ESSS"
        repo_name = "test-webhooks"
        ref = "2c202379fefc2ca03c390b30050a87a87c9a4c81"
        status_code = 404 if file_not_found else 200
        m.get(
            f"https://{username}:{token}@raw.githubusercontent.com/{owner_name}/{repo_name}/{ref}/.jobs_done.yaml",
            text=file_contents,
            status_code=status_code,
        )
        settings = {"JD_GH_USERNAME": username, "JD_GH_TOKEN": token}
        (request,) = iter_jobs_done_requests_for_github_payload(
            github_post_data, settings
        )

    expected_contents = None if file_not_found else file_contents
    assert request == JobsDoneRequest(
        owner_name="ESSS",
        repo_name="test-webhooks",
        pusher_email="nicoddemus@gmail.com",
        commit="2c202379fefc2ca03c390b30050a87a87c9a4c81",
        clone_url="git@github.com:ESSS/test-webhooks.git",
        branch="fb-add-jobs-done",
        jobs_done_file_contents=expected_contents,
    )
