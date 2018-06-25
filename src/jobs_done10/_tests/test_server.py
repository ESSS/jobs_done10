from textwrap import dedent

import pytest
import requests_mock

from jobs_done10.repository import Repository


@pytest.fixture(name='client')
def client_(monkeypatch, tmpdir):
    from jobs_done10.server import app

    env_vars = tmpdir.join('env_vars')
    monkeypatch.setenv('JOBSDONE_DOTENV', str(env_vars))

    env_vars.write("""
        JD_JENKINS_URL=https://example.com/jenkins
        JD_JENKINS_USERNAME=jenkins_user
        JD_JENKINS_PASSWORD=jenkins_password

        JD_STASH_URL=https://example.com/stash
        JD_STASH_USERNAME=stash_user
        JD_STASH_PASSWORD=stash_password

        JD_EMAIL_SERVER=smtp.example.com
        JD_EMAIL_FROM=JobsDone Bot <jobsdone@example.com>
        JD_EMAIL_PORT=5900
        JD_EMAIL_USER=email_user
        JD_EMAIL_PASSWORD=email_password
    """)

    return app.test_client()


@pytest.fixture(name='post_json_data')
def post_json_data_():
    """
    Return the json data which posted by Stash/BitBucket Server. Obtained from the webhooks page configuration:

        https://eden.esss.com.br/stash/plugins/servlet/webhooks/projects/ESSS/repos/eden

    There's a "View details" link which you can inspect the body of the post.
    """
    return {"eventKey": "repo:refs_changed", "date": "2018-06-18T16:20:06-0300",
            "actor": {"name": "jenkins", "emailAddress": "bugreport+jenkins@esss.co", "id": 2852,
                      "displayName": "jenkins", "active": True, "slug": "jenkins", "type": "NORMAL"},
            "repository": {"slug": "eden", "id": 2231, "name": "eden", "scmId": "git", "state": "AVAILABLE",
                           "statusMessage": "Available", "forkable": True,
                           "project": {"key": "ESSS", "id": 1, "name": "ESSS", "description": "Dev projects",
                                       "public": False, "type": "NORMAL"}, "public": False}, "changes": [
            {"ref": {"id": "refs/heads/stable-pwda11-master", "displayId": "stable-pwda11-master", "type": "BRANCH"},
             "refId": "refs/heads/stable-pwda11-master", "fromHash": "cd39f701ae0a729b73c57b7848fbd1f340a36514",
             "toHash": "8522b06a7c330008814a522d0342be9a997a1460", "type": "UPDATE"}]}


@pytest.fixture(name='repo_info_json_data')
def repo_info_json_data_():
    """
    Return json data that results from a call to the project/slug endpoint.

    Taken from manually doing the query on our live server.
    """
    return {'forkable': True,
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


def test_post(client, post_json_data, mocker, repo_info_json_data):
    contents = 'jobs_done yaml contents'

    new_jobs = ['new1-eden-master', 'new2-eden-master']
    updated_jobs = ['upd1-eden-master', 'upd2-eden-master']
    deleted_jobs = ['del1-eden-master', 'del2-eden-master']

    upload_mock = mocker.patch('jobs_done10.generators.jenkins.UploadJobsFromFile', autospec=True,
                               return_value=(new_jobs, updated_jobs, deleted_jobs))

    with requests_mock.Mocker() as m:
        stash_url = 'https://example.com/stash'
        project_key = 'ESSS'
        slug = 'eden'
        path = '.jobs_done.yaml'
        ref = '8522b06a7c330008814a522d0342be9a997a1460'
        m.get(f'{stash_url}/projects/{project_key}/repos/{slug}/raw/{path}?at={ref}', text=contents)

        m.get(f'{stash_url}/rest/api/1.0/projects/{project_key}/repos/{slug}', json=repo_info_json_data)

        response = client.post(json=post_json_data)
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
        assert response.data.decode('UTF-8') == dedent("""
            NEW - new1-eden-master
            NEW - new2-eden-master
            UPD - upd1-eden-master
            UPD - upd2-eden-master
            DEL - del1-eden-master
            DEL - del2-eden-master
        """).strip()

    assert upload_mock.call_count == 1
    args, kwargs = upload_mock.call_args
    assert args == ()
    assert kwargs == dict(
        repository=Repository('ssh://git@eden.fln.esss.com.br:7999/esss/eden.git', 'stable-pwda11-master'),
        jobs_done_file_contents=contents,
        url='https://example.com/jenkins',
        username='jenkins_user',
        password='jenkins_password',
    )


def test_error_handling(client, post_json_data, mocker):
    import mailer

    mocker.patch.object(mailer.Mailer, 'send', autospec=True)
    mocker.spy(mailer.Mailer, '__init__')

    del post_json_data['eventKey']
    response = client.post(json=post_json_data)
    assert response.status_code == 500
    assert response.mimetype == 'text/plain'
    obtained_message = response.data.decode('UTF-8')
    assert "ERROR processing request: <Request 'http://localhost/' [POST]>" in obtained_message
    assert "JSON data:" in obtained_message
    assert "Traceback (most recent call last):" in obtained_message
    assert "Email sent to bugreport+jenkins@esss.co" in obtained_message

    assert mailer.Mailer.__init__.call_count == 1
    assert mailer.Mailer.send.call_count == 1
    args, kwargs = mailer.Mailer.__init__.call_args
    assert kwargs == dict(
        host='smtp.example.com',
        port=5900,
        use_tls=True,
        usr='email_user',
        pwd='email_password',
    )
    args, kwargs = mailer.Mailer.send.call_args
    assert len(args) == 2  # (self, message)
    message = args[-1]
    assert message.To == ['bugreport+jenkins@esss.co']
    assert message.From == 'JobsDone Bot <jobsdone@example.com>'
    assert message.Subject == 'JobsDone failure during push to ESSS/eden (stable-pwda11-master @ 8522b06)'
    assert message.charset == 'UTF-8'
    assert 'An error happened when processing your push' in message.Body
