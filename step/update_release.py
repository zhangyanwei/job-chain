from typing import Callable

from . import _release_branch
from ..common.repository import Repository


def run(__parser: Callable, repository: Repository,
        release_version: str, verify_callback: dict=None,
        merge_into: str=None, merge_comment: str=None, merge_verify_callback: dict=None):
    _release_branch.update_release(
        __parser, repository,
        f'release/{release_version}', verify_callback,
        merge_into, merge_comment, merge_verify_callback
    )
