class TranslatorError(Exception):
    pass

class TranslatorSyntaxError(TranslatorError):
    pass

class UnknownWordError(TranslatorError):
    pass
