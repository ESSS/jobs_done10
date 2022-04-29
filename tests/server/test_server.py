# mypy: disallow-untyped-defs
import json
import os
from base64 import b64encode
from contextlib import contextmanager
from http import HTTPStatus
from pathlib import Path
from textwrap import dedent
from typing import Any
from typing import Dict
from typing import Iterator

import pkg_resources
import pytest
import requests_mock
from flask.testing import FlaskClient
from pytest_mock import MockerFixture

from jobs_done10.repository import Repository
from jobs_done10.server.app import app
from jobs_done10.server.app import JobsDoneRequest
from jobs_done10.server.app import parse_github_post
from jobs_done10.server.app import SignatureVerificationError
from jobs_done10.server.app import verify_github_signature


@pytest.fixture(name="configure_environment")
def configure_environment_(monkeypatch: pytest.MonkeyPatch) -> None:
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
        "JD_GH_TOKEN": "gh-token",
        "JD_GH_WEBHOOK_SECRET": "MY SECRET",
    }
    for env_var, value in test_env.items():
        monkeypatch.setenv(env_var, value)


@pytest.fixture(name="client")
def client_(configure_environment: None) -> FlaskClient:
    return app.test_client()


@pytest.fixture(name="stash_post_data")
def stash_post_data_(datadir: Path) -> Dict[str, Any]:
    """
    Return the json data which posted by Stash/BitBucket Server. Obtained from the webhooks page configuration:

        https://eden.esss.com.br/stash/plugins/servlet/webhooks/projects/ESSS/repos/eden

    There's a "View details" link which you can inspect the body of the post.
    """
    return json.loads(datadir.joinpath("stash-post.json").read_text(encoding="UTF-8"))


@pytest.fixture(name="stash_repo_info_data")
def stash_repo_info_data_(datadir: Path) -> Dict[str, Any]:
    """
    Return json data that results from a call to the project/slug endpoint.

    Taken from manually doing the query on our live server.
    """
    return json.loads(
        datadir.joinpath("stash-repo-info.json").read_text(encoding="UTF-8")
    )


@pytest.fixture(name="github_post_data")
def github_post_data_(datadir: Path) -> bytes:
    """
    Return the raw data posted by GitHub on push events.

    Docs:

        https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#push

    The contents were obtained by configuring the webhook in a repo to post to https://requestbin.com.
    """
    return datadir.joinpath("github-post.body.data").read_bytes()


@pytest.fixture(name="github_post_headers")
def github_post_headers_(datadir: Path) -> Dict[str, Any]:
    """
    Return the headers posted by GitHub on push events.

    Same docs as in github_post_payload.
    """
    return json.loads(
        datadir.joinpath("github-post.headers.json").read_text(encoding="UTF-8")
    )


@pytest.fixture(name="github_post_del_branch_data")
def github_post_del_branch_data_(datadir: Path) -> bytes:
    """
    Same as git_hub_post_data, but for post about a branch being deleted.
    """
    return datadir.joinpath("github-post-del-branch.body.data").read_bytes()


@pytest.fixture(name="github_post_del_branch_headers")
def github_post_del_branch_headers_(datadir: Path) -> Dict[str, Any]:
    """
    Same as git_hub_post_headers, but for post about a branch being deleted.
    """
    return json.loads(
        datadir.joinpath("github-post-del-branch.headers.json").read_text(
            encoding="UTF-8"
        )
    )


@contextmanager
def mock_stash_repo_requests(stash_repo_info_data: Dict[str, Any]) -> Iterator[None]:
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
            json=stash_repo_info_data,
        )
        yield


@contextmanager
def mock_github_repo_requests(
    file_contents: str, status_code: int, settings: Dict[str, str]
) -> Iterator[None]:
    with requests_mock.Mocker() as m:
        token = settings["JD_GH_TOKEN"]
        owner_name = "ESSS"
        repo_name = "test-webhooks"
        ref = "17fcbd494ea4a140a4d4816de218e761b264b1b1"
        encoded_content = b64encode(file_contents.encode("UTF-8")).decode("ASCII")
        m.get(
            f"https://api.github.com/repos/{owner_name}/{repo_name}/contents/.jobs_done.yaml",
            json={"content": encoded_content, "encoding": "base64"},
            status_code=status_code,
        )
        yield
        history = m.request_history[0]
        assert history.qs == {"ref": [ref]}
        # According to requests.auth._basic_auth_str(), basic authentications
        # is encoded as "{username}:{password}" as a base64 string.
        username = ""
        basic_auth = b64encode(f"{username}:{token}".encode("UTF-8"))
        assert (
            history.headers.get("Authorization")
            == f"Basic {basic_auth.decode('ASCII')}"
        )


@pytest.mark.parametrize("post_url", ["/", "/stash"])
def test_stash_post(
    client: FlaskClient,
    stash_post_data: Dict[str, Any],
    mocker: MockerFixture,
    stash_repo_info_data: Dict[str, Any],
    post_url: str,
) -> None:
    new_jobs = ["new1-eden-master", "new2-eden-master"]
    updated_jobs = ["upd1-eden-master", "upd2-eden-master"]
    deleted_jobs = ["del1-eden-master", "del2-eden-master"]

    upload_mock = mocker.patch(
        "jobs_done10.generators.jenkins.UploadJobsFromFile",
        autospec=True,
        return_value=(new_jobs, updated_jobs, deleted_jobs),
    )

    with mock_stash_repo_requests(stash_repo_info_data):
        response = client.post(post_url, json=stash_post_data)
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


