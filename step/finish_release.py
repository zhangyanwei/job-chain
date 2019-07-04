from typing import Callable

from . import _release_branch
from ..common.repository import Repository


def run(__parser: Callable, repository: Repository,
        release_version: str, comment: str = None, tag: str = None, verify_callback: dict = None):
    _release_branch.finish_release(__parser, repository,
                                   f'release/{release_version}', 'develop', comment, tag or release_version, verify_callback)
