import inspect
import re
from typing import Any, Callable

import jobchain.event as events
import jobchain.function as functions
import jobchain.step as steps
from ._utils import get_nested, optional
from .exception import StepError, ParseError
from .job_description import JobDescription
from .logger import logger

INTERNAL_VARIABLE_PATTERN = r'\$\{((\d+)?(?:\.(?:\w+|\[[\w\.]+\]))*)\}'
VARIABLE_PATTERN = r'\${([a-zA-Z][\w\-_]+)}'
ALL_VARIABLE_PATTERN = r'(\$\{\d*(?:\.(?:\w+|\[[\w\.]+\]))*\}|\$\{[a-zA-Z][\w\-_]+\})'
FUNC_PATTERN = r'\$([a-zA-Z_]+)\((.*)\);'
INTERNAL_VARIABLE_PART = r'(?:[\$\w]+|\[[\w\.]+\])'


class JobExecutor:

    def __init__(self, job_description: JobDescription, repository_name: str, job_name: str, variables: dict=None):
        self._job_description = job_description
        self._repository_name = repository_name
        self._job_name = job_name
        self._job = job_description.job(repository_name, job_name)
        self._context = {
            '$': {},
            '$0': {
                'context': {
                    'repository': repository_name,
                    'job': job_name
                }
            },
            'variables': self._parse_variables(job_description.variable_definition(), variables)
        }

    def execute(self):
        step_names = [key for key in self._job.keys() if not key.startswith('_')]
        try:
            for index in range(len(step_names)):
                step_name = step_names[index]
                step_name_matcher = re.match(JobDescription.STEP_NAME_PATTERN, step_name)
                name, alias = step_name_matcher.groups()
                step = self._job[step_name]
                self._context[f'${index + 1}'] = self._exec_step(name, alias, step)
            self._exec_handler('success')
        except StepError as e:
            self._exec_handler('error', {'error': e}, e.step_name)
            raise

    def _exec_step(self, name, alias, arguments):
        logger.info(f"Running {name}{optional(alias).format('.{}')}")
        step_runner = getattr(steps, name, None)
        if step_runner is None:
            logger.error(f"step runner [{name}] not found. {optional(alias).format('alis: {}')}")
            raise StepError(name, alias, 'Not found')

        # Resolve the step parameters
        if hasattr(step_runner, 'decorate_arguments'):
            arguments = step_runner.decorate_arguments(arguments)
        step_params = {key: self._resolve_context(arguments[key]) for key in arguments.keys()}

        # Execute
        configs, params = JobExecutor._split(step_params)
        if configs.get('_condition', True):
            params['__context'] = dict()
            params['__parser'] = self._resolve_context
            parameter_names = inspect.signature(step_runner.run).parameters.keys()
            try:
                return step_runner.run(**{arg: value for arg, value in params.items() if arg in parameter_names})
            except Exception as e:
                raise StepError(name, alias, str(e))
        else:
            logger.info(f"ignored {name}{optional(alias).format('.{}')}")

    def _exec_handler(self, event_name: str, scoped_variables: dict=None, step_name: str=None):
        error_handlers = self._job_description.event_handlers(event_name, self._repository_name, self._job_name, step_name)
        for handler in error_handlers:
            event_handler = getattr(events, handler['name'], None)
            if event_handler is None:
                raise NotImplementedError(f'Event handler \'{handler.name}\' not implemented yet.')
            parsed_args = {name: self._resolve_context(value, scoped_variables) for name, value in handler.get('args', {}).items()}
            # TODO Should I pass the event object into the handler ?
            if event_handler.run(**parsed_args):
                break

    def _resolve_context(self, value, scoped_variables: dict=None):
        if type(value) == str:
            return self._convert_variable(value, scoped_variables)
        elif type(value) == list:
            return [self._resolve_context(item, scoped_variables) for item in value]
        elif type(value) == dict:
            return {k: self._resolve_context(v, scoped_variables) for k, v in value.items()}
        return value

    def _internal_variable_matched(self, m, to_str: bool = True, scoped_variables: dict=None):
        path, idx = m.groups()
        path_parts = [x.strip('[]') for x in re.findall(INTERNAL_VARIABLE_PART, f'${path}')]
        context_value = self._context
        if scoped_variables:
            context_value = {**context_value, '$': scoped_variables}
        v = get_nested(context_value, path_parts)
        return str(v) if to_str else v

    def _variable_matched(self, m, to_str: bool = True, variables: dict=None):
        variable_name, = m.groups()
        if variables is None:
            v = self._context.get('variables', {}).get(variable_name)
        else:
            v = variables.get(variable_name)
        return str(v) if to_str else v

    def _func_matched(self, m, to_str: bool = True, argument_resolver: Callable[[str], list] = None):
        func_name, args_str = m.groups()
        parameters = argument_resolver(args_str) if argument_resolver else self._default_argument_resolver(args_str)

        if func_name == 'eval':
            ret_val = parameters[0] if len(parameters) == 1 else parameters
        else:
            func = getattr(functions, func_name, None)
            if not func:
                raise NotImplementedError(f'function "{func_name}" not supported yet.')
            ret_val = func.run(*parameters)
        return str(ret_val) if to_str else ret_val

    def _convert_variable(self, value, scoped_variables: dict=None):
        matcher = re.match(INTERNAL_VARIABLE_PATTERN, value)
        if matcher:
            return self._internal_variable_matched(matcher, False, scoped_variables)
        matcher = re.match(VARIABLE_PATTERN, value)
        if matcher:
            return self._variable_matched(matcher, False)
        matcher = re.match(FUNC_PATTERN, value)
        if matcher:
            return self._func_matched(matcher, False)
        # treat as a string replace holder
        ret_value = re.sub(FUNC_PATTERN, self._func_matched, value)
        ret_value = re.sub(INTERNAL_VARIABLE_PATTERN, lambda m: self._internal_variable_matched(m, True, scoped_variables), ret_value)
        ret_value = re.sub(VARIABLE_PATTERN, self._variable_matched, ret_value)
        return ret_value

    def _default_argument_resolver(self, args_str: str,
                                   variable_pattern: str=ALL_VARIABLE_PATTERN,
                                   variable_converter: Callable[[str], Any]=None):
        if not args_str:
            return []
        variables = re.findall(variable_pattern, args_str)
        if not variables:
            return eval(f'[{args_str}]')

        if not variable_converter:
            variable_converter = self._convert_variable
        mapped_variables = {variables[i]: f'_var_{i}' for i in range(len(variables))}
        names = mapped_variables.keys()
        generated_args = ", ".join([mapped_variables[name] for name in names])
        generated_body = re.sub(variable_pattern, lambda vm: mapped_variables[vm.group(1)], args_str)
        generated_lambda = f'lambda {generated_args}: [{generated_body}]'
        logger.info(f'Resolving the argument expression: {args_str}\n\tGenerated argument resolver: {generated_lambda}')
        return eval(generated_lambda)(*[variable_converter(v) for v in names])

    def _parse_variables(self, variable_definition: dict, variables: dict):

        def func_matcher_resolver(m, value, to_str=False):
            return self._func_matched(m, to_str=to_str, argument_resolver=lambda args: argument_resolver(args, value))

        def argument_resolver(args: str, value):
            return self._default_argument_resolver(args, '({})', lambda h: value)

        def value_resolver(value):
            if type(value) == str:
                matcher = re.match(VARIABLE_PATTERN, value)
                if matcher:
                    return self._variable_matched(matcher, False, variables)
            return value

        def parse(name, parser: str=None, value=None):
            try:
                v = variables.get(name, value_resolver(value))
                if parser is None:
                    return v
                matcher = re.match(FUNC_PATTERN, parser)
                if matcher:
                    return func_matcher_resolver(matcher, v)
                return re.sub(FUNC_PATTERN, lambda m: func_matcher_resolver(m, v, True), parser)
            except Exception as e:
                raise ParseError(name, parser, value, str(e))

        return {**variables, **{name: parse(name, **definition)
                                for name, definition in variable_definition.items() if not name.startswith('_')}}

    @staticmethod
    def _split(full_params: dict):
        configs = {}
        params = {}
        for key, value in full_params.items():
            if key.startswith('_'):
                configs[key] = value
            else:
                params[key] = value
        return configs, params
