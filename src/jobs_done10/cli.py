import click


@click.command()
@click.argument("url")
@click.option("--username", prompt=True, help="Jenkins username.")
@click.option("--password", prompt=True, hide_input=True, help="Jenkins password.")
def jenkins(url, username=None, password=None):
    """
    Push jobs to Jenkins instance.

    The targeted Jenkins instance is identified by it's URL.
    """
    from jobs_done10.generators.jenkins import GetJobsFromDirectory, JenkinsJobPublisher

    click.secho("Publishing jobs in ", nl=False)
    click.secho(url, fg="white")

    repository, jobs = GetJobsFromDirectory()
    publisher = JenkinsJobPublisher(repository, jobs)
    new_jobs, updated_jobs, deleted_jobs = publisher.PublishToUrl(
        url, username, password
    )

    for job in new_jobs:
        click.secho("NEW", fg="green", nl=False)
        click.secho(" - ", nl=False)
        click.secho(job)
    for job in updated_jobs:
        click.secho("UPD", fg="yellow", nl=False)
        click.secho(" - ", nl=False)
        click.secho(job)
    for job in deleted_jobs:
        click.secho("DEL", fg="red", nl=False)
        click.secho(" - ", nl=False)
        click.secho(job)


@click.command()
@click.argument("output_directory")
def jenkins_test(output_directory):
    """
    Save the resulting '.xml's in a directory.
    """
    from jobs_done10.generators.jenkins import GetJobsFromDirectory, JenkinsJobPublisher

    click.secho('Saving jobs in "%s"' % output_directory)

    repository, jobs = GetJobsFromDirectory()
    publisher = JenkinsJobPublisher(repository, jobs)
    publisher.PublishToDirectory(output_directory)

    click.secho("OK", fg="green")


try:
    from ._version import version
except ImportError:
    version = "DEV"


@click.group(name="jobs_done10")
@click.version_option(version=version)
def jobs_done():
    """
    Creates jobs for Jenkins.
    """


jobs_done.add_command(jenkins)
jobs_done.add_command(jenkins_test)
