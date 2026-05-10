import struct
from enum import Enum


class Opcode(Enum):
    """
    Коды операций для нашего RISC-процессора.
    Гарвардская архитектура: память команд отделена от памяти данных.
    Forth-стек реализован поверх RISC-инструкций и памяти данных.
    """

    # --- Системные инструкции ---
    NOP = 0x00
    HALT = 0x01

    # --- Арифметические и логические R-type (Регистр-Регистр) ---
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

    # --- Инструкции I-type (с непосредственным значением) ---
    ADDI = 0x20
    LOAD = 0x21
    STORE = 0x22
    JZ = 0x23
    JNZ = 0x24
    LUI = 0x25
    ORI = 0x26
    IN = 0x27
    OUT = 0x28

    # --- Инструкции для работы со стеком ---
    PUSH = 0x30
    POP = 0x31

    # --- Инструкции J-type (безусловные переходы) ---
    JMP = 0x32
    CALL = 0x33
    RET = 0x34


class Reg(Enum):
    """Регистры процессора. 8 регистров общего назначения."""

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
    """
    Представление одной 32-битной машинной инструкции.
    Определяет методы для кодирования в бинарный формат.
    """

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
        self.imm = imm  # 16-bit immediate
        self.addr = addr  # 26-bit address for J-type

    def to_binary(self) -> bytes:
        """Кодирование инструкции в 32-битное слово (big-endian)."""
        opcode_val = self.opcode.value & 0x3F
        word = 0

        # R-type: [opcode:6][rs:5][rt:5][rd:5][unused:11]
        if self.opcode in [
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
        ]:
            word = (
                (opcode_val << 26) | (self.rs << 21) | (self.rt << 16) | (self.rd << 11)
            )

        # I-type: [opcode:6][rs:5][rt:5][imm:16]
        elif self.opcode in [
            Opcode.ADDI,
            Opcode.LOAD,
            Opcode.STORE,
            Opcode.JZ,
            Opcode.JNZ,
            Opcode.LUI,
            Opcode.ORI,
            Opcode.IN,
            Opcode.OUT,
        ]:
            if self.opcode == Opcode.LUI:
                self.rs = 0
            word = (
                (opcode_val << 26)
                | (self.rs << 21)
                | (self.rt << 16)
                | (self.imm & 0xFFFF)
            )

        # J-type: [opcode:6][addr:26]
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
        """Генерация строкового представления для листинга (адрес, код, мнемоника)."""
        hex_code = self.to_binary().hex().upper()
        mnemonic = self.get_mnemonic()
        return f"0x{addr:04X}: {hex_code}  {mnemonic}"

    def get_mnemonic(self) -> str:
        """Получить мнемонику инструкции."""
        if self.opcode in [
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
        ]:
            return f"{self.opcode.name:<5} R{self.rd}, R{self.rs}, R{self.rt}"

        elif self.opcode in [Opcode.ADDI, Opcode.ORI]:
            return f"{self.opcode.name:<5} R{self.rt}, R{self.rs}, {self.imm}"
        elif self.opcode in [Opcode.LOAD, Opcode.STORE]:
            return f"{self.opcode.name:<5} R{self.rt}, {self.imm}(R{self.rs})"
        elif self.opcode == Opcode.IN:
            return f"IN    R{self.rt}, port {self.imm}"
        elif self.opcode == Opcode.OUT:
            return f"OUT   port {self.imm}, R{self.rt}"
        elif self.opcode in [Opcode.JZ, Opcode.JNZ]:
            return f"{self.opcode.name:<5} R{self.rt}, {self.imm}"

        elif self.opcode == Opcode.LUI:
            return f"LUI   R{self.rt}, 0x{self.imm:04X}"

        elif self.opcode in [Opcode.JMP, Opcode.CALL]:
            return f"{self.opcode.name:<5} 0x{self.addr:07X}"

        elif self.opcode == Opcode.PUSH:
            return f"PUSH  R{self.rs}"
        elif self.opcode == Opcode.POP:
            return f"POP   R{self.rt}"

        else:
            return self.opcode.name

    def __repr__(self):
        return f"Instruction({self.get_mnemonic()})"
