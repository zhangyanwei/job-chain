import glob
import os
import re
import shutil
import subprocess

from .._utils import available_modules
from ..common.executor import Executor, ProxyExecutor
from ..common.repository import Repository
from ..data import resource
from ..logger import logger

_DOCKER_JAVA_PATH = resource('docker/java')


def run(executor: Executor, repository: Repository,
        jar_content_git_configuration: dict,
        remote_ssh_agent_executor: dict,
        remote_docker_registry_configuration: dict,
        modular: bool=True,
        module_pattern: str='*-service',
        file_pattern: str='{module}/target/{module}-*.jar',
        cmd_pattern: str='jar -xf "{file}"',
        modules: list=None,
        directory: str=None):

    _available_modules = None if not modular else available_modules(repository, modules, module_pattern)

    # _available_modules is None means it's not a modular project, or it is.
    if _available_modules is None or len(_available_modules) > 0:
        # step 0: initialize the local git repository to the latest status
        jar_content_repository = Repository(executor, jar_content_git_configuration.get('directory', 'jar-content'))
        jar_content_repository.init(
            jar_content_git_configuration.get('url'),
            jar_content_git_configuration.get('user'),
            jar_content_git_configuration.get('password'),
            jar_content_git_configuration.get('branch')
        )
        jar_content_repository.reset()

        # step 1: extract jars to remote repository
        extracted_modules = _extract_jar(repository, jar_content_repository, file_pattern, cmd_pattern, _available_modules, directory)

        # step 2: commit the jar content into remote repository
        _commit_extracted_jar(jar_content_repository)

        # step 3: remote rebuild jar files
        agent_executor = ProxyExecutor(**remote_ssh_agent_executor)
        _remote_build_docker(agent_executor, jar_content_git_configuration,
                             remote_docker_registry_configuration, extracted_modules, directory)


def _extract_jar(repository: Repository,
                 jar_content_repository: Repository,
                 file_pattern: str, cmd_pattern: str, modules: list=None, directory: str=None):

    def extract(f, m):
        c = jar_content_repository.abspath(m) if directory is None else jar_content_repository.abspath(os.path.join(directory, m))
        shutil.rmtree(c, ignore_errors=True)
        os.makedirs(c, exist_ok=True)
        logger.info(f'extract jar file "{f}" into directory "{c}"')
        subprocess.run(cmd_pattern.format(file=f), cwd=c, check=True, shell=True)

    ret = []
    if modules is not None:
        for module in modules:
            for file in glob.glob(repository.abspath(file_pattern.format(module=module))):
                extract(file, module)
                ret.append(module)
    else:
        for file in glob.glob(repository.abspath('target/*.jar')):
            module_name = re.sub(r'.+[/\\]([^/\\]+)-(\d+[^/\\]+)\.jar$', '\\1', file)
            extract(file, module_name)
            ret.append(module_name)
    return ret


def _commit_extracted_jar(jar_content_repository: Repository):
    if jar_content_repository.local_diff('*'):
        logger.info(f'commit extracted jar into remote git repository')
        jar_content_repository.commit('auto commit', '*')
        jar_content_repository.push()


def _remote_build_docker(agent_executor: ProxyExecutor,
                         jar_content_git_configuration, remote_docker_registry_configuration,
                         modules: list=None, directory: str=None):
    # docker registry information for docker image push
    registry = remote_docker_registry_configuration.get('registry')
    username = remote_docker_registry_configuration.get('username')
    password = remote_docker_registry_configuration.get('password')

    # remote git repository for extracted jars' content
    remote_repository = Repository(agent_executor, jar_content_git_configuration.get('remote_directory', '/root/jar-content'))
    remote_repository.init(jar_content_git_configuration.get('url'),
                           jar_content_git_configuration.get('user'),
                           jar_content_git_configuration.get('password'),
                           jar_content_git_configuration.get('branch'))
    remote_repository.pull()

    java_docker_temp_dir = _prepare_remote_docker_directory(agent_executor)
    working_dir = remote_repository.directory if directory is None else remote_repository.abspath(directory)
    for module in modules:
        logger.info(f'remote build the module "{module}"')
        # retrieve version
        version = agent_executor.execute(f'cat {module}/META-INF/MANIFEST.MF | grep -Po "Implementation-Version: \K.+"',
                                         stdout=subprocess.PIPE, encoding='UTF-8', cwd=working_dir).stdout.strip()
        qualified_docker_image_name = f'{registry}/{module}:{version}'
        # rebuild jar file
        agent_executor.execute(f'cd {module} && jar -cmf0 META-INF/MANIFEST.MF ../{module}.jar .',
                               cwd=working_dir)
        agent_executor.execute(f'cp {module}.jar {java_docker_temp_dir}/app.jar', cwd=working_dir)
        # docker build
        agent_executor.docker(f'build {java_docker_temp_dir} -t {qualified_docker_image_name}')
        # docker push
        if username and password:
            agent_executor.docker(f'login -u={username} -p={password} {registry}')
        agent_executor.docker(f'push {qualified_docker_image_name}')


def _prepare_remote_docker_directory(agent_executor: ProxyExecutor):
    logger.info('preparing the remote docker files')
    java_docker_temp_dir = '/tmp/java_docker'
    java_docker_temp_file_name = 'java_docker'
    java_docker_temp_file = f'{java_docker_temp_file_name}.tar'
    shutil.make_archive(java_docker_temp_file_name, 'tar', _DOCKER_JAVA_PATH)
    agent_executor.execute(f'rm -rf {java_docker_temp_dir} && mkdir -p {java_docker_temp_dir}')
    agent_executor.put_file(java_docker_temp_file, f'/tmp/{java_docker_temp_file}')
    agent_executor.execute(f'tar -xf /tmp/{java_docker_temp_file}', cwd=java_docker_temp_dir)
    return java_docker_temp_dir
