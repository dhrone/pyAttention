# exception.py


class MessageException(Exception):
    def __init__(self, issue="", message=None):
        self.message = message
        super().__init__(issue)


class ParserException(MessageException):
    pass


class MessageTimeout(MessageException):
    pass


class PollingException(Exception):
    pass


class ConnectionException(Exception):
    pass
