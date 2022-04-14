# mypy: disallow-untyped-defs
import os
import pprint
import traceback
from typing import Any
from typing import Dict
from typing import Tuple
from typing import Union

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
    Jenkins job generation end-point

    Example of a post event for a push:

       {"eventKey": "repo:refs_changed", "date": "2018-06-18T16:20:06-0300",
        "actor": {"name": "jenkins", "emailAddress": "bugreport+jenkins@esss.co", "id": 2852,
                  "displayName": "jenkins", "active": true, "slug": "jenkins", "type": "NORMAL"},
        "repository": {"slug": "eden", "id": 2231, "name": "eden", "scmId": "git", "state": "AVAILABLE",
                       "statusMessage": "Available", "forkable": true,
                       "project": {"key": "ESSS", "id": 1, "name": "ESSS", "description": "Dev projects",
                                   "public": false, "type": "NORMAL"}, "public": false}, "changes": [
        {"ref": {"id": "refs/heads/stable-pwda11-master", "displayId": "stable-pwda11-master", "type": "BRANCH"},
         "refId": "refs/heads/stable-pwda11-master", "fromHash": "cd39f701ae0a729b73c57b7848fbd1f340a36514",
         "toHash": "8522b06a7c330008814a522d0342be9a997a1460", "type": "UPDATE"}]}
    """
    payload = flask.request.json
    if flask.request.method == "GET" or payload is None or payload.get("test"):
        # return a 200 response also on POST, when no JSON data is posted; this is useful
        # because the "Test Connection" in BitBucket does just that, making it easy to verify
        # we have the correct version up.
        app.logger.info("I'm alive")
        return get_version_title()

    try:
        message = _process_jobs_done_request(payload)
        return message
    except Exception:
        err_message = _process_jobs_done_error(payload)
        return err_message, 500


def _process_jobs_done_request(payload: Dict[str, Any]) -> str:
    """
    Generate/update a Jenkins job from a request and returns a debug message
    """
    if not isinstance(payload, dict) or "eventKey" not in payload:
        raise RuntimeError(f"Invalid request json data: {pprint.pformat(payload)}")

    app.logger.info(f"Received request:\n{pprint.pformat(payload)}")

    stash_url = os.environ["JD_STASH_URL"].rstrip()
    stash_username = os.environ["JD_STASH_USERNAME"]
    stash_password = os.environ["JD_STASH_PASSWORD"]
    project_key = payload["repository"]["project"]["key"]
    slug = payload["repository"]["slug"]

    all_new_jobs = []
    all_updated_jobs = []
    all_deleted_jobs = []
    lines = []
    for change in payload["changes"]:
        try:
            jobs_done_file_contents = get_file_contents(
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

        from jobs_done10.generators import jenkins
        from jobs_done10.repository import Repository

        clone_url = get_clone_url(
            stash_url=stash_url,
            username=stash_username,
            password=stash_password,
            project_key=project_key,
            slug=slug,
        )

        branch = change["ref"]["id"]
        prefix = "refs/heads/"
        if not branch.startswith(prefix):
            lines.append(f"WARNING: ignoring branch {branch}: expected {prefix}")
            continue
        branch = branch[len(prefix) :]
        repository = Repository(url=clone_url, branch=branch)
        jenkins_url = os.environ["JD_JENKINS_URL"].rstrip("/")
        jenkins_username = os.environ["JD_JENKINS_USERNAME"]
        jenkins_password = os.environ["JD_JENKINS_PASSWORD"]

        new_jobs, updated_jobs, deleted_jobs = jenkins.UploadJobsFromFile(
            repository=repository,
            jobs_done_file_contents=jobs_done_file_contents,
            url=jenkins_url,
            username=jenkins_username,
            password=jenkins_password,
        )
        all_new_jobs.extend(new_jobs)
        all_updated_jobs.extend(updated_jobs)
        all_deleted_jobs.extend(deleted_jobs)

    lines.extend(f"NEW - {x}" for x in all_new_jobs)
    lines.extend(f"UPD - {x}" for x in all_updated_jobs)
    lines.extend(f"DEL - {x}" for x in all_deleted_jobs)

    message = "\n".join(lines)
    app.logger.info(message)
    return message


def _process_jobs_done_error(payload: Dict[str, Any]) -> str:
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
        recipient = send_email_with_error(payload, error_traceback)
    except Exception:
        lines.append("*" * 80)
        lines.append("ERROR SENDING EMAIL:")
        lines.append(traceback.format_exc())
    else:
        lines.append(f"Email sent to {recipient}")
    message = "\n".join(lines)
    app.logger.exception("Uncaught exception")
    return message


def get_file_contents(
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
    response = requests.get(file_url, auth=(username, password))

    if response.status_code == 404:
        raise IOError('File "%s" not found. Full URL: %s' % (path, file_url))
    elif response.status_code != 200:
        # Raise other exceptions if unsuccessful
        response.raise_for_status()

    contents = response.text
    return contents


def get_clone_url(
    *, stash_url: str, username: str, password: str, project_key: str, slug: str
) -> str:
    """
    Get information about the repository, returning the SSH clone url.

    {'forkable': True,
     'id': 2231,
     'links': {'clone': [{'href': 'https://bruno@eden.esss.com.br/stash/scm/esss/eden.git',
                          'name': 'http'},
                         {'href': 'ssh://git@eden.fln.esss.com.br:7999/esss/eden.git',
                          'name': 'ssh'}],
               'self': [{'href': 'https://eden.esss.com.br/stash/projects/ESSS/repos/eden/browse'}]},
     'name': 'eden',
     'project': {'description': 'Dev projects',
                 'id': 1,
                 'key': 'ESSS',
                 'links': {'self': [{'href': 'https://eden.esss.com.br/stash/projects/ESSS'}]},
                 'name': 'ESSS',
                 'public': False,
                 'type': 'NORMAL'},
     'public': False,
     'scmId': 'git',
     'slug': 'eden',
     'state': 'AVAILABLE',
     'statusMessage': 'Available'}
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


def send_email_with_error(data: Dict[str, Any], error_traceback: str) -> str:
    """
    Send an email to the user who committed the changes that an error has happened while processing
    their .jobs_done file.

    Returns the recipient of the email in case of success, otherwise will raise an exception (not sure
    which exceptions are raised by the underlying library).
    """
    import mailer

    recipient = data["actor"]["emailAddress"]

    project_key = data["repository"]["project"]["key"]
    slug = data["repository"]["slug"]
    changes = [(change["ref"]["id"], change["toHash"]) for change in data["changes"]]
    changes_msg = ", ".join(
        f'{branch.replace("refs/heads/", "")} @ {commit[:7]}'
        for (branch, commit) in changes
    )
    subject = f"JobsDone failure during push to {project_key}/{slug} ({changes_msg})"

    message = mailer.Message(
        From=os.environ["JD_EMAIL_FROM"],
        To=[recipient],
        # RTo=None,
        # Cc=self.cc,
        Subject=subject,
        charset="UTF-8",
    )

    pretty_json = pprint.pformat(data)
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
    return recipient
