'''
This module is a copy of Git from sharedscripts10.

It was copied here to remove dependencies to that project, and should be removed once that code
is refactored into an open-source project.

All classes have "pragma: no cover" because we didn't copy tests for this class.

TODO: CI-123 Refactor Git code out of sharedscripts10
'''



#===================================================================================================
# Git
#===================================================================================================
class Git(object):  # pragma: no cover (see module docs)

    # Constants for common refs
    ZERO_REVISION = '0' * 40

    def Execute(self, command_line, repo_path=None, flat_output=False):
        '''
        Executes a git command line in the given repository.

        :param list(str) command_line:
            List of commands to execute, not including 'git' as the first.

        :type repo_path: str | None
        :param repo_path:
            Path to repository where the command will be executed (without .git)

            If None, runs command in current directory (useful for clone, for example)

        :param bool flat_output:
            If True, joins the output lines with '\n' (returning a single string)

        :rtype: list(str) | str
        :returns:
            List of lines output from git command, or the complete output if parameter flat_output
            is True

        :raises GitExecuteError:
            If the git executable returns an error code
        '''
        command_line = ['git'] + command_line

        from ben10.filesystem import Cwd
        with Cwd(repo_path):
            import subprocess
            popen = subprocess.Popen(
                command_line,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )

        try:
            output = popen.stdout.read().splitlines()
        finally:
            popen.stdout.close()

        popen.wait()

        if popen.returncode != 0:
            raise GitExecuteError(' '.join(command_line), popen.returncode, '\n'.join(output))

        if flat_output:
            return '\n'.join(output)

        return output


    def Status(self, repo_path, flags=['--branch', '--short'], flat_output=True, source_dir='.'):
        '''
        :param str repo_path:
            Path to the repository (local)

        :param list(str) flags:
            List of additional flags given to status.
            Defaults to --branch and --short

        :param bool flat_output:
            .. seealso:: self.Execute

        :param str source_dir:
            Directory (relative to repo_path) where status will be executed.

        :returns str:
            Output from git status with the given flags
        '''
        return self.Execute(['status', source_dir] + flags, repo_path, flat_output=flat_output)


    def IsDirty(self, repo_path):
        '''
        :param str repo_path:
            Path to the repository (local)

        @return bool
            If the repository is dirty (has changes that weren't commited yet).

        @note:
            Ignores untracked files
        '''
        return len(self.GetDirtyFiles(repo_path)) > 0


    def Add(self, repo_path, filename):
        '''
        Adds a filename to a repository's staged changes.

        :param str repo_path:

        :param str filename:
        '''
        self.Execute(['add', filename], repo_path)


    def Commit(self, repo_path, commit_message, flags=[]):
        '''
        Commits staged changes in a repository

        :param str repo_path:

        :param str commit_message:
        '''
        self.Execute(['commit', '-m', commit_message] + flags, repo_path)


    def GetCurrentBranch(self, repo_path):
        '''
        :param  repo_path:
            Path to the repository (local)

        :rtype: str or None
        :returns:
            The name of the current branch.

        @raise: NotCurrentlyInAnyBranchError
            If not on any branch.
        '''
        branches = self.Execute(['branch'], repo_path)

        for branch in branches:
            if '*' in branch:  # Current branch
                current_branch = branch.split(' ', 1)[1]
                break
        else:
            raise RuntimeError('Error parsing output from git branch')

        # The comment differns depending on Git version. The text "(no branch)' was used before version 1.8.3
        if current_branch == '(no branch)' or current_branch.startswith('(detached from'):
            raise NotCurrentlyInAnyBranchError(repo_path)

        return current_branch


    def GetRemoteUrl(self, repo_path, remote_name='origin'):
        '''
        Returns the url associated with a remote in a git repository.

        :param str repo_path:
            Path to the repository (local)

        :param str remote_name:
            The remote name.

        :rtype: str
        :returns:
            The url of the remote.
        '''
        return self.Execute(
            ['config', '--local', '--get', 'remote.%s.url' % remote_name],
            repo_path,
            flat_output=True,
        )


    def AddRemote(self, repo_path, remote_name, remote_url):
        '''
        Add a remote in a git repository.

        :param str repo_path:
            Path to the repository (local)

        :param str remote_name:
            The (new) remote name.

        :param str remote_url:
            The (new) remote url.
        '''
        self.Execute(
            ['remote', 'add', remote_name, remote_url],
            repo_path,
            flat_output=True,
        )


    def GetDirtyFiles(self, repo_path, source_dir='.'):
        '''
        Returns modified files from a repository (ignores untracked files).
        Parses output from git status to obtain this information.

        :param str repo_path:
            Path to the repository (local)

        :param str source_dir:
            .. seealso:: Git.Status

        :rtype: list(tuple(str,str))
        :returns:
            List of (status, path) of modified files in a repository
        '''
        status = self.Status(
            repo_path,
            flags=['--porcelain'],
            flat_output=False,
            source_dir=source_dir,
        )

        def ExtractFileStatus(line):
            # Strip lines
            line = line.strip()

            # Split at first whitespaces
            import re
            return re.search('(\S*)\s+(\S*)', line).groups()

        result = map(ExtractFileStatus, status)

        # Ignore untracked files ('??')
        result = [i for i in result if i[0] != '??']

        return result


    def CreateLocalBranch(self, repo_path, branch_name):
        '''
        Creates a new local branch, and stays in it.
        Equivalent to 'git checkout -b branch_name'

        :param str repo_path:
            Path to the repository (local)

        :param str branch_name:
            The name of the branch to be created.

        :raises DirtyRepositoryError:
            .. seealso:: DirtyRepositoryError

        :raises BranchAlreadyExistsError:
            .. seealso:: BranchAlreadyExistsError
        '''
        if self.IsDirty(repo_path):
            raise DirtyRepositoryError(repo_path)

        try:
            # Create the new branch
            self.Execute(['checkout', '-b', branch_name], repo_path)
        except GitExecuteError, e:
            if 'already exists' in e.git_msg:
                raise BranchAlreadyExistsError(branch_name)
            raise