def test_github_post(
    client: FlaskClient,
    github_post_data: bytes,
    github_post_headers: Dict[str, Any],
    mocker: MockerFixture,
) -> None:
    new_jobs = ["new1-eden-master", "new2-eden-master"]
    updated_jobs = ["upd1-eden-master", "upd2-eden-master"]
    deleted_jobs = ["del1-eden-master", "del2-eden-master"]

    upload_mock = mocker.patch(
        "jobs_done10.generators.jenkins.UploadJobsFromFile",
        autospec=True,
        return_value=(new_jobs, updated_jobs, deleted_jobs),
    )

    file_contents = "github jobs done contents"
    with mock_github_repo_requests(
        file_contents, status_code=200, settings=dict(os.environ)
    ):
        response = client.post(
            "/github", data=github_post_data, headers=github_post_headers
        )

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
            "git@github.com:ESSS/test-webhooks.git", "fb-add-jobs-done"
        ),
        jobs_done_file_contents=file_contents,
        url="https://example.com/jenkins",
        username="jenkins_user",
        password="jenkins_password",
    )


def test_github_post_signature_failed(
    client: FlaskClient,
    github_post_data: bytes,
    github_post_headers: Dict[str, Any],
) -> None:
    tampered_data = github_post_data + b"\n"
    response = client.post("/github", data=tampered_data, headers=github_post_headers)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.data.decode("UTF-8") == (
        "Computed signature does not match the one in the header"
    )


@pytest.mark.parametrize("endpoint", ["/", "/stash", "/github"])
def test_version(client: FlaskClient, endpoint: str) -> None:
    version = pkg_resources.get_distribution("jobs_done10").version
    response = client.get(endpoint)
    expected = f"jobs_done10 ver. {version}"
    assert response.data.decode("UTF-8") == expected

    response = client.post(endpoint)
    assert response.data.decode("UTF-8") == expected


@pytest.mark.parametrize("endpoint", ["/", "/stash", "/github"])
def test_post_invalid_content_type(client: FlaskClient, endpoint: str) -> None:
    response = client.post(
        endpoint, json="hello", headers={"content-type": "application/text"}
    )
    assert response.data.decode("UTF-8") == f"Only posts in JSON format accepted"
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_error_handling(
    client: FlaskClient,
    stash_post_data: Dict[str, Any],
    mocker: MockerFixture,
    stash_repo_info_data: Dict[str, Any],
) -> None:
    import mailer

    mocker.patch.object(mailer.Mailer, "send", autospec=True)
    mocker.spy(mailer.Mailer, "__init__")

    mocker.patch(
        "jobs_done10.generators.jenkins.UploadJobsFromFile",
        autospec=True,
        side_effect=RuntimeError("Error processing JobsDone"),
    )

    with mock_stash_repo_requests(stash_repo_info_data):
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
def test_parse_github_post(
    github_post_data: bytes, github_post_headers: Dict[str, Any], file_not_found: bool
) -> None:

    file_contents = "jobs_done yaml contents"

    settings = {
        "JD_GH_TOKEN": "GH-TOKEN",
        "JD_GH_WEBHOOK_SECRET": "MY SECRET",
    }
    with mock_github_repo_requests(
        file_contents,
        status_code=HTTPStatus.NOT_FOUND if file_not_found else HTTPStatus.OK,
        settings=settings,
    ):
        (request,) = parse_github_post(
            github_post_headers,
            json.loads(github_post_data),
            github_post_data,
            settings,
        )

    expected_contents = None if file_not_found else file_contents
    assert request == JobsDoneRequest(
        owner_name="ESSS",
        repo_name="test-webhooks",
        pusher_email="nicoddemus@gmail.com",
        commit="17fcbd494ea4a140a4d4816de218e761b264b1b1",
        clone_url="git@github.com:ESSS/test-webhooks.git",
        branch="fb-add-jobs-done",
        jobs_done_file_contents=expected_contents,
    )


def test_parse_github_post_delete_branch(
    github_post_del_branch_data: bytes, github_post_del_branch_headers: Dict[str, Any]
) -> None:
    settings = {
        "JD_GH_TOKEN": "GH-TOKEN",
        "JD_GH_WEBHOOK_SECRET": "MY SECRET",
    }
    (request,) = parse_github_post(
        github_post_del_branch_headers,
        json.loads(github_post_del_branch_data),
        github_post_del_branch_data,
        settings,
    )

    assert request == JobsDoneRequest(
        owner_name="ESSS",
        repo_name="test-webhooks",
        pusher_email="nicoddemus@gmail.com",
        commit=None,
        clone_url="git@github.com:ESSS/test-webhooks.git",
        branch="fb-add-jobs-done2",
        jobs_done_file_contents=None,
    )


def test_verify_github_signature(
    github_post_data: bytes,
    github_post_headers: Dict[str, Any],
    configure_environment: None,
) -> None:
    # The original post and secret should match without an exception.
    verify_github_signature(
        github_post_headers, github_post_data, os.environ["JD_GH_WEBHOOK_SECRET"]
    )

    with pytest.raises(
        SignatureVerificationError, match="Computed signature does not match.*"
    ):
        tampered_data = github_post_data + b"\n"
        verify_github_signature(
            github_post_headers, tampered_data, os.environ["JD_GH_WEBHOOK_SECRET"]
        )

    # Should fail if the signature header is not present.
    with pytest.raises(
        SignatureVerificationError,
        match='Missing "x-hub-signature-256" entry in header',
    ):
        del github_post_headers["x-hub-signature-256"]
        verify_github_signature(
            github_post_headers, github_post_data, os.environ["JD_GH_WEBHOOK_SECRET"]
        )
