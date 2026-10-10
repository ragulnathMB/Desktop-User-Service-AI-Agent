class Cancelled(Exception):
    """Raised inside a running task when the user pressed Stop."""


class LLMError(Exception):
    """Any problem talking to an online LLM API."""


class ControllerError(Exception):
    """A desktop action could not be performed."""
