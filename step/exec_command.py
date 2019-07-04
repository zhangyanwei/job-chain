from ..common.executor import ProxyExecutor


def run(host: str, user: str=None, password: str=None, private_key: str=None, ssh_config: str = None,
        cmd: str=None, cwd: str=None, parameters: list=None, executor: dict=None):
    with ProxyExecutor(host=host, user=user, password=password, private_key=private_key, ssh_config=ssh_config,
                       executor=executor) as proxy_executor:
        if parameters:
            for parameter in parameters:
                proxy_executor.execute(_format_command(cmd, parameter), cwd=cwd)
        else:
            proxy_executor.execute(cmd, cwd=cwd)


def _format_command(cmd, parameter):
    if type(parameter) in [tuple, list, set]:
        return cmd.format(*parameter)
    if type(parameter) == dict:
        return cmd.format(**parameter)
    return cmd.format(parameter)
