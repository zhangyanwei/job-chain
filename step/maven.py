import time
import xml.sax

from ..common.executor import Executor
from ..common.repository import Repository


class _VersionHandler(xml.sax.ContentHandler):

    def __init__(self):
        super(_VersionHandler, self).__init__()
        self._version_path = '/project/version'
        self._current_path = []
        self.version = None

    def startElement(self, name: str, attributes: list):
        self._current_path.append(name)

    def characters(self, content: str):
        if '/' + '/'.join(self._current_path) == self._version_path:
            self.version = content

    def endElement(self, name: str):
        self._current_path.pop()

    @staticmethod
    def parse_version(pom: str):
        parser = xml.sax.make_parser()
        parser.setFeature(xml.sax.handler.feature_namespaces, 0)
        handler = _VersionHandler()
        parser.setContentHandler(handler)
        parser.parse(pom)
        return handler.version


def run(executor: Executor, repository: Repository, modules: dict=None,
        skip_unit_test: bool=False, skip_it_test: bool=True, it_env_up_pycmd: str=None, it_env_down_pycmd=None,
        sonar_url: str=None, sonar_auth_token: str=None,
        deploy_repository: str=None):
    phases = 'package'
    sonar_option = ''
    pl_option = ''
    deploy_option = ''
    if sonar_url:
        sonar_option = f' org.sonarsource.scanner.maven:sonar-maven-plugin:sonar -Dsonar.host.url={sonar_url}'
        if sonar_auth_token:
            sonar_option += f' -Dsonar.login={sonar_auth_token}'
    else:
        # if sonar enabled, should build all modules.
        pl_option = f' -am -pl {",".join(modules)}' if modules else ''

    if deploy_repository:
        phases = 'deploy'
        deploy_option = f' -DaltDeploymentRepository={deploy_repository}'

    if not it_env_up_pycmd:
        executor.mvn(
            f'clean {phases}{pl_option}{deploy_option} -Dsurefire.skip.test={skip_unit_test} -Dfailsafe.skip.test={skip_it_test}',
            cwd=repository.directory)
    elif not skip_it_test:
        # package first for integration test environment preparation
        executor.mvn(f'clean package -Dsurefire.skip.test=true -Dfailsafe.skip.test=true',
                     cwd=repository.directory)
        # JUST sleep 5 second for jar files write complete(tricky)
        time.sleep(10)
        try:
            it_env_up_pycmd and executor.python(it_env_up_pycmd, cwd=repository.directory)
            executor.mvn(f'{phases} -P it{pl_option}{sonar_option}{deploy_option} -Dsurefire.skip.test={skip_unit_test} -Dfailsafe.skip.test=false', cwd=repository.directory)
        finally:
            it_env_down_pycmd and executor.python(it_env_down_pycmd, cwd=repository.directory)
    else:
        executor.mvn(
            f'clean {phases}{pl_option}{deploy_option} -Dsurefire.skip.test={skip_unit_test} -Dfailsafe.skip.test=true',
            cwd=repository.directory)
    return {'version': _VersionHandler.parse_version(repository.abspath('pom.xml'))}
