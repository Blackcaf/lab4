from isa import Opcode
from translator import Translator


def test_execution_token_literal_compiles_to_address_push():
    translator = Translator()
    code, _ = translator.translate("' DUP HALT")
    opcodes = [instr.opcode for instr in code]
    assert Opcode.HALT in opcodes
    assert Opcode.PUSH in opcodes


def test_execute_compiles_to_indirect_call():
    translator = Translator()
    code, _ = translator.translate("' DUP EXECUTE HALT")
    opcodes = [instr.opcode for instr in code]
    assert Opcode.CALLR in opcodes