#===================================================================================================
# GitExecuteError
#===================================================================================================
class GitExecuteError(RuntimeError):  # pragma: no cover (see module docs)
    '''
    Raised when running the git executable returns anything other than 0.
    '''
    def __init__(self, command, retcode, git_msg):
        self.command = command
        self.retcode = retcode
        self.git_msg = git_msg

        RuntimeError.__init__(
            self,
            'Command "%(command)s" returned with error %(retcode)s\n\n' % locals() + \
            'Output from git:\n\n' + git_msg
        )



#===================================================================================================
# DirtyRepositoryError
#===================================================================================================
class DirtyRepositoryError(Exception):  # pragma: no cover (see module docs)
    '''
    Raised when trying to perform some operations in a dirty (uncommited changes) repository.
    '''
    def __init__(self, repo_path):
        Exception.__init__(self, 'Repository at "%s" is dirty.' % repo_path)
        self.repo = repo_path



#===================================================================================================
# BranchAlreadyExistsError
#===================================================================================================
class BranchAlreadyExistsError(Exception):  # pragma: no cover (see module docs)
    '''
    Raised when trying to create a branch that already exists.
    '''
    def __init__(self, branch_name):
        Exception.__init__(self, 'Branch "%s" already exists.' % branch_name)
        self.branch = branch_name



#===================================================================================================
# NotCurrentlyInAnyBranchError
#===================================================================================================
class NotCurrentlyInAnyBranchError(Exception):  # pragma: no cover (see module docs)
    '''
    Raised when operating while not on any branch (headless state)
    '''
    def __init__(self, repo_path):
        Exception.__init__(self, 'Repository "%s" is not currently on any branch.' % repo_path)
        self.repo_path = repo_path
