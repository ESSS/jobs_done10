


#===================================================================================================
# BuildJobsInDirectory
#===================================================================================================
def BuildJobsInDirectory(builder, directory='.'):
    '''
    Using the given builder, extract repository information and look for a jobs_done file in the
    given `directory`.

    :param IJobBuilder builder:
        Builder used to generate jobs

    :param str directory:
        Base directory of a git repository containing a jobs_done file.
    '''
    from ben10.filesystem import GetFileContents
    from jobs_done10.jobs_done_file import JOBS_DONE_FILENAME
    from jobs_done10.repository import Repository
    from sharedscripts10.shared_scripts.git_ import Git
    import os

    git = Git()
    repository = Repository(
        url=git.GetRemoteUrl(repo_path=directory),
        branch=git.GetCurrentBranch(repo_path=directory)
    )

    jobs_done_file_contents = GetFileContents(os.path.join(directory, JOBS_DONE_FILENAME))
    return BuildJobsFromFile(builder, repository, jobs_done_file_contents)



#===================================================================================================
# BuildJobsFromFile
#===================================================================================================
def BuildJobsFromFile(builder, repository, jobs_done_file_contents):
    '''
    Builds jobs from a jobs_done file's contents.

    :param IJobBuilder builder:
        Builder used to generate jobs

    :param repository:
        .. seealso:: JobBuilderConfigurator.Configure

    :param str jobs_done_file_contents:
        Contents of a .jobs_done
    '''
    from jobs_done10.jobs_done_file import JobsDoneFile
    from jobs_done10.job_builder import JobBuilderConfigurator

    jobs_done_files = JobsDoneFile.CreateFromYAML(jobs_done_file_contents)

    for jobs_done_file in jobs_done_files:
        JobBuilderConfigurator.Configure(builder, jobs_done_file, repository)
        builder.Build()
