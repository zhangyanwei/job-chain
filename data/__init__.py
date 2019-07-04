import os

from .._utils import to_native

root = os.path.abspath(os.path.dirname(__file__))


def resource(path):
    return os.path.join(root, to_native(path))
