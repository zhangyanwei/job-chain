import argparse
import re
import sys

from .job_description import JobDescription
from .job_executor import JobExecutor


class EnvironmentVariableAction(argparse.Action):
    commandline_specified_env = []

    def __init__(self, option_strings, **kwargs):
        self.dest = None
        argparse.Action.__init__(self, option_strings, **kwargs)

    def __call__(self, arg_parser, namespace, values, option_string=None):
        def parse_and_update(value, pair, from_command=False):
            m = re.match(f'^({ENV_KEY_REGEX})=(.*)$', pair)
            assert m, f'invalid variable "{pair}", the format should be "([\w.-]+)=(.*)", but "{pair}" not match'
            value[m.group(1)] = m.group(2)
            if from_command:
                EnvironmentVariableAction.commandline_specified_env.append(m.group(1))

        v = getattr(namespace, self.dest)
        if not v:
            v = {}
        if isinstance(v, str):
            v, d = {}, v
            [parse_and_update(v, pair) for pair in re.split(r'\s+', d)]
        [parse_and_update(v, value, True) for value in values]

        setattr(namespace, self.dest, v)


def create_parser():
    parser = argparse.ArgumentParser(description='jenkins job executor',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--file', required=True, help='file path/url of job description')
    parser.add_argument('-r', '--repository', required=True, help='repository name')
    parser.add_argument('-j', '--job', required=True, help='job name')
    env_group = parser.add_argument_group(
        'overwrite the json attributes, or supply the env variables')
    env_group.add_argument('-d', nargs=argparse.ONE_OR_MORE, action=EnvironmentVariableAction, default=dict(),
                           metavar='jsonpath=value',
                           help='for example: -d configuration.git.password=secret will overwrite the password configuration.')
    env_group.add_argument('-e', nargs=argparse.ONE_OR_MORE, action=EnvironmentVariableAction, default=dict(),
                           metavar='variable=value',
                           help='for example: -e release_version=1.0.0.Beta')
    return parser


def _execute(**kwargs):
    args = kwargs.copy()
    job_description = JobDescription(args["file"], args.get('d'))
    job_executor = JobExecutor(job_description, args['repository'], args.get('job'), args.get('e'))
    job_executor.execute()


def main():
    parsed_args = create_parser().parse_args()
    # noinspection PyBroadException
    try:
        _execute(**(vars(parsed_args)))
    except Exception as e:
        sys.stderr.write(f'[ERROR] failed... type: {type(e)}\n        message: {e}')
        raise
