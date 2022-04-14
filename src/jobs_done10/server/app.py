# mypy: disallow-untyped-defs
import os
import pprint
import traceback
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import attr
import flask
import requests
from dotenv import load_dotenv
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer
from pygments.lexers import PythonTracebackLexer

from jobs_done10 import get_version_title
from jobs_done10.server_email_templates import EMAIL_HTML
from jobs_done10.server_email_templates import EMAIL_PLAINTEXT


app = flask.Flask("jobs_done")
load_dotenv(dotenv_path=os.environ.get("JOBSDONE_DOTENV"))
if not app.debug:
    app.logger.setLevel("INFO")
app.logger.info(f"Initializing Server App - {get_version_title()}")


@app.route("/", methods=["GET", "POST"])
def index() -> Union[str, Tuple[str, int]]:
    """
    Jenkins job creation/update/deletion end-point for stash.
    """
    return _handle_end_point(iter_jobs_done_requests_for_stash_payload)


def _handle_end_point(
    iter_jobs_done_requests: Callable[
        [Dict[str, Any], Dict[str, str]], Iterator["JobsDoneRequest"]
    ]
) -> Union[str, Tuple[str, int]]:
    """Common handling for the jobs-done end-point."""
    payload = flask.request.json
    app.logger.info(f"Received request:\n{pprint.pformat(payload)}")
    if flask.request.method == "GET" or payload is None or payload.get("test"):
        # return a 200 response also on POST, when no JSON data is posted; this is useful
        # because the "Test Connection" in BitBucket does just that, making it easy to verify
        # we have the correct version up.
        app.logger.info("I'm alive")
        return get_version_title()

    jobs_done_requests = []
    try:
        jobs_done_requests = list(iter_jobs_done_requests(payload, dict(os.environ)))
        message = _process_jobs_done_request(jobs_done_requests)
        app.logger.info(message)
        return message
    except Exception:
        err_message = _process_jobs_done_error(jobs_done_requests, payload)
        app.logger.exception("Uncaught exception")
        return err_message, 500


@attr.s(auto_attribs=True, frozen=True)
class JobsDoneRequest:
    """
    Information necessary to process a jobs done request to create/update/delete jobs
    for a branch in a repository.
    """

    # Owner of the repository: "ESSS" for example.
    owner_name: str
    # Repository name: "etk" for example.
    repo_name: str
    pusher_email: str
    commit: str
    clone_url: str
    branch: str
    jobs_done_file_contents: Optional[str]


def iter_jobs_done_requests_for_stash_payload(
    payload: Dict[str, Any], settings: Dict[str, str]
) -> Iterator[JobsDoneRequest]:
    """
    Parses a Stash payload from a push event into jobs done requests.

    See ``_tests/test_server/stash-post.json`` for an example of a payload.
    """
    if not isinstance(payload, dict) or "eventKey" not in payload:
        raise RuntimeError(f"Invalid request json data: {pprint.pformat(payload)}")

    stash_url = settings["JD_STASH_URL"].rstrip()
    stash_username = settings["JD_STASH_USERNAME"]
    stash_password = settings["JD_STASH_PASSWORD"]
    project_key = payload["repository"]["project"]["key"]
    slug = payload["repository"]["slug"]
    pusher_email = payload["actor"]["emailAddress"]

    for change in payload["changes"]:
        branch = change["ref"]["id"]
        prefix = "refs/heads/"
        if not branch.startswith(prefix):
            continue

        branch = branch[len(prefix) :]
        try:
            jobs_done_file_contents = get_stash_file_contents(
                stash_url=stash_url,
                username=stash_username,
                password=stash_password,
                project_key=project_key,
                slug=slug,
                path=".jobs_done.yaml",
                ref=change["toHash"],
            )
        except IOError:
            jobs_done_file_contents = None

        clone_url = get_stash_clone_url(
            stash_url=stash_url,
            username=stash_username,
            password=stash_password,
            project_key=project_key,
            slug=slug,
        )

        yield JobsDoneRequest(
            owner_name=project_key,
            repo_name=slug,
            clone_url=clone_url,
            commit=change["toHash"],
            pusher_email=pusher_email,
            branch=branch,
            jobs_done_file_contents=jobs_done_file_contents,
        )


def iter_jobs_done_requests_for_github_payload(
    payload: Dict[str, Any], settings: Dict[str, str]
) -> Iterator[JobsDoneRequest]:
    """..."""
    owner_name = payload["repository"]["owner"]["login"]
    repo_name = payload["repository"]["name"]
    clone_url = payload["repository"]["ssh_url"]
    commit = payload["head_commit"]["id"]
    pusher_email = payload["pusher"]["email"]
    branch = payload["ref"]
    prefix = "refs/heads/"
    if branch.startswith(prefix):
        branch = branch[len(prefix) :]

    username = settings["JD_GH_USERNAME"]
    token = settings["JD_GH_TOKEN"]

    url = f"https://{username}:{token}@raw.githubusercontent.com/{owner_name}/{repo_name}/{commit}/.jobs_done.yaml"
    try:
        jobs_done_file_contents = _fetch_file_contents(url, auth=None)
    except IOError:
        jobs_done_file_contents = None

    yield JobsDoneRequest(
        owner_name=owner_name,
        repo_name=repo_name,
        clone_url=clone_url,
        commit=commit,
        branch=branch,
        pusher_email=pusher_email,
        jobs_done_file_contents=jobs_done_file_contents,
    )


