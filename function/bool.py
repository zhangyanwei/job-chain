def run(value):
    if type(value) == str:
        return value.lower() in ['true', 'yes', 'y']
    if type(value) == bool:
        return value
    return bool(value)
