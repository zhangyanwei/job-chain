from typing import Callable

from . import _release_branch
from ..common.executor import Executor
from ..common.repository import Repository


def run(__parser: Callable, executor: Executor, repository: Repository,
        release_version: str, next_develop_version: str, force: bool = False,
        verify_callback: dict = None, update_version_method: str = None):
    _release_branch.start_release(
        __parser, executor, repository, 
        'develop', f'release/{release_version}', release_version, next_develop_version, force, 
        verify_callback, update_version_method
    )