def _process_jobs_done_request(jobs_done_requests: Iterable[JobsDoneRequest]) -> str:
    """
    Generate/update a Jenkins job from a request and returns a message
    informing what has been done.
    """
    from jobs_done10.generators import jenkins
    from jobs_done10.repository import Repository

    all_new_jobs = []
    all_updated_jobs = []
    all_deleted_jobs = []

    for request in jobs_done_requests:
        repository = Repository(url=request.clone_url, branch=request.branch)
        jenkins_url = os.environ["JD_JENKINS_URL"].rstrip("/")
        jenkins_username = os.environ["JD_JENKINS_USERNAME"]
        jenkins_password = os.environ["JD_JENKINS_PASSWORD"]

        new_jobs, updated_jobs, deleted_jobs = jenkins.UploadJobsFromFile(
            repository=repository,
            jobs_done_file_contents=request.jobs_done_file_contents,
            url=jenkins_url,
            username=jenkins_username,
            password=jenkins_password,
        )
        all_new_jobs.extend(new_jobs)
        all_updated_jobs.extend(updated_jobs)
        all_deleted_jobs.extend(deleted_jobs)

    lines: List[str] = []
    lines.extend(f"NEW - {x}" for x in all_new_jobs)
    lines.extend(f"UPD - {x}" for x in all_updated_jobs)
    lines.extend(f"DEL - {x}" for x in all_deleted_jobs)

    message = "\n".join(lines)
    return message


def _process_jobs_done_error(
    jobs_done_requests: List[JobsDoneRequest], payload: Dict[str, Any]
) -> str:
    """
    In case of error while processing the job generation request, sent an e-mail to the user with
    the traceback.
    """
    error_traceback = traceback.format_exc()
    lines = [
        f"ERROR processing request: {flask.request}",
        "",
        "JSON data:",
        "",
        pprint.pformat(payload),
        "",
        "",
        error_traceback,
        "",
    ]
    try:
        recipient = send_email_with_error(jobs_done_requests, payload, error_traceback)
    except Exception:
        lines.append("*" * 80)
        lines.append("ERROR SENDING EMAIL:")
        lines.append(traceback.format_exc())
    else:
        lines.append(f"Email sent to {recipient}")
    message = "\n".join(lines)
    return message


def get_stash_file_contents(
    *,
    stash_url: str,
    username: str,
    password: str,
    project_key: str,
    slug: str,
    path: str,
    ref: str,
) -> str:
    """
    Get the file contents from the stash server.

    We are using a "raw" Get which returns the entire file contents as text.
    """
    file_url = stash_url + f"/projects/{project_key}/repos/{slug}/raw/{path}?at={ref}"
    return _fetch_file_contents(file_url, auth=(username, password))


def _fetch_file_contents(file_url: str, *, auth: Optional[Tuple[str, str]]) -> str:
    """Fetches the contents of the file given the full URL, handling responses appropriately."""
    response = requests.get(file_url, auth=auth)
    if response.status_code == 404:
        raise IOError(f"File {file_url} not found in server")
    elif response.status_code != 200:
        # Raise other exceptions if unsuccessful
        response.raise_for_status()

    contents = response.text
    return contents


def get_stash_clone_url(
    *, stash_url: str, username: str, password: str, project_key: str, slug: str
) -> str:
    """
    Get information about the repository, returning the SSH clone url.

    See ``_tests/test_server/stash-repo-info.json`` for an example of a payload.
    """
    url = f"{stash_url}/rest/api/1.0/projects/{project_key}/repos/{slug}"
    response = requests.get(url, auth=(username, password))
    if response.status_code != 200:
        response.raise_for_status()

    data = response.json()
    for clone_url in data["links"]["clone"]:
        if clone_url["name"] == "ssh":
            return clone_url["href"]

    import pprint

    raise RuntimeError(
        f"Could not find the ssh clone url in json response:\n{pprint.pformat(data)}"
    )


def send_email_with_error(
    jobs_done_requests: List[JobsDoneRequest],
    payload: Dict[str, Any],
    error_traceback: str,
) -> str:
    """
    Send an email to the user who committed the changes that an error has happened while processing
    their .jobs_done file.

    Returns the recipient of the email in case of success, otherwise will raise an exception (not sure
    which exceptions are raised by the underlying library).
    """
    import mailer

    if not jobs_done_requests:
        raise RuntimeError("Cannot send an email without any parsed requests")

    pusher_email = jobs_done_requests[-1].pusher_email

    owner_name = jobs_done_requests[-1].owner_name
    repo_name = jobs_done_requests[-1].repo_name
    changes_msg = ", ".join(f"{x.branch} @ {x.commit[:7]}" for x in jobs_done_requests)
    subject = (
        f"JobsDone failure during push to {owner_name}/{repo_name} ({changes_msg})"
    )

    message = mailer.Message(
        From=os.environ["JD_EMAIL_FROM"],
        To=[pusher_email],
        Subject=subject,
        charset="UTF-8",
    )

    pretty_json = pprint.pformat(payload)
    message.Body = EMAIL_PLAINTEXT.format(
        error_traceback=error_traceback, pretty_json=pretty_json
    )
    style = "colorful"
    html = EMAIL_HTML.format(
        error_traceback_html=highlight(
            error_traceback, PythonTracebackLexer(), HtmlFormatter(style=style)
        ),
        pretty_json_html=highlight(
            pretty_json, JsonLexer(), HtmlFormatter(style=style)
        ),
    )

    message.Html = html

    sender = mailer.Mailer(
        host=os.environ["JD_EMAIL_SERVER"],
        port=int(os.environ["JD_EMAIL_PORT"]),
        use_tls=True,
        usr=os.environ["JD_EMAIL_USER"],
        pwd=os.environ["JD_EMAIL_PASSWORD"],
    )
    sender.send(message)
    return pusher_email
