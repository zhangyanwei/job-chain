import collections
import os
import re
import urllib.request as request
from collections import deque


def read_data(path):
    if re.match(r'^https?://.+$', path):
        with request.urlopen(path) as resp:
            return resp.read().decode('utf-8')
    else:
        with open(path, 'rb') as f:
            return f.read()


def to_native(path):
    return re.sub(r'[/\\]', os.sep.replace('\\', '\\\\'), path)


def optional(value):
    return Optional(value)


def get_nested(value: dict, path: [str, list], default=None):
    if type(path) == str:
        return _get_nested(value, deque(path.split()), default)
    else:
        return _get_nested(value, deque(path), default)


def _get_nested(value: collections.Mapping, keys: deque, default=None):
    if len(keys) > 0:
        attr = keys.popleft()
        value = value.get(attr)
        if len(keys) > 0 and value is not None:
            if isinstance(value, collections.Mapping):
                return _get_nested(value, keys, default)
            if isinstance(value, object):
                return _get_nested(vars(value), keys, default)
    return value or default


def _pattern_to_regex(pattern):
    return re.sub(r'[/\\]', r'[/\\\\]', pattern).replace('*', r'[^/\\]+')


class Optional:

    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def or_get(self, value):
        return self.value if self.value else value

    def format(self, f: str, d=""):
        return f.format(self.value) if self.value else d
