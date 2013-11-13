


#===================================================================================================
# BuildJobsInDirectory
#===================================================================================================
def BuildJobsInDirectory(builder, directory='.', progress_callback=None):
    '''
    Using the given builder, extract repository information and look for CIFiles in the given
    `directory`.
    
    :param IJobBuilder builder:
        Builder used to generate jobs
    
    :param str directory:
        Base directory of a git repository containing jobs_done files.
    
    :param callable progress_callback:
        Function called for each CIFile found in `directory` before it is processed.
    '''
    from jobs_done10.ci_file import CIFile
    from jobs_done10.job_builder import JobBuilderConfigurator
    from jobs_done10.repository import Repository
    from sharedscripts10.shared_scripts.git_ import Git

    git = Git()
    repository = Repository(
        url=git.GetRemoteUrl(repo_path=directory),
        branch=git.GetCurrentBranch(repo_path=directory)
    )

    from ben10.filesystem import FindFiles
    ci_files = FindFiles(
        directory,
        in_filters=['*.jd.yaml'],
        recursive=False,
        standard_paths=True,
    )
    if not ci_files:
        raise RuntimeError('Found no files in cwd that match "*.jd.yaml"')

    for ci_filename in ci_files:
        if progress_callback:
            progress_callback(ci_filename)

        ci_file = CIFile.CreateFromFile(ci_filename)
        JobBuilderConfigurator.Configure(builder, ci_file, repository)
        builder.Build()
