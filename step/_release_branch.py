from typing import Callable

from . import (maven, npm_build)
from ..common.executor import Executor
from ..common.repository import Repository


def _maven_update_version(executor: Executor, repository: Repository, version, snapshot: bool = False):
    if not version:
        raise ValueError('missing version, it\'s an empty or null')
    new_version = version + ('-SNAPSHOT' if snapshot else '')
    executor.mvn(f'org.codehaus.mojo:versions-maven-plugin:2.1:set -DnewVersion={new_version}', cwd=repository.directory)
    return new_version, ['**pom.xml']


def _mark_update_version(_: Executor, repository: Repository, version, snapshot: bool = False):
    if not version:
        raise ValueError('missing version, it\'s an empty or null')
    new_version = version + ('-SNAPSHOT' if snapshot else '')
    with open(repository.abspath('.version'), 'w') as file:
        file.write(new_version)
    return new_version, ['.version']


verify_methods = {
    'maven': maven,
    'npm': npm_build
}

update_version_methods = {
    'maven': _maven_update_version,
    'mark': _mark_update_version
}


def _verify(__parser: Callable, options: dict):
    if options:
        verify_method = options.get('method', {})
        verify_module = verify_methods.get(verify_method)
        if verify_module:
            arguments = options.get('arguments', {})
            arguments = {name: __parser(value) for name, value in arguments.items()}
            verify_module.run(**arguments)


def start_release(__parser: Callable, executor: Executor, repository: Repository,
                  work_branch: str, release_branch: str, release_version: str, next_version: str=None, force: bool = False,
                  verify_callback: dict = None, update_version_method: str = None):

    def update_version(version, snapshot: bool = False):
        if update_version_method:
            update_version_func = update_version_methods.get(update_version_method)
            if update_version_func:
                return update_version_func(executor, repository, version, snapshot)
        return version, []

    repository.start_release(
        work_branch, release_branch,
        verify=lambda: _verify(__parser, verify_callback),
        update_next_version=lambda: update_version(next_version, snapshot=True) if next_version else None,
        update_version=lambda: update_version(release_version),
        force=force
    )


def update_release(__parser: Callable, repository: Repository,
                   release_branch: str, verify_callback: dict=None,
                   merge_into: str=None, merge_comment: str=None, merge_verify_callback: dict=None):
    repository.update_release(release_branch, lambda: _verify(__parser, verify_callback),
                              merge_into, merge_comment, lambda: _verify(__parser, merge_verify_callback))


def finish_release(__parser: Callable, repository: Repository, release_branch: str, merge_into: str,
                   release_comment: str = None, tag: str = None, verify_callback: dict = None):
    repository.finish_release(release_branch, merge_into, release_comment, tag, verify=lambda: _verify(__parser, verify_callback))
