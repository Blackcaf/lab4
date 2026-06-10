class TranslatorError(Exception):
    """Базовый класс ошибок транслятора."""


class TranslatorSyntaxError(TranslatorError):
    """Неверный синтаксис исходной программы."""


class UnknownWordError(TranslatorError):
    """Неизвестное слово/токен при трансляции."""
