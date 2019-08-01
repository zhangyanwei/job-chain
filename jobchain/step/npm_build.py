import glob
import re
import shutil

from ._executor import Executor
from ._repository import Repository


def run(executor: Executor, repository: Repository, modules=None, modular: bool=False, web_pattern: str='*-web'):
    if not modular:
        _build(executor, repository.directory, repository.abspath('dist'))
    else:
        for m in _available_modules(repository, modules, web_pattern):
            _build(executor, repository.abspath(m), repository.abspath(f'{m}/dist'))


def _build(executor: Executor, working_path: str, dist_path: str):
    shutil.rmtree(dist_path, ignore_errors=True)
    executor.npm('--registry https://registry.npm.taobao.org install', cwd=working_path)
    executor.npm('--registry https://registry.npm.taobao.org run build', cwd=working_path)


def _available_modules(repository: Repository, modules: list, web_pattern: str):
    available_modules = [re.sub(r'.+[/\\]([^/\\]+)$', '\\1', m) for m in glob.glob(f'{repository.directory}/{web_pattern}')]
    if modules is not None:
        available_modules = [m for m in modules if m in available_modules]
    return available_modules
