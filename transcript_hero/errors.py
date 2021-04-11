class Error(Exception):
    """
    Base error class for transcript hero
    """
    pass


class LimitError(Error):
    """
    Raised when a user limit is reached
    """

    def __init__(self, message):
        self.message = message
