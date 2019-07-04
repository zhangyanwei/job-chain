def run(value: dict, keys, sep=None):
    ks = set()
    if type(keys) == str:
        ks.update(keys.split(sep=sep))
    elif type(keys) == list:
        ks.update(keys)
    return [value.get(key) for key in keys if key in value.keys()]
