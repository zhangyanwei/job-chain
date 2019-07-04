import glob
import os
import re
import shutil
import subprocess
import time
from typing import List

from .executor import Executor
from .._utils import read_data
from ..data import resource
from ..logger import logger

_DOCKER_JAVA_PATH = resource('docker/java')
_DOCKER_NGINX_PATH = resource('docker/nginx')

_DOCKER_DIR = os.path.abspath('.docker')
_DOCKER_JAVA_TMP_PATH = os.path.join(_DOCKER_DIR, 'java')
_DOCKER_NGINX_TMP_PATH = os.path.join(_DOCKER_DIR, 'nginx')


class Docker:

    def __init__(self, executor: Executor, registries: List[dict], directory: str):
        """
        constructor

        Args:
            executor (_Executor): executor for docker, and python
            registry (str): the host of docker registry
            directory (str): working directory for docker build
        """
        self._executor = executor
        self._directory = directory
        self._registries = registries
        shutil.rmtree(_DOCKER_DIR, ignore_errors=True)

    def build_env_dockers(self, *paths: str):
        built = []
        for path in paths:
            with open(self._path(f'{path}/Dockerfile')) as f:
                header = f.readline()
            matched = re.findall(r'([^#:\s]+):(.+)', header)
            if matched:
                built.append(self._build_docker(path, *matched[0]))
        return built

    def build_web_dockers(self, configs: dict, modules: [List[str], str]):
        if not os.path.exists(_DOCKER_NGINX_TMP_PATH):
            shutil.copytree(_DOCKER_NGINX_PATH, _DOCKER_NGINX_TMP_PATH)

        built = []
        if type(modules) == list:
            for module in modules:
                dist_path = os.path.join(self._directory, module, 'dist')
                built.append(self._build_web_docker(module, dist_path, configs))
        else:
            dist_path = os.path.join(self._directory, 'dist')
            built.append(self._build_web_docker(modules, dist_path, configs))
        return built

    def build_java_dockers(self, modules: List[str] = None):
        if not os.path.exists(_DOCKER_JAVA_TMP_PATH):
            shutil.copytree(_DOCKER_JAVA_PATH, _DOCKER_JAVA_TMP_PATH)

        built = []
        if modules is not None:
            for module in modules:
                self._build_java_docker(f'{self._directory}/{module}/target/{module}-*.jar', built)
        else:
            self._build_java_docker(f'{self._directory}/target/*.jar', built)
        return built

    def _build_java_docker(self, pathname, build_dockers: list):
        for jar in glob.glob(pathname):
            shutil.copyfile(jar, f'{_DOCKER_JAVA_TMP_PATH}/app.jar')
            time.sleep(5)
            build_dockers.append(
                self._build_docker(_DOCKER_JAVA_TMP_PATH,
                                   *re.findall(r'([^/\\]+)-(\d+[^/\\]+)\.jar$', jar)[0]))
        return build_dockers

    def _build_web_docker(self, name, dist_path, configs):
        tmp_web = os.path.join(_DOCKER_NGINX_TMP_PATH, 'web')
        tmp_conf = os.path.join(_DOCKER_NGINX_TMP_PATH, 'nginx.conf')
        shutil.rmtree(tmp_web, ignore_errors=True)
        shutil.copytree(dist_path, tmp_web)
        if name in configs:
            config_file_path = configs.get(name)
            with open(tmp_conf, 'w') as f:
                f.write(read_data(config_file_path))
        else:
            shutil.copyfile(os.path.join(_DOCKER_NGINX_PATH, 'nginx.conf'), tmp_conf)
        time.sleep(5)  # wait files copy finished
        with open(os.path.join(self._directory, '.version'), 'r') as file:
            version = file.readline()
            if not version:
                raise ValueError('missing version in ".version" file')
            return self._build_docker(_DOCKER_NGINX_TMP_PATH, name, version.strip())

    def _build_docker(self, directory: str, name: str, version: str):
        qualified = version and f'{name}:{version}' or name

        logger.info(f'remove the image {qualified} from local')
        self._execute(f'rmi {qualified}', stderr=subprocess.DEVNULL, check=False)

        logger.info(f'build docker {qualified} in directory {directory}')
        self._execute(f'build {directory} -t {qualified}')

        qualified_in_registries = []
        for registry in self._registries:
            address = registry.get('registry')
            username = registry.get('username')
            password = registry.get('password')

            qualified_in_registry = f'{address}/{qualified}'
            qualified_in_registries.append(qualified_in_registry)

            logger.info(f'push docker image {qualified} to registry {address}')
            self._execute(f'tag {qualified} {qualified_in_registry}')

            # login docker registry
            if username and password:
                self._execute(f'login -u={username} -p={password} {address}')
            self._execute(f'push {qualified_in_registry}')

            logger.info(f'remove the pushed image {qualified_in_registry} from local')
            self._execute(f'rmi {qualified_in_registry}')

        logger.info(f'remove the image {qualified} from local')
        self._execute(f'rmi {qualified}')

        return name, version, qualified_in_registries

    def _path(self, subpath: str) -> str:
        return os.path.abspath(os.path.join(self._directory, subpath))

    def _execute(self, command: str, **kwargs):
        return self._executor.docker(command, cwd=self._directory, **kwargs)
