import json
import re

import dockercompose
from .executor import Executor
from .._utils import read_data


class Containers:
    def __init__(self, executor: Executor, docker_host, json_path: str, profile: str):
        """
        constructor

        Args:
            executor (_Executor): executor for python
            docker_host (str): docker host address
            json_path (str): the path of deploy description json file
            profile (str): deploy profile (defined in description json file)
        """
        self._executor = executor
        self._json_path = json_path
        self._docker_host = docker_host
        self._profile = profile
        self._services = {}

    def update_container(self, image_name: str, version: str):
        self._obtain_containers_info()
        container_info = self._services.get(image_name)
        if container_info:
            params = {
                'json': self._json_path,
                'services': [container_info["container"]]
            }
            if self._docker_host:
                params['host'] = self._docker_host
            if self._profile:
                params['profile'] = self._profile
            if container_info.get('version_env_name'):
                version_env_name = container_info.get('version_env_name')
                params['env'] = {
                    version_env_name: version
                }
            runner = dockercompose.Runner(**params)
            runner.run('run')

    def run_services(self, services: list):
        params = {
            'json': self._json_path,
            'services': services
        }
        if self._docker_host:
            params['host'] = self._docker_host
        if self._profile:
            params['profile'] = self._profile
        runner = dockercompose.Runner(**params)
        runner.run('run')

    def _obtain_containers_info(self):
        if not self._services:
            desc = json.loads(read_data(self._json_path))
            for service in desc['services']:
                image, version_env_name, version = \
                    re.findall(r'(?:.+/)?([^:]+)(?::(?:\${(.+)}|(.+)))?', service['image'])[0]
                self._services[image] = {
                    'container': service['name'],
                    'version_env_name': version_env_name,
                    'version': version
                }
