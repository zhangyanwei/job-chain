import os
import subprocess
import sys
import uuid

import paramiko

from ..logger import logger


class Executor(object):

    def git(self, command: str, **kwargs):
        raise NotImplementedError

    def mvn(self, command: str, **kwargs):
        raise NotImplementedError

    def npm(self, command: str, **kwargs):
        raise NotImplementedError

    def docker(self, command: str, **kwargs):
        raise NotImplementedError

    def python(self, command, **kwargs):
        raise NotImplementedError

    def abspath(self, path: str, subpath: str = ''):
        raise NotImplementedError

    def path_exists(self, path: str):
        raise NotImplementedError

    def execute(self, command: str, *, cwd=None, **kwargs):
        raise NotImplementedError


class FileTransfer(object):

    def put_file(self, local_file: str, remote_destination: str):
        raise NotImplementedError

    def get_file(self, remote_file: str, local_destination: str):
        raise NotImplementedError


class EmptyExecutor(Executor):

    def __init__(self, *, git_executor: str = 'git {}', maven_executor: str = 'mvn {}', npm_executor: str = 'npm {}',
                 docker_executor: str = 'docker {}', python_executor: str = None):
        """
        Executor for git, maven and npm, will call `subprocess.run`` method to handle them.

        Args:
            git_executor (str): the git executor pattern, ex: git {}
            maven_executor (str): the maven executor pattern, ex: mvn {}
            npm_executor (str): the npm executor pattern, ex: npm {}
            docker_executor (str): the docker executor pattern, ex: docker {}
            python_executor (str): the python executor pattern, ex: python {}
        """
        self._git_executor = git_executor
        self._maven_executor = maven_executor
        self._npm_executor = npm_executor
        self._docker_executor = docker_executor
        self._python_executor = python_executor or f'"{sys.executable}" {{}}'

    def git(self, command: str, **kwargs):
        return self.execute(self._git_executor.format(command), **kwargs)

    def mvn(self, command: str, **kwargs):
        return self.execute(self._maven_executor.format(command), **kwargs)

    def npm(self, command: str, **kwargs):
        return self.execute(self._npm_executor.format(command), **kwargs)

    def docker(self, command: str, **kwargs):
        return self.execute(self._docker_executor.format(command), **kwargs)

    def python(self, command, **kwargs):
        return self.execute(self._python_executor.format(command), **kwargs)

    def abspath(self, path: str, subpath: str = ''):
        raise NotImplementedError

    def path_exists(self, path: str):
        raise NotImplementedError

    def execute(self, command: str, *, cwd=None, **kwargs):
        raise NotImplementedError


class EmtpyRemoteExecutor(EmptyExecutor, FileTransfer):

    def abspath(self, path: str, subpath: str = ''):
        # ret = self.python(rf'-c "import os; print(os.path.abspath(os.path.join(\"{path}\", \"{subpath}\")))"', stdout=subprocess.PIPE, encoding='UTF-8')
        ret = self.execute(f'readlink -efm "{path}/{subpath}"', stdout=subprocess.PIPE, encoding='UTF-8')
        return str(ret.stdout).strip()

    def path_exists(self, path: str):
        ret = self.execute(f'[ -e "{path}" ] && echo "true" || echo "false"', stdout=subprocess.PIPE, encoding='UTF-8')
        return str(ret.stdout).strip() == 'true'

    def put_file(self, local_file: str, remote_destination: str):
        raise NotImplementedError

    def get_file(self, remote_file: str, local_destination: str):
        raise NotImplementedError

    def execute(self, command: str, *, cwd=None, **kwargs):
        raise NotImplementedError


class LocalExecutor(EmptyExecutor):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def abspath(self, path: str, subpath: str = ''):
        return os.path.abspath(os.path.join(path, subpath))

    def path_exists(self, path: str):
        return os.path.exists(path)

    def execute(self, command: str, *, cwd=None, **kwargs):
        logger.info(f'execute local command: "{command}"' + (f' in directory {cwd}' if cwd else ''))
        return subprocess.run(command, cwd=cwd, **{'shell': True, 'check': True, **kwargs})


