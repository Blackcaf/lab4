import struct
from enum import Enum


class Opcode(Enum):
    """
    Коды операций для моего RISC-процессора.
    Гарвардская архитектура: память команд отделена от памяти данных.
    Forth-стек реализован поверх RISC-инструкций и памяти данных.
    """

    NOP = 0x00
    HALT = 0x01

    ADD = 0x10
    SUB = 0x11
    MUL = 0x12
    DIV = 0x13
    MOD = 0x14
    AND = 0x15
    OR = 0x16
    XOR = 0x17
    CMP = 0x18
    SHL = 0x19
    SHR = 0x1A

    ADDI = 0x20
    LOAD = 0x21
    STORE = 0x22
    JZ = 0x23
    JNZ = 0x24
    LUI = 0x25
    ORI = 0x26
    IN = 0x27
    OUT = 0x28

    PUSH = 0x30
    POP = 0x31

    JMP = 0x32
    CALL = 0x33
    RET = 0x34
    JMPR = 0x35
    CALLR = 0x36


class Reg(Enum):
    ZERO = 0
    SP = 1
    RA = 2
    T0 = 3
    T1 = 4
    T2 = 5
    T3 = 6
    A1 = 7


MEMORY_SIZE = 65536
IO_INPUT_PORT = 0
IO_OUTPUT_PORT = 1


class Instruction:
    _R_TYPE_OPCODES = {
        Opcode.ADD,
        Opcode.SUB,
        Opcode.MUL,
        Opcode.DIV,
        Opcode.MOD,
        Opcode.AND,
        Opcode.OR,
        Opcode.XOR,
        Opcode.CMP,
        Opcode.SHL,
        Opcode.SHR,
    }

    _I_TYPE_OPCODES = {
        Opcode.ADDI,
        Opcode.LOAD,
        Opcode.STORE,
        Opcode.JZ,
        Opcode.JNZ,
        Opcode.LUI,
        Opcode.ORI,
        Opcode.IN,
        Opcode.OUT,
        Opcode.JMPR,
        Opcode.CALLR,
    }

    def __init__(
        self,
        opcode: Opcode,
        rs: int = 0,
        rt: int = 0,
        rd: int = 0,
        imm: int = 0,
        addr: int = 0,
    ) -> None:
        self.opcode = opcode
        self.rs = rs
        self.rt = rt
        self.rd = rd
        self.imm = imm
        self.addr = addr

    def to_binary(self) -> bytes:
        opcode_val = self.opcode.value & 0x3F
        word = 0

        if self.opcode in self._R_TYPE_OPCODES:
            word = (
                (opcode_val << 26) | (self.rs << 21) | (self.rt << 16) | (self.rd << 11)
            )

        elif self.opcode in self._I_TYPE_OPCODES:
            rs = 0 if self.opcode == Opcode.LUI else self.rs
            word = (
                (opcode_val << 26) | (rs << 21) | (self.rt << 16) | (self.imm & 0xFFFF)
            )

        elif self.opcode in [Opcode.JMP, Opcode.CALL]:
            word = (opcode_val << 26) | (self.addr & 0x03FFFFFF)

        elif self.opcode in [Opcode.PUSH]:
            word = (opcode_val << 26) | (self.rs << 21)
        elif self.opcode in [Opcode.POP]:
            word = (opcode_val << 26) | (self.rt << 16)
        else:  # HALT, NOP, RET
            word = opcode_val << 26

        return struct.pack(">I", word)

    def to_hex(self, addr: int) -> str:
        hex_code = self.to_binary().hex().upper()
        mnemonic = self.get_mnemonic()
        return f"0x{addr:04X}: {hex_code}  {mnemonic}"

    def get_mnemonic(self) -> str:
        if self.opcode in self._R_TYPE_OPCODES:
            return f"{self.opcode.name:<5} R{self.rd}, R{self.rs}, R{self.rt}"

        templates = {
            Opcode.ADDI: f"{self.opcode.name:<5} R{self.rt}, R{self.rs}, {self.imm}",
            Opcode.ORI: f"{self.opcode.name:<5} R{self.rt}, R{self.rs}, {self.imm}",
            Opcode.LOAD: f"{self.opcode.name:<5} R{self.rt}, {self.imm}(R{self.rs})",
            Opcode.STORE: f"{self.opcode.name:<5} R{self.rt}, {self.imm}(R{self.rs})",
            Opcode.IN: f"IN    R{self.rt}, port {self.imm}",
            Opcode.OUT: f"OUT   port {self.imm}, R{self.rt}",
            Opcode.JMPR: f"JMPR  R{self.rs}",
            Opcode.CALLR: f"CALLR R{self.rs}",
            Opcode.JZ: f"{self.opcode.name:<5} R{self.rt}, {self.imm}",
            Opcode.JNZ: f"{self.opcode.name:<5} R{self.rt}, {self.imm}",
            Opcode.LUI: f"LUI   R{self.rt}, 0x{self.imm:04X}",
            Opcode.JMP: f"{self.opcode.name:<5} 0x{self.addr:07X}",
            Opcode.CALL: f"{self.opcode.name:<5} 0x{self.addr:07X}",
            Opcode.PUSH: f"PUSH  R{self.rs}",
            Opcode.POP: f"POP   R{self.rt}",
        }
        if self.opcode in templates:
            return templates[self.opcode]
        return self.opcode.name

    def __repr__(self):
        return f"Instruction({self.get_mnemonic()})"
