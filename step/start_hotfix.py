from typing import Callable

from . import _release_branch
from ..common.executor import Executor
from ..common.repository import Repository


def run(__parser: Callable, executor: Executor, repository: Repository,
        hotfix_version: str, force: bool = False,
        update_version_method: str = None):
    _release_branch.start_release(
        __parser, executor, repository, 
        'master', f'hotfix/{hotfix_version}', hotfix_version, None, force, 
        None, update_version_method
    )
