import pytest

from core.isa import Opcode
from core.translator import Translator
from core.translator_exceptions import TranslatorSyntaxError, UnknownWordError


def _opcodes(source: str) -> list[Opcode]:
    code, _ = Translator().translate(source)
    return [instr.opcode for instr in code]


def test_if_else_then_generates_conditional_and_jump():
    opcodes = _opcodes(": T 1 IF 2 ELSE 3 THEN ; T HALT")
    assert Opcode.JZ in opcodes
    assert Opcode.JMP in opcodes
    assert opcodes[-1] == Opcode.HALT


def test_begin_until_generates_backward_conditional_jump():
    opcodes = _opcodes(": LOOP 1 BEGIN 0 UNTIL ; LOOP HALT")
    assert opcodes.count(Opcode.JZ) >= 1
    assert opcodes[-1] == Opcode.HALT


def test_unknown_word_raises_typed_error():
    translator = Translator()
    with pytest.raises(UnknownWordError):
        translator.translate("DOES_NOT_EXIST HALT")


def test_misplaced_definition_raises_typed_error():
    translator = Translator()
    with pytest.raises(TranslatorSyntaxError):
        translator.translate("1 : LATE 2 ; HALT")


@pytest.mark.parametrize(
    "source,error_message",
    [
        ("ELSE HALT", "ELSE without IF"),
        ("THEN HALT", "THEN without matching IF/ELSE"),
        ("WHILE HALT", "WHILE without matching BEGIN"),
        ("REPEAT HALT", "REPEAT without matching WHILE"),
        ("BEGIN REPEAT HALT", "REPEAT without matching WHILE"),
        ("UNTIL HALT", "UNTIL without matching BEGIN"),
    ],
)
def test_unmatched_control_flow_constructs_raise_typed_errors(
    source: str, error_message: str
):
    translator = Translator()
    with pytest.raises(TranslatorSyntaxError, match=error_message):
        translator.translate(source)
