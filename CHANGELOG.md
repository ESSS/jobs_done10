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
