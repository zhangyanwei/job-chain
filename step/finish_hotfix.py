from typing import Callable

from . import _release_branch
from ..common.repository import Repository


def run(__parser: Callable, repository: Repository,
        hotfix_version: str, merge_into: str=None, 
        comment: str = None, tag: str = None, verify_callback: dict = None):
    _release_branch.finish_release(__parser, repository,
                                   f'hotfix/{hotfix_version}', merge_into, comment, tag or hotfix_version, verify_callback)
