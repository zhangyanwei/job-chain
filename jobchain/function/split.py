def run(value, sep=None):
    if type(value) == str:
        return value.split(sep=sep)
    if value is not None:
        return value
    return []
