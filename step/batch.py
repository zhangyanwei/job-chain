import inspect
from typing import List

import __init__ as steps


def run(commands: dict, executors: List[str]=None):
    ret = dict()
    for name, command in commands.items():
        if executors is None or name in executors:
            command_name = command.get('name')
            step_runner = getattr(steps, command_name, None)
            assert step_runner is not None, f'Not found the executor [{command_name}].'

            command_args = command.get('args')
            parameter_names = inspect.signature(step_runner.run).parameters.keys()
            ret[name] = step_runner.run(**{arg: value for arg, value in command_args.items() if arg in parameter_names})
    return ret


def decorate_arguments(arguments: dict):
    commands = arguments.get('commands')
    executors = arguments.get('executors')
    assert commands is not None, f'Missing commands, it can not be None.'
    return {
        **arguments,
        'commands': {key: value for key, value in commands.items() if key in executors}
    }
