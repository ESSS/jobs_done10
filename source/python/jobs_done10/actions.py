


#===================================================================================================
# BuildJobsInDirectory
#===================================================================================================
def BuildJobsInDirectory(builder, directory='.', progress_callback=None):
    '''
    Using the given builder, extract repository information and look for JobsDoneFiles in the given
    `directory`.

    :param IJobBuilder builder:
        Builder used to generate jobs

    :param str directory:
        Base directory of a git repository containing jobs_done files.

    :param callable progress_callback:
        Function called for each JobsDoneFile found in `directory` before it is processed.
    '''
    from jobs_done10.jobs_done_file import JobsDoneFile, JOBS_DONE_FILE_PATTERN
    from jobs_done10.job_builder import JobBuilderConfigurator
    from jobs_done10.repository import Repository
    from sharedscripts10.shared_scripts.git_ import Git

    git = Git()
    repository = Repository(
        url=git.GetRemoteUrl(repo_path=directory),
        branch=git.GetCurrentBranch(repo_path=directory)
    )

    from ben10.filesystem import FindFiles
    jobs_done_files = FindFiles(
        directory,
        in_filters=[JOBS_DONE_FILE_PATTERN],
        recursive=False,
        standard_paths=True,
    )
    if not jobs_done_files:
        raise RuntimeError('Found no files in cwd that match "%s"' % JOBS_DONE_FILE_PATTERN)

    for jobs_done_filename in jobs_done_files:
        if progress_callback:
            progress_callback(jobs_done_filename)

        jobs_done_file = JobsDoneFile.CreateFromFile(jobs_done_filename)
        JobBuilderConfigurator.Configure(builder, jobs_done_file, repository)
        builder.Build()



#===================================================================================================
# BuildJobsFromFiles
#===================================================================================================
def BuildJobsFromFiles(builder, repository, jobs_done_file_contents):
    '''
    Builds jobs from a list of jobs_done file contents.

    :param IJobBuilder builder:
        Builder used to generate jobs

    :param repository:
        .. seealso:: JobBuilderConfigurator.Configure

    :param list(str) jobs_done_file_contents:
        List of .jobs_done file contents (each list member is the contents of a .jobs_done file)
    '''
    from jobs_done10.jobs_done_file import JobsDoneFile
    from jobs_done10.job_builder import JobBuilderConfigurator

    for jd_content in jobs_done_file_contents:
        jobs_done_file = JobsDoneFile.CreateFromYAML(jd_content)
        JobBuilderConfigurator.Configure(builder, jobs_done_file, repository)
        builder.Build()
