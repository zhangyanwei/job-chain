from typing import List

from .._utils import available_modules
from ..common.docker import Docker
from ..common.executor import Executor
from ..common.repository import Repository


def run(executor: Executor, repository: Repository,
        registries: List[dict],
        type: str=None, java_modules: list=None, web_modules: dict=None, env_modules: list=None,
        service_pattern: str='*-service', web_pattern='*-web', docker_pattern='docker/*'):
    docker = Docker(executor, registries, repository.directory)
    images = []
    images += _build_java_docker(repository, docker, type, java_modules, service_pattern)
    images += _build_web_docker(repository, docker, type, web_modules, web_pattern)
    images += _build_env_docker(repository, docker, env_modules, docker_pattern)
    return {"images": images}


def _build_java_docker(repository: Repository, docker: Docker, type: str, modules: list, service_pattern: str):
    if type == 'java':
        return docker.build_java_dockers()
    else:
        return docker.build_java_dockers(available_modules(repository, modules, service_pattern))


def _build_web_docker(repository: Repository, docker: Docker, type: str, modules: dict, web_pattern: str):
    module_names = None
    module_configs = {}
    if modules is not None:
        module_names = modules.get('modules')
        module_configs = modules.get('configs')
    if type == 'web':
        name = modules.get('name')
        assert name is not None, 'missing module name, the attribute path is "docker_build.web_modules.name"'
        return docker.build_web_dockers(module_configs, name)
    else:
        return docker.build_web_dockers(module_configs, available_modules(repository, module_names, web_pattern))


def _build_env_docker(repository: Repository, docker: Docker, modules: list, docker_pattern: str):
    return docker.build_env_dockers(*available_modules(repository, modules, docker_pattern))
