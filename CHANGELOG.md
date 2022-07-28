# 1.11.0 (2022-07-28)

* The code has been updated to Python 3.10, including the Docker image.

# 1.10.2 (2022-07-27)

* Drop dependency to ``mailer``: this library no longer seems to be maintained, and is not installable in recent
  setuptools because it still uses the ``use_2to3`` option, which no longer exists in recent setuptools.

# 1.10.1 (2022-07-26)

* Fix error in Dockerfile: do not copy dummy `.env` file anymore, it needs to be supplied by the service running the container.

# 1.10.0 (2022-07-26)

* Changed the ``git/lfs`` option default to ``false``. Many hosting providers (GitHub included) charge LFS bandwidth
  usage, so it is common to use some kind of proxy to cache LFS files. Another reason is that ``false`` is the
  plugin default.

# 1.9.1 (2022-07-13)

* Fix bug where options for the ``git:`` setting were not being honored when set to ``false``.

# 1.9.0 (2022-07-08)

* Add support for GitHub build status notification with the `notify_github` option.

# 1.8.0 (2022-05-04)

* Split test dependencies into its own `dev` extra category (`pip install .[dev]` for example).
* Fixed handling of branch deletions and job updates in `/github`.
* The `GH_SECRET` has been renamed to `GH_WEBHOOK_SECRET` to make its purpose clearer.
* The `GH_USERNAME` setting is no longer used/needed.

# 1.7.1 (2022-04-27)

* Properly interpret the content type/mimedata of POST events.

# 1.7.0 (2022-04-26)

* The `/github` end-point now **requires** the webhook to be configured with a *secret*, which is known to JobsDone via the `JD_GH_SECRET` configuration variable.
* Tests have been moved to `tests`, outside the `src` directory. This avoids installing test-related files when using the package.

# 1.6.1 (2022-04-25)

* Add dependency to `gunicorn`, which was missing for deployment.

# 1.6.0 (2022-04-25)

* Server now understands GitHub pushes at the `/github` end-point.
* Server now understands Stash pushes also at the `/stash` end-point. Posting Stash pushes at `/` still works, but
  might be removed in the future.

# 1.5.0 (2021-11-11)

* New `tags` configuration added to Git, controlling if should fetch all tags or not during cloning. Default to `false`.

# 1.4.2 (2021-11-10)

* Fixed deploy to PyPI procedure.

# 1.4.0 (2021-10-14)

* Build commands (shell, batch, python) now flatten their lists allowing the use of references (#33).

# 1.3.1 (2021-09-10)

* Remove usage of xml.ElementTree.Element.getchildren for Python 3.9 compatibility.
* Use setuptools\_scm version for --version.

# 1.3.0 (2021-09-03)

* Revert parsable option `auto-updater`.
* Update generated XML for xUnit plugin to support most recent version.

# 1.2.2 (2019-09-11)

* Production version now logs to stdout.
* Refactor internal layout of Server app.

# 1.2.1 (2019-09-11)

* No code changes. Just build scripts

# 1.2.0 (2019-09-11)

* Add new parsable option `auto-updater`.

# 1.1.1 (2018-08-31)

* Drop unnecessary dependency to `jenkins-webapi`.

# 1.1.0 (2018-06-27)

- Now an empty JSON post will respond with 200 and the jobs_done10 version as plain text, instead of an error.

# 1.0.4 (2018-06-26)

- First release.
