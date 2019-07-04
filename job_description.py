import collections
import json
import re
from collections import deque

import yaml

from ._utils import read_data


def _recursive_update(left: collections.Mapping, *others: collections.Mapping):
    r = {}
    r.update(left)
    for item in others:
        for k, v in item.items():
            if isinstance(v, collections.Mapping):
                r[k] = _recursive_update(r.get(k) or {}, v)
            else:
                r[k] = v
    return r


def _read_json(json_path, externals: dict = None):
    data = read_data(json_path)
    parsed = json.loads(data)
    if externals:
        for key, value in externals.items():
            _set_nested_attr(parsed, deque(key.split('.')), value)
    return parsed


def _read_yaml(yaml_path, externals: dict = None):
    data = read_data(yaml_path)
    parsed = yaml.load(data)
    if externals:
        for key, value in externals.items():
            _set_nested_attr(parsed, deque(key.split('.')), value)
    return parsed


def _set_nested_attr(jsontree, paths: deque, value: str):
    if paths:
        attr = paths.popleft()
        attr_value = jsontree.get(attr, {})
        jsontree[attr] = _set_nested_attr(attr_value, paths, value)
        return jsontree
    else:
        try:
            return json.loads(value)
        except json.decoder.JSONDecodeError:
            return value


class JobDescription:
    STEP_NAME_PATTERN = r'(\w+)(?:\.([\w\.-]+))?'

    def __init__(self, yaml_path, externals: dict = None):
        self._yaml = _read_yaml(yaml_path, externals)
        self._repositories = self._yaml.get('repositories')
        self._template = self._yaml.get('template', {})
        self._variable = self._yaml.get('variable', {})
        self._check()

    def variable_definition(self) -> dict:
        return self._variable

    def job(self, repository_name: str, job_name: str) -> dict:
        repository = self._repositories[repository_name]
        assert repository, f'Not found repository \'{repository_name}\''
        assert job_name in repository, f'Not found job \'{job_name}\''

        job = repository[job_name]
        merged = _recursive_update(
            {step: step_template for step, step_template in self._template.items() if step in job.keys()},
            job
        )
        # return as the original sort.
        return {step: merged.get(step) for step, params in job.items()}

    def event_handlers(self, event_name: str, repository_name: str, job_name: str, step_name: str = None) -> list:
        handler_name = f'_on_{event_name}'
        return [item.get(handler_name) for item in self._get_objects(repository_name, job_name, step_name) if
                handler_name in item]

    def _get_objects(self, repository_name: str, job_name: str, step_name: str = None) -> list:
        items = [self._repositories]
        repository = self._repositories[repository_name]
        items.append(repository)

        job = repository[job_name]
        items.append(job)

        if step_name:
            items.append(job[step_name])
        items.reverse()
        return items

    def _check(self):
        assert self._repositories, 'invalid file, missing "repositories" attribute'
        for job in self._repositories.values():
            [JobDescription._check_step_name(step_name) for step_name in job.keys()]
        self._check_event_handlers(self._repositories, 3)

    def _check_event_handlers(self, value: collections.Mapping, level: int):
        if level > 0:
            for k, v in value.items():
                if k.startswith('_on_'):
                    assert 'name' in v, f'Missing name for the event handler \'{k}\'.'
                    assert type(v['name']) == str, f'The name of event handler \'{k}\' MUST be a string.'
                    assert 'args' in v, f'Missing args for the event handler \'{k}\'.'
                    assert isinstance(v, collections.Mapping), f'The args of event handler \'{k}\' MUST be an object.'
                if isinstance(v, collections.Mapping):
                    self._check_event_handlers(v, level - 1)

    @staticmethod
    def _check_step_name(step_name: str):
        assert re.match(JobDescription.STEP_NAME_PATTERN, step_name), \
            f'invalid step name "${step_name}", the pattern of valid step name is "${JobDescription.STEP_NAME_PATTERN}"'