class ProxyExecutor(Executor, FileTransfer):

    def __init__(self, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        use_paramiko = kwargs.pop('paramiko', False)
        if not kwargs.get('host'):
            self._proxy_executor = LocalExecutor(**kwargs)
        elif use_paramiko or kwargs.get('password'):
            self._proxy_executor = RemoteExecutor(**kwargs)
        else:
            self._proxy_executor = ShellRemoteExecutor(**kwargs)

    def git(self, command: str, **kwargs):
        return self._proxy_executor.git(command, **kwargs)

    def mvn(self, command: str, **kwargs):
        return self._proxy_executor.mvn(command, **kwargs)

    def npm(self, command: str, **kwargs):
        return self._proxy_executor.npm(command, **kwargs)

    def docker(self, command: str, **kwargs):
        return self._proxy_executor.docker(command, **kwargs)

    def python(self, command, **kwargs):
        return self._proxy_executor.python(command, **kwargs)

    def abspath(self, path: str, subpath: str = ''):
        return self._proxy_executor.abspath(path, subpath)

    def path_exists(self, path: str):
        return self._proxy_executor.path_exists(path)

    def put_file(self, local_file: str, remote_destination: str):
        if self.is_local_proxy():
            raise RuntimeError('Not support copy file through the LocalExecutor yet.')
        self._proxy_executor.put_file(local_file, remote_destination)

    def get_file(self, remote_file: str, local_destination: str):
        if self.is_local_proxy():
            raise RuntimeError('Not support copy file through the LocalExecutor yet.')
        self._proxy_executor.get_file(remote_file, local_destination)

    def execute(self, command: str, *, cwd=None, **kwargs):
        return self._proxy_executor.execute(command, cwd=cwd, **kwargs)

    def is_local_proxy(self):
        return type(self._proxy_executor) == LocalExecutor

    def _close(self):
        if hasattr(self, '_proxy_executor') and type(self._proxy_executor) == RemoteExecutor:
            # noinspection PyProtectedMember,PyUnresolvedReferences
            self._proxy_executor._close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._close()

    def __del__(self):
        self._close()


class RemoteExecutor(EmtpyRemoteExecutor):

    def __init__(self, host: str, *, user: str = None, password: str = None, private_key: str = None, **kwargs):
        super().__init__(**kwargs)
        self.ssh = RemoteExecutor._ssh_client(host, user, password, private_key)

    def put_file(self, local_file: str, remote_destination: str):
        with self.ssh.open_sftp() as sftp:
            sftp.put(local_file, remote_destination)

    def get_file(self, remote_file: str, local_destination: str):
        with self.ssh.open_sftp() as sftp:
            sftp.get(remote_file, local_destination)

    def execute(self, command: str, *, cwd=None, check=True, **kwargs):
        logger.info(f'Execute remote command: "{command}"' + (f' in directory {cwd}' if cwd else ''))
        if cwd:
            command = f'cd {cwd} && {command}'
        _, stdout, stderr = self.ssh.exec_command(command)
        error = ''.join(stderr.readlines())
        output = ''.join(stdout.readlines())
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            if check:
                logger.error('error: ' + error)
                raise subprocess.CalledProcessError(returncode=exit_status, cmd=command, stderr=error)
        return subprocess.CompletedProcess(args=command, returncode=exit_status, stdout=output, stderr=error)

    @staticmethod
    def _ssh_client(host: str, user: str = None, password: str = None, private_key: str = None):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        ssh.load_system_host_keys()
        ssh.connect(host, username=user, password=password, key_filename=private_key)
        return ssh

    def _close(self):
        hasattr(self, 'ssh') and self.ssh.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._close()

    def __del__(self):
        self._close()


class ShellRemoteExecutor(EmtpyRemoteExecutor):

    def __init__(self, host: str, *, user: str = None, private_key: str = None, ssh_config: str = None,
                 ssh_executor: str = 'ssh {}', scp_executor: str = 'scp {}',
                 executor: dict = None, **kwargs):
        # if password is not None and 'host' in executor:
        #     raise RuntimeError('Can not use the password on the remote host to access another server.')
        super().__init__(**kwargs)
        self._private_key = private_key
        self._ssh_config = ssh_config
        self._host = host
        self._user = user
        self._user_prefix = f'{user}@' if user else ''
        self._ssh_executor = ssh_executor
        self._scp_executor = scp_executor
        # Will proxy the local executor if the executor not provided.
        self._proxy_executor = ProxyExecutor(**executor or {})

    def put_file(self, local_file: str, remote_destination: str):
        # Upload the file to the remote server first, then upload it again from the remote server.
        if not self._proxy_executor.is_local_proxy():
            file = f'/tmp/{uuid.uuid4().hex}'
            self._proxy_executor.put_file(local_file, file)
        else:
            file = local_file
        return self._proxy_executor.execute(self._scp_command(file, remote_destination, upload=True))

    def get_file(self, remote_file: str, local_destination: str):
        # Download the file to the remote server, then download it again from the remote server to local.
        if not self._proxy_executor.is_local_proxy():
            file = f'/tmp/{uuid.uuid4().hex}'
            self._proxy_executor.get_file(remote_file, file)
        else:
            file = remote_file
        return self._proxy_executor.execute(self._scp_command(local_destination, file, upload=False))

    def execute(self, command: str, *, cwd=None, **kwargs):
        if cwd:
            command = f'cd {cwd} && {command}'
        command = ShellRemoteExecutor._escape_quoted_command(command)
        command = self._ssh_command(command)
        return self._proxy_executor.execute(command, **kwargs)

    def _ssh_command(self, command: str):
        if self._private_key:
            cmd_options = f'-i {self._private_key} {self._user_prefix}{self._host} "{command}"'
        elif self._ssh_config:
            cmd_options = f'-T -F {self._ssh_config} {self._user_prefix}{self._host} "{command}"'
        else:
            cmd_options = f'{self._user_prefix}{self._host} "{command}"'
        return self._ssh_executor.format(cmd_options)

    def _scp_command(self, local_path: str, remote_path: str, upload: bool = False):
        params = [local_path, f'{self._user_prefix}{self._host}:{remote_path}']
        upload or params.reverse()
        options = ' '.join(params)
        if self._private_key:
            scp_options = f'-i {self._private_key} {options}'
        elif self._ssh_config:
            scp_options = f'-F {self._ssh_config} {options}'
        else:
            scp_options = f'{options}'
        return self._scp_executor.format(scp_options)

    @staticmethod
    def _escape_quoted_command(command: str):
        return command.replace('\\', '\\\\').replace('"', r'\"')
