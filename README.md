Job's Done
===========

[![link](https://img.shields.io/pypi/v/jobs_done10.svg)](https://pypi.org/project/jobs_done10)
[![link](https://img.shields.io/pypi/pyversions/jobs_done10.svg)](https://pypi.org/project/jobs_done10)
[![link](https://github.com/ESSS/jobs_done10/workflows/tests/badge.svg)](https://github.com/ESSS/jobs_done10/actions)
[![link](https://img.shields.io/github/license/ESSS/jobs_done10.svg)](https://img.shields.io/github/license/ESSS/jobs_done10.svg)

# About #

Job's Done is a tool heavily inspired by [Travis](https://travis-ci.org/), and works in the same way
in that configuring a `.jobs_done.yaml` file in your repository's root to create and trigger Continuous Integration jobs.

Example of a `.jobs_done.yaml` file:

```yaml
matrix:
  platform:
  - "win64"
  - "redhat64"

platform-win64:build_batch_commands:
- |
  python -m venv .env3   || goto eof
  call .env3\Scripts\activate   || goto eof
  pytest --junitxml=tests-{platform}.xml

platform-redhat64:build_shell_commands:
- |
  python3 -m venv .env3
  source .env3/bin/activate
  pytest --junitxml=tests-{platform}.xml

junit_patterns:
- "tests.*.xml"
```

Considering this file is in the root of repository `myproject` and was pushed to branch `feat-71`, this will generate two Jenkins jobs:

* `myproject-feat-71-win64`
* `myproject-feat-71-linux64`


## Command-line ###

Jobs done can be executed in the command-line.

To use it, from the repository's folder that you want to create jobs for, execute:

```console
$ jobs_done jenkins --username USER https://example.com/jenkins
```

This will create/update existing jobs.

Below are the possible installation options.

### PyPI ###

1. Create a virtual environment using Python 3 and activate it:

   ```console
   $ python -m venv .env
   $ .env\Scripts\activate  # Windows
   $ source .env/bin/activate  # Linux
   ```

3. Install jobs_done10:

   ```console
   $ pip install jobs_done10
   ```

### Development ###

1. Clone the repository:

   ```console
   git clone git@github.com:ESSS/jobs_done10.git
   cd jobs_done10
   ```

2. Create a virtual environment using Python 3 and activate it:

   ```console
   $ python -m venv .env
   $ .env\Scripts\activate  # Windows
   $ source .env/bin/activate  # Linux
   ```

3. We need to downgrade `setuptools` because the `mailer` package won't install in
   the latest `setuptools` versions (it uses the removed `use_2to3` argument to `setup`):

   ```console
   $ pip install "setuptools<58"
   ```

4. Install dependencies and the project in editable mode:

   ```console
   $ pip install -r requirements.txt -e .
   ```


#### Upgrading dependencies

We use [pip-tools](https://pypi.org/project/pip-tools) to pin versions, follow the instructions in the
docs to add new libraries or update existing versions, adding `--extra dev` to include development dependencies.


## Server ##

jobs done includes a `flask` server in `jobs_done10.server` which can be deployed using [Docker](https://www.docker.com/).

It provides two end-points for `PUSH` and `GET`:

* `/stash`: tailored to receive the push event from BitBucket Server (formerly known as Stash).
* `/github`: tailored to receive the push event from GitHub. **Important**: the webhook must be configured with content-type of `application/json` and a **secret**.

A `GET` to either ends points will return the JobsDone version, useful to check the installed version and
that the end-point is correct.

Posting to `/` is the same as posting to `/stash` for backwards compatibility (might be removed in the future).

### Configuration ###

Configuration is done by having a `.env` file (cortesy of [python-dotenv](https://github.com/theskumar/python-dotenv))
in the root of this repository with the following variables:

```ini
JD_JENKINS_URL=https://example.com/jenkins
JD_JENKINS_USERNAME=jenkins-user
JD_JENKINS_PASSWORD=some password

JD_STASH_URL=https://example.com/stash
JD_STASH_USERNAME=stash-user
JD_STASH_PASSWORD=some password

JD_GH_TOKEN=github-user-personal-access-token
JD_GH_WEBHOOK_SECRET=webhook-secret

JD_EMAIL_USER=mail-sender@example.com
JD_EMAIL_FROM=JobsDone Bot <mail-sender@example.com>
JD_EMAIL_PASSWORD=email password
JD_EMAIL_SERVER=smtp.example.com
JD_EMAIL_PORT=587
```

### Build ###

Clone the repository and checkout the tag:

```console
$ git clone https://github.com/ESSS/jobs_done10.git
$ cd jobs_done10
$ git checkout <VERSION>
```

Build a docker image:

```console
$ docker build . --tag jobsdone:<VERSION> --build-arg SETUPTOOLS_SCM_PRETEND_VERSION=<VERSION>
```

### Run server ###

```console
$ docker run --publish 5000:5000 jobsdone:<VERSION>
```

# Hello World #

This is an example of a Job's Done file, and what you might expect of its contents.

```yaml
build_batch_commands:
- "echo MESSAGE: Hello, world!"

description_regex: "MESSAGE\\:(.*)"
```

Adding this file to a repository hooked into our CI system will create a single job that when executed run a
Windows batch command, and later on catches the message echoed and sets that as the build description.


# Tests #

This is an example of a simple application with tests:

```yaml

build_batch_commands:
- "pytest --junitxml=pytest_results.xml"

junit_patterns:
- "pytest_results.xml"
```

This jobs runs pytest in the repository and outputs test results to a file. We also configure the job to look for that
file, and present test results to us at then end of the build.

# Multiple platforms #


The same application as above, but now running on multiple platforms.

```yaml

platform-win64:build_batch_commands:
- "pytest --junitxml=pytest_results-{platform}.xml"

platform-redhat64:build_shell_commands:
- "pytest --junitxml=pytest_results-{platform}.xml"

junit_patterns:
- "pytest_results.*.xml"

matrix:
  platform:
  - "win64"
  - "redhat64"
```

Here we add a **matrix** section to define variations of this job. In this case, we have the platform variable,
with two possible values, `win64` and `redhat64`.

One job will be created for each possible combination in the matrix (only two jobs in this case).

Since we can't run batch commands in linux, we add another builder section, `build_shell_commands`. Using some flags
before defining sections we can choose which one will be available in each job.

Values from the matrix can also be used as variables, in this case, `{platform}` will be replaced by the platform used
in that job (`win64` or `redhat64`).


## Branch patterns ##

Branch patterns are used to filter which branches will produce jobs. This list of regular expressions
(using Python syntax), ensures that a branch will only produce jobs if at least one of the regular
expressions matches the name of the branch.

Here's an example that filter only `master` and feature branches:

```yaml

branch_patterns:
- "master"
- "fb-*"
```

If this section is not defined in the file, all branches will produce jobs.

## Job Matrix ##

As shown in the examples above, the job matrix can be used to create multiple variations of a job.
One job for each combination of entries in this matrix is created.

```yaml
matrix:
  mode:
  - "app"
  - "cases"
  platform:
  - "win64"
  - "linux64"
```

In this case 4 jobs will be generated:

* `app-win64`
* `app-linux64`
* `cases-win64`
* `cases-linux64`

Note that you can use any variables you need, Job's done has no idea what `mode` or `platform` means.

There's an `exclude` clause which can be used to remove particular entries from the matrix:


```yaml
matrix:
  mode:
  - "app"
  - "cases"
  platform:
  - "win64"
  - "linux64"

mode-cases:platform-win.*:exclude: "yes"
```

This will exclude all cases jobs from windows.

## String replacement ##

Variables defined in the job matrix can be used to replace strings in the job file.

On top of matrix variables, there are a few special string templates that can be used in any job:

* `name` - Name of the repository
* `branch` - Branch being built


```yaml
matrix:
  platform:
  - "win64"
  - "linux64"

platform-win.*:build_batch_commands:
- "echo Building project {name} in branch {branch} on platform {platform}"
```

Note that we use Python's format syntax, so if you need an actual `{` or `}` use double braces: `{{`, `}}`.


## Condition Flags ##

Variables defined in your job matrix can also be used to control some of the contents in your job file.
A common example here is using different builder for windows (bash) and linux (shell).

This is done by adding a prefix to sections of the YAML file, with the variable name and value necessary to use it:

```yaml
platform-win.*:build_batch_commands:
- "dir ."

platform-linux.*:build_shell_commands:
- "ls -la ."

matrix:
  platform:
  - "win32"
  - "linux64"
```

Matrix variables can also define aliases, useful to reduce duplication when using such flags.
To add aliases, simply use commas to separate additional names for matrix values:

```yaml
platform-windows:build_batch_commands:
- "dir ."

platform-linux:build_shell_commands:
- "ls -la ."

matrix:
  platform:
  - "win32,windows"
  - "win64,windows"
  - "linux64,linux"
```

On top of that you can use a special variable `branch` that's always available, and points to your branch:

```yaml
branch-master:build_batch_commands:
- "echo Build"

branch-deploy:build_batch_commands:
- "echo Build + Deploy"
```

Condition values can use Python regex syntax for extra flexibility:

```yaml
branch-master:build_batch_commands:
- "echo Build"

branch-fb.*:build_batch_commands:
- "echo Feature branch!"

branch-rb.*:build_batch_commands:
- "echo Release branch!"
```

# Development #

Create a virtual environment and install it in development mode:

```console
$ python -m virtualenv .env36
$ source .env36/bin/activate
$ pip install -e .
```

Run tests:

```console
$ pytest src
```

## Deploy to PyPI ##

Jobs done can be deployed to PyPI. Open a PR updating the CHANGELOG and after it passes, push a tag to the repository;
Travis will see the tag and publish the package to PyPI automatically.

## Deploy at ESSS ##

There's a job in Jenkins: `jobs_done10-deploy-main`. It takes the tag version to be deployed.

# All options #

### additional_repositories ###

Additional repositories to be checked out in this job.

The repository where this .jobs_done file is included by default.

Requires [Multiple SCMs Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Multiple+SCMs+Plugin) and [Git Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Git+Plugin).

Uses same options as `git`.

```yaml
additional_repositories:
- git:
    url: "https://project.git"
    branch: "{branch}"
```

### auth_token ###

Job authentication token required to triggers builds remotely.

```yaml
auth_token: "my_token"
```

### boosttest_patterns ###

List of boosttest file patterns to look for test results.

Requires the [xUnit Plugin](https://wiki.jenkins-ci.org/display/JENKINS/xUnit+Plugin).

```yaml
boosttest_patterns:
- "*.xml"
```


### branch_patterns ###

List of regexes used to match branch names.
Only branches that match one of these will create
jobs.

```yaml
branch_patterns:
- "master"
- "fb-*"
```

### build_batch_commands ###
List of Windows batch commands used to build the job.
If errorcode is not 0 after any command, the build fails.

```yaml
build_batch_commands:
- "pytest src"
- "echo Finished"
```

### build_shell_commands ###

List of shell commands used to build the job.
If errorcode is not 0 after any command, the build fails.

```yaml
build_shell_commands:
- "pytest src"
- "echo Finished"
```

### build_python_commands ###

List of python commands used to build the job.

Requires [Python Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Python+Plugin).

```yaml
build_python_commands:
- "print(5)"
```

### console_color ###

Enable support for ANSI escape sequences, including color, to Console Output.

Requires [AnsiColor Plugin](https://wiki.jenkins-ci.org/display/JENKINS/AnsiColor+Plugin).

Accepted values:
* `xterm` (default)
* `vga`
* `css`
* `gnome-terminal`

```yaml
console_color: "css"
```

### coverage ###


Enables code coverage report.

Require [Cobertura Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Cobertura+Plugin).

Options:

* `report_pattern`: mandatory, pattern where XML coverage files are searched. These XML files are usually in
  [Cobertura](http://cobertura.github.io/cobertura) format, which is also format by
  [pytest-cov](https://pypi.python.org/pypi/pytest-cov) XML output (because pytest-cov uses coverage library).
* `healthy`: optional, specifies desired method, line and conditional metric. Any omitted metric defaults to `80`.
* `unhealthy`: optional, specifies desired method, line and conditional metric. Any omitted metric defaults to `0`. Builds below these thresholds are marked as unhealthy.
* `failing`: optional, specifies desired method, line and conditional metric. Any omitted metric defaults to `0`. Builds below these thresholds are marked as failed.

```yaml
coverage:
  report_pattern: "**/build/coverage/*.xml"
  healthy:
    method: 100
    line: 100
    conditional: 90
  unhealthy:
    method: 95
    line: 95
    conditional: 85
  failing:
    method: 90
    line: 90
    conditional: 80
```

### cron ###

Schedules to build to run periodically.

```yaml
cron: |
  # Everyday at 22pm
  * 22 * * *
```

### custom_workspace ###

Defines a custom workspace directory for the job. To maintain the same base directory as the default workspace directories prefix it with `"workspace/"`.

```yaml
custom_workspace: "workspace/devspace-user"
```

### description_regex ###

Regular expression for searching job output for a description.
If a match is found, the contents of the first group will be set as the description.

Requires [Description Setter Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Description+Setter+Plugin).

```yaml
description_regex: "OUTPUT: (.*)"
```

### display_name ###

Configures the display name of the job.

```yaml
display_name: "{branch} {name}"
```

### email_notification ###

Sends emails for failed builds.

```yaml
email_notification: "email1@example.com email2@example.com"

# or

email_notification:
  recipients: "email1@example.com email2@example.com"
  notify_every_build: true
  notify_individuals: true
```

### exclude ###

Excludes a job from the matrix.

```yaml
platform-linux64:exclude: "yes"
```

### git ###

Additional git options for the main project.

Requires [Git Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Git+Plugin).

Options available here are shared with `additional_repositories`.

```yaml
git:
  branch: master
  clean_checkout: false
  lfs: true
  recursive_submodules: true
  reference: "/home/reference.git"
  shallow_clone: 50
  tags: true
  target_dir: "main_application"
  timeout: 30
  url: "ssh://server/somerepo.git"
```

Note: by default, `tags` is `false` because we noticed that fetching tags takes quite some time and
we don't use tags for anything. If tags are needed, set `tags` to `true`.

### jsunit_patterns ###

List of jsunit file patterns to look for test results.

Requires [JSUnit Plugin](https://wiki.jenkins-ci.org/display/JENKINS/JSUnit+plugin).

```yaml
jsunit_patterns:
- "*.xml"
```

### junit_patterns ###

List of junit file patterns to look for test results.

Requires [xUnit Plugin](https://wiki.jenkins-ci.org/display/JENKINS/xUnit+Plugin).

```yaml
junit_patterns:
- "*.xml"
```

### label_expression ###

Configures the label expression of the job.

The label-expression is used to determine which workers can run the job.

```yaml
label_expression: "{platform}"
```

### matrix ###

Configures variations of a job.

```yaml
matrix:
  python:
  - "27"
  - "36"
```

### notify_stash ###

Notifies a Stash instance when the build passes.

When no parameters are given, uses configurations set in the Jenkins instance.

Requires [StashNotifier Plugin](https://wiki.jenkins-ci.org/display/JENKINS/StashNotifier+Plugin).

```yaml
notify_stash:
  url: "example.com/stash"
  username: "user"
  password: "pass"

# Using default from Jenkins
notify_stash:
```

### parameters ###

Job parameters for Jenkins jobs.

Currently, only `choice` and `string` are implemented.

```yaml
parameters:
  - choice:
      name: "PARAM_BIRD"
      choices:
        - "African"
        - "European"
      description: "Area where the bird is from"
  - string:
      name: "PARAM_VERSION"
      default: "dev"
      description: "App version"
```

### scm_poll ###

Schedules to periodically poll SCM for changes, and trigger builds.

```yaml
scm_poll: |
  # Everyday at 22pm
  * 22 * * *
```

### slack ###

Configure notification with slack.

1. Configure your Jenkins integration on Slack
2. Obtain the token
3. Configure your job to notify slack using this option.

```yaml
slack:
  team: esss
  channel: dev
  token: XXX
  url: https://example.com/jenkins
```

### timeout ###

Job timeout in minutes.

```yaml
timeout: 60
```

### timestamps ###

Show timestamps on the left side of the console output.

Requires the [Timestamper Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Timestamper).

```yaml
timestamps:
```

### trigger_jobs ###

Trigger other jobs after the current job finishes. Parameters are optional.

```yaml
trigger_jobs:
  names:
    - myrepo-{branch}-synthetic-{platform}
  condition: SUCCESS  # can be one of: SUCCESS, UNSTABLE, FAILED, ALWAYS. Defaults to SUCCESS.
  parameters:  # optional
    - PARAM1=VALUE1
    - PARAM2=VALUE2
```

### warnings ###

Configures parsing of warnings and static analysis in a CI job.

Requires [Warnings Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Warnings+Plugin).

```yaml
warnings:
  console:
    - parser: Clang (LLCM based)
    - parser: PyLint
  file:
    - parser: CppLint
      file_pattern: *.cpplint
    - parser: CodeAnalysis
      file_pattern: *.codeanalysis
```
