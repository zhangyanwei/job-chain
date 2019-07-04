import os
import importlib

for file in os.listdir(os.path.dirname(__file__)):
    if not file.startswith('__'):
        mod_name = file[:-3]   # strip .py at the end
        importlib.import_module('.' + mod_name, package=__package__)
