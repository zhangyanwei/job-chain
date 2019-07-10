import re
import subprocess
import urllib.parse
from typing import Callable

from ._executor import Executor
from ..logger import logger


class Repository:
    def __init__(self, executor: Executor, directory: str):
        """
        the directory of workspace, can be a relative path against the current work directory.

        Args:
            executor (_Executor): executor for git
            directory (str): directory name or path
        """
        self._executor = executor
        self._directory = executor.abspath(directory)
        self._branch = None

    def init(self, url: str, user: str = None, password: str = None, branch: str = None, reset: bool = True,
             *, email: str = None, name: str = None):
        """
        initialize the repository in directory (specified by "directory" parameter of constructor)

        Args:
            url (str): repository url
            user (str): user name for git authentication
            password (str): password for git authentication
            branch (str): branch name if you want check it out.
            reset (bool): reset the branch status if true
            email (str): email address for git configuration
            name (str): representation name for git configuration
        """
        logger.info(f'Initialize the repository "{url}" in directory "{self._directory}".')
        self._branch = branch
        if not self._executor.path_exists(self._directory):
            auth_prefix = ''
            if user:
                password = password and f':{urllib.parse.quote(password)}'
                auth_prefix += f'{user}{password}@'
            url = re.sub(r'(\w+://)(.+)', f'\\1{auth_prefix}\\2', str(url))
            logger.info(f'Clone the remote repository "{url}".')
            self._execute(f'clone {url} {self._directory}', cwd=None)
            if email is not None:
                self._execute(f'config user.email "{email}"', cwd=None)
            if name is not None:
                self._execute(f'config user.name "{name}"', cwd=None)
        self._execute('fetch')
        if branch:
            if reset:
                logger.info(f'Check out the branch "{branch}" to the latest status. (will drop the uncommit changes)')
                self.reset(branch)
            else:
                self.checkout(branch)

    @property
    def directory(self):
        return self._directory

    def abspath(self, subpath):
        return self._executor.abspath(self._directory, subpath)

    def diff(self, branch=None):
        b = branch or self._branch
        self._check_out(b)
        return self._execute(f'diff --name-only origin/{b}', stdout=subprocess.PIPE, encoding='UTF-8').stdout

    def local_diff(self, unstaged_pattern: str = None):
        if unstaged_pattern is not None:
            self._execute(f'add --all {unstaged_pattern}')
        diff = self._execute(f'diff HEAD --name-only', stdout=subprocess.PIPE, encoding='UTF-8').stdout
        # reset the "add" command.
        self._execute(f'reset')
        return diff

    def reset(self, branch=None):
        b = branch or self._branch
        self._check_out(b, True)
        self._execute(f'reset --hard origin/{b}')

    def checkout(self, branch=None, force: bool = False):
        self._execute(f'checkout {"-f " if force else " "}{branch}')

    def commit(self, message, *patterns):
        self._commit(message, *patterns)

    def pull(self):
        self._execute('pull')

    def push(self):
        self._push(self._branch)

    def start_release(self, work_branch: str, release_branch: str,
                      verify: Callable[[], None] = None,
                      update_next_version: Callable[[], tuple] = None,
                      update_version: Callable[[str], tuple] = None,
                      force=False):
        # Check out the working branch
        self._execute(
            f'fetch --progress --prune --recurse-submodules=no origin refs/heads/{work_branch}:refs/remotes/origin/{work_branch}')
        self._execute(f'checkout -f {work_branch}')
        self._execute(f'reset --hard origin/{work_branch}')

        # Delete the release branch if the force option enabled.
        if force:
            logger.info(f'Remove release branch "{release_branch}" if already exists in force mode.')
            self._remove_branch(release_branch, remove_remote=True)
        if self._is_remote_branch_exists(release_branch):
            raise IOError(f'Remote release branch \'{release_branch}\' already exists.')

        # Verify the working branch
        if verify:
            logger.info(f'Verify the branch \'{work_branch}\'.')
            verify()

        # noinspection PyBroadException
        try:
            # Create the release branch
            self._execute(f'branch -f --no-track {release_branch} refs/heads/{work_branch}')
            # Update the next version on release branch
            if update_next_version:
                next_version, patterns = update_next_version()
                patterns and self._commit(
                    f'Update next version to \'{next_version}\' on the working branch \'{work_branch}\'.', *patterns)

            # Checkout the release branch
            self._execute(f'checkout -f {release_branch}')
            # Update the version on release branch
            if update_version:
                version, patterns = update_version()
                self._commit(f'Update version to \"{version}\" on the release branch.', *patterns)
        except Exception as err:
            logger.info(f'Remove release branch "{release_branch}", because error occurs: {err}.')
            self.reset(work_branch)
            self._remove_branch(release_branch)
            raise err

        # Push the changes, and let the local release branch upstream to the remote.
        self._push(work_branch)
        self._push(release_branch)
        self._execute(f'branch --set-upstream-to=origin/{release_branch} {release_branch}')

    def update_release(self, release_branch: str, verify: Callable[[], None] = None,
                       merge_into: str = None, merge_comment: str = None, merge_verify: Callable[[], None] = None):
        # 1. checkout and pull the release branch
        logger.info(f'Checkout and reset the release branch \'{release_branch}\' to the latest version.')
        self._execute(
            f'fetch --progress --prune --recurse-submodules=no origin refs/heads/{release_branch}:refs/remotes/origin/{release_branch}')
        self._execute(f'checkout -f {release_branch}')
        self._execute(f'reset --hard origin/{release_branch}')
        # 2. verify the release branch
        if verify:
            logger.info(f'Verify the release branch "{release_branch}".')
            verify()
        if merge_into:
            # 3. merge back
            logger.info(f'Merge the release branch \'{release_branch}\' into the branch \'{merge_into}\'.')
            self._execute(
                'fetch --progress --prune --recurse-submodules=no origin refs/heads/{merge_into}:refs/remotes/origin/{merge_into}')
            if not merge_comment:
                merge_comment = f'Merged the changes from the the release branch \'{release_branch}\'.'
            self._execute(f'checkout {merge_into}')
            self._execute(f'reset --hard origin/{merge_into}')
            self._execute(f'merge --no-ff -m "{merge_comment}"  -s recursive -X ours {release_branch}')
            # 4. verify the merged branch
            if merge_verify:
                logger.info(f'Verify the merged {merge_into} branch.')
                merge_verify()
            self._execute(
                f'push --porcelain --progress --recurse-submodules=check origin refs/heads/{merge_into}:refs/heads/{merge_into}')

            # Finally, switch the working branch to the release branch.
            self._execute(f'checkout {release_branch}')

    def finish_release(self, release_branch: str, merge_into: str,
                       release_comment: str = None, tag_name: str = None, verify: Callable[[], None] = None):
        # Check out the latest release branch.
        self._execute(
            f'fetch --progress --prune --recurse-submodules=no origin refs/heads/{release_branch}:refs/remotes/origin/{release_branch}')
        self._execute(f'checkout -f {release_branch}')
        self._execute(f'reset --hard origin/{release_branch}')

        # == actions on master branch ==
        # Check out the latest master branch.
        self._execute(
            'fetch --progress --prune --recurse-submodules=no origin refs/heads/master:refs/remotes/origin/master')
        self._execute('checkout -f master')
        self._execute('reset --hard origin/master')
        # Merge the release branch into the master branch.
        if not release_comment:
            release_comment = f'Release \'{release_branch}\'.'
        self._execute(f'merge --no-ff -m "{release_comment}" {release_branch}')
        # Create a tag on master branch
        if not tag_name:
            tag_name = release_branch
        self._execute(f'tag -f -m "{release_comment}" {tag_name} refs/heads/master')
        # Verify the merged code on the master branch.
        if verify:
            logger.info(f'verify the tagged version "{tag_name}" on master branch')
            verify()

        # == actions on the merging branch ==
        # Check out the latest target merge branch.
        self._execute(
            f'fetch --progress --prune --recurse-submodules=no origin refs/heads/{merge_into}:refs/remotes/origin/{merge_into}')
        self._execute(f'checkout -f {merge_into}')
        self._execute(f'reset --hard origin/{merge_into}')
        # Merge the release branch into the merging branch
        self._execute(f'merge --no-ff -m "{release_comment}"  -s recursive -X ours {release_branch}')

        # Delete the release branch
        self._execute(f'branch -D {release_branch}')

        # Finally, switch the working branch to master.
        self._execute('checkout master')

        # Push the changes into the remote repository.
        self._execute(
            'push --porcelain --progress --recurse-submodules=check origin refs/heads/master:refs/heads/master')
        self._execute(
            f'push --porcelain --progress --recurse-submodules=check origin refs/heads/{merge_into}:refs/heads/{merge_into}')
        self._execute(
            f'push --porcelain --progress --recurse-submodules=check origin refs/tags/{tag_name}:refs/tags/{tag_name}')
        self._execute(
            f'push --porcelain --progress --recurse-submodules=check origin :refs/heads/{release_branch}')

    def _remove_branch(self, branch, *, check=False, remove_remote: bool = False):
        self._execute(f'branch -D {branch}', check=check)
        if remove_remote:
            self._execute(f'branch -D -r origin/{branch}', check=check)
            self._execute(f'push --porcelain --progress --recurse-submodules=check origin :refs/heads/{branch}',
                          check=check)

    def _is_remote_branch_exists(self, branch):
        matched = re.search(r'\sorigin/+{}\n'.format(branch),
                            self._execute('branch -r', stdout=subprocess.PIPE, encoding='UTF-8').stdout)
        return matched is not None

    def _is_branch_exists(self, branch):
        matched = re.search(r'\s+{}\n'.format(branch),
                            self._execute('branch', stdout=subprocess.PIPE, encoding='UTF-8').stdout)
        return matched is not None

    def _is_current_branch(self, branch):
        matched = re.search(r'\n?\*\s+{}\n'.format(branch),
                            self._execute('branch', stdout=subprocess.PIPE, encoding='UTF-8').stdout)
        return matched is not None

    def _check_out(self, branch, force: bool = False):
        if not self._is_branch_exists(branch):
            self._execute(f'checkout {"-f " if force else " "}-b {branch} origin/{branch}')
        elif not self._is_current_branch(branch):
            self._execute(f'checkout {"-f " if force else " "}{branch}')

    def _commit(self, message, *patterns):
        if len(patterns) > 0:
            patterns_str = ' '.join([f'"{pattern}"' for pattern in patterns])
            self._execute(f'add --all {patterns_str}')
            self._execute(f'commit -m "{message}"')

    def _push(self, branch):
        self._execute(
            f'push --porcelain --progress --recurse-submodules=check origin refs/heads/{branch}:refs/heads/{branch}')

    def _execute(self, command: str, **kwargs):
        default_kwargs = {
            'cwd': self._directory,
            **kwargs
        }
        return self._executor.git(command, **default_kwargs)
