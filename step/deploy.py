from ..common.container import Containers
from ..common.executor import Executor


def run(executor: Executor, docker_host: str, description: str, profile: str, images: list):
    container = Containers(executor, docker_host, description, profile)
    if images:
        [container.update_container(image, version) for image, version, _ in images]
