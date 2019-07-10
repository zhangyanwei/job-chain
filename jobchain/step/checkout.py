from ._executor import Executor
from ._repository import Repository


def run(executor: Executor, url: str, user: str, password: str, branch: str, directory: str, commit: str=False, reset: bool=False):
    repository = Repository(executor, directory)
    repository.init(url, user, password, branch)
    if reset:
        repository.reset()
    if commit:
        repository.checkout(commit, True)
    return {'repository': repository}
