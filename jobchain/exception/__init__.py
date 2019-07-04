class StepError(Exception):

    """
    Exception raised for errors when executing a step failed.

    Attributes:
        step (str): step name
        alias (str): step alias name
        message (str): error message
    """
    def __init__(self, step: str, alias: str, message: str):
        self.step = step
        self.alias = alias
        self.step_name = step + ('.' + alias if alias else '')
        self.message = message

    def __str__(self):
        return f'The step \'{self.step_name}\' failed, error: {self.message}'


class EventHandlerError(Exception):

    """
    Exception raised for errors when executing an event handler.

    Attributes:
        handler (str): event handler name
        message (str): error message
    """
    def __init__(self, handler: str, message: str):
        self.handler = handler
        self.message = message


class ParseError(Exception):

    """
    Exception for an error when parsing a variable.

    Attributes:
        name (str): variable name
        parser (str): parser expression
        value (str): given value
        message (str): error message
    """
    def __init__(self, name: str, parser: str, value: str, message: str):
        self.name = name
        self.parser = parser
        self.value = value
        self.message = message

    def __str__(self):
        return f'Can\'t parsing variable "{self.name}" with the parser "{self.parser}", ' \
               f'the given value is "{self.value}" and the error message is "{self.message}".'
