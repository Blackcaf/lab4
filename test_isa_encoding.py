from isa import Instruction, Opcode


def test_lui_encoding_does_not_mutate_instruction_state():
    instr = Instruction(Opcode.LUI, rs=5, rt=3, imm=0x1234)
    _ = instr.to_binary()
    assert instr.rs == 5


def test_lui_ignores_rs_in_binary_encoding():
    instr_with_rs = Instruction(Opcode.LUI, rs=7, rt=1, imm=0xBEEF)
    instr_zero_rs = Instruction(Opcode.LUI, rs=0, rt=1, imm=0xBEEF)
    assert instr_with_rs.to_binary() == instr_zero_rs.to_binary()
