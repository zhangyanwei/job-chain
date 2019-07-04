import glob
import re

from .._utils import to_native
from ..common.repository import Repository
from ..logger import logger


def run(repository: Repository, scopes: list, full_scopes: list, docker_pattern: str, module_pattern: str,
        top_module_check: str=None, reset_repository: bool=False):
    dockers, modules = _retrieve_diffs(
        repository, scopes, full_scopes, docker_pattern, module_pattern, top_module_check
    )
    if reset_repository:
        repository.reset()
    return {
        'dockers': dockers,
        'modules': modules
    }


def _pattern_to_regex(pattern):
    return re.sub(r'[/\\]', r'[/\\\\]', pattern).replace('*', r'[^/\\]+')


def _to_regex(regex):
    return r'(?:\n|^)({})'.format(regex)


def _retrieve_diffs(repository: Repository, scopes: list, full_scopes: list,
                    docker_pattern: str, module_pattern: str, top_module_check: str):
    """
    according the build_scope or the git-diff result to find the dockers and modules to compile.

    Args:

        repository (Repository): Repository instance
        scopes (list): the specified scopes
        full_scopes (list): the scope names for full build.
        docker_pattern (str): docker path pattern
        module_pattern (str): module path pattern
        top_module_check (bool|str): to check whether require full rebuild, if bool value passed, will use it directly,
            otherwise will check the regex.

    Returns:
        (dockers, modules, full_rebuild)
    """
    dockers = set()
    modules = set()
    if scopes:
        if [scope for scope in full_scopes if scope in scopes]:
            logger.info(f'rebuild all modules (specified)')
            modules = None
        else:
            logger.info(f'only rebuild the specified dockers and modules')
            scopes = [to_native(d) for d in scopes]
            dockers.update([d for d in scopes if d in _available(repository, docker_pattern)])
            modules.update([m for m in scopes if m in _available(repository, module_pattern)])
    else:
        diff_result = repository.diff()
        logger.info(f'rebuild the changed dockers')
        dockers.update(_diff_modules(diff_result, docker_pattern))
        if top_module_check and len({m.group(1) for m in re.finditer(_to_regex(top_module_check), diff_result)}) > 0:
            logger.info(f'rebuild all modules because the top modules changed')
            modules = None
        else:
            logger.info(f'rebuild the changed modules')
            modules.update(_diff_modules(diff_result, module_pattern))
    if modules is None:
        logger.info(f'rebuild dockers {dockers or "{}"} and all modules')
    else:
        logger.info(f'rebuild dockers {dockers or "{}"} and modules {modules or "{}"}')
    return dockers, modules


def _diff_modules(diff_result, pattern):
    return {to_native(m.group(1)) for m in re.finditer(_to_regex(_pattern_to_regex(pattern)), diff_result)}


def _available(repository, pattern):
    return [re.sub(r'.+[/\\]({})$'.format(_pattern_to_regex(pattern)), '\\1', d) for d in
            glob.glob(repository.abspath(pattern))]
