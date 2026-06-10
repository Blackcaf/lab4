class TranslatorError(Exception):
    """Base class for translator errors."""


class TranslatorSyntaxError(TranslatorError):
    """Invalid source program structure."""


class UnknownWordError(TranslatorError):
    """Unknown token/word encountered during translation."""
