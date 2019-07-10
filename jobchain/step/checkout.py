from ._executor import Executor
from ._repository import Repository


def run(executor: Executor, url: str, branch: str, directory: str,
        user: str=None, password: str=None, commit: str=False, reset: bool=False):
    repository = Repository(executor, directory)
    repository.init(url, user, password, branch)
    if reset:
        repository.reset()
    if commit:
        repository.checkout(commit, True)
    return {'repository': repository}
