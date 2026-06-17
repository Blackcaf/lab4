from __future__ import annotations

import logging
from enum import Enum, auto

from core.isa import Opcode


class MicroOp(Enum):
    LATCH_PC_INC = auto()
    LATCH_PC_ADDR = auto()
    LATCH_PC_ALU = auto()

    LATCH_MAR_PC = auto()
    LATCH_IR = auto()
    INSTR_READ = auto()

    LATCH_A_RS = auto()
    LATCH_A_RT = auto()
    LATCH_A_MDR = auto()
    LATCH_A_SP = auto()
    LATCH_A_PC = auto()

    LATCH_B_RT = auto()
    LATCH_B_IMM = auto()
    LATCH_B_CONST_1 = auto()

    LATCH_RD_ALU = auto()
    LATCH_RT_ALU = auto()
    LATCH_RT_MDR = auto()
    LATCH_SP_ALU = auto()

    ALU_ADD = auto()
    ALU_SUB = auto()
    ALU_MUL = auto()
    ALU_DIV = auto()
    ALU_MOD = auto()
    ALU_OR = auto()
    ALU_AND = auto()
    ALU_XOR = auto()
    ALU_CMP = auto()
    ALU_SHL = auto()
    ALU_SHR = auto()
    ALU_LUI = auto()

    LATCH_MAR_ALU = auto()
    LATCH_MDR_RT = auto()
    LATCH_MDR_A = auto()

    CACHE_READ = auto()
    CACHE_WRITE = auto()
    PORT_READ = auto()
    PORT_WRITE = auto()

    BRANCH_IF_ZERO = auto()
    BRANCH_IF_NOT_ZERO = auto()
    FINISH_INSTRUCTION = auto()
    HALT_PROCESSOR = auto()


MICROCODE_SIZE = 64


class MicrocodeMemory:
    def __init__(self) -> None:
        self.size = MICROCODE_SIZE
        self.memory: list[list[MicroOp] | None] = [None] * self.size
        self._port_used = False

    def tick(self) -> None:
        self._port_used = False

    def write(self, addr: int, data: list[MicroOp]) -> None:
        assert 0 <= addr < self.size, f"Invalid microcode address: {addr}"
        self.memory[addr] = data
        logging.info(
            f"MICROCODE: Wrote {len(data)} micro-ops at addr {addr} "
            f"(Opcode.{Opcode(addr).name})"
        )

    def read(self, addr: int) -> list[MicroOp]:
        assert 0 <= addr < self.size, f"Invalid microcode address: {addr}"
        assert not self._port_used, "Microcode memory: port busy this tick"
        self._port_used = True
        data = self.memory[addr]
        if data is None:
            return []
        return data


def _build_microcode_rom() -> MicrocodeMemory:
    fetch_cycle = [
        MicroOp.LATCH_MAR_PC,
        MicroOp.INSTR_READ,
        MicroOp.LATCH_PC_INC,
    ]

    microcode = {
        Opcode.NOP: [MicroOp.FINISH_INSTRUCTION],
        Opcode.HALT: [MicroOp.HALT_PROCESSOR],
        Opcode.ADD: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.SUB: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_SUB,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.MUL: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_MUL,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.DIV: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_DIV,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.MOD: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_MOD,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.OR: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_OR,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.AND: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_AND,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.XOR: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_XOR,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.CMP: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_CMP,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.SHL: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_SHL,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.SHR: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_RT,
            MicroOp.ALU_SHR,
            MicroOp.LATCH_RD_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.ADDI: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_IMM,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_RT_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.ORI: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_IMM,
            MicroOp.ALU_OR,
            MicroOp.LATCH_RT_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.LUI: [
            MicroOp.LATCH_B_IMM,
            MicroOp.ALU_LUI,
            MicroOp.LATCH_RT_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.IN: [
            MicroOp.PORT_READ,
            MicroOp.LATCH_RT_MDR,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.OUT: [
            MicroOp.LATCH_MDR_RT,
            MicroOp.PORT_WRITE,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.LOAD: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_IMM,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_MAR_ALU,
            MicroOp.CACHE_READ,
            MicroOp.LATCH_RT_MDR,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.STORE: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_IMM,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_MAR_ALU,
            MicroOp.LATCH_MDR_RT,
            MicroOp.CACHE_WRITE,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.JZ: [
            MicroOp.LATCH_A_RT,
            MicroOp.BRANCH_IF_ZERO,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.JNZ: [
            MicroOp.LATCH_A_RT,
            MicroOp.BRANCH_IF_NOT_ZERO,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.JMPR: [
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_IMM,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_PC_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.CALLR: [
            MicroOp.LATCH_A_SP,
            MicroOp.LATCH_B_CONST_1,
            MicroOp.ALU_SUB,
            MicroOp.LATCH_SP_ALU,
            MicroOp.LATCH_MAR_ALU,
            MicroOp.LATCH_A_PC,
            MicroOp.LATCH_MDR_A,
            MicroOp.CACHE_WRITE,
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_B_IMM,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_PC_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.PUSH: [
            MicroOp.LATCH_A_SP,
            MicroOp.LATCH_B_CONST_1,
            MicroOp.ALU_SUB,
            MicroOp.LATCH_SP_ALU,
            MicroOp.LATCH_MAR_ALU,
            MicroOp.LATCH_A_RS,
            MicroOp.LATCH_MDR_A,
            MicroOp.CACHE_WRITE,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.POP: [
            MicroOp.LATCH_A_SP,
            MicroOp.LATCH_MAR_ALU,
            MicroOp.CACHE_READ,
            MicroOp.LATCH_A_SP,
            MicroOp.LATCH_B_CONST_1,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_SP_ALU,
            MicroOp.LATCH_RT_MDR,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.JMP: [MicroOp.LATCH_PC_ADDR, MicroOp.FINISH_INSTRUCTION],
        Opcode.CALL: [
            MicroOp.LATCH_A_SP,
            MicroOp.LATCH_B_CONST_1,
            MicroOp.ALU_SUB,
            MicroOp.LATCH_SP_ALU,
            MicroOp.LATCH_MAR_ALU,
            MicroOp.LATCH_A_PC,
            MicroOp.LATCH_MDR_A,
            MicroOp.CACHE_WRITE,
            MicroOp.LATCH_PC_ADDR,
            MicroOp.FINISH_INSTRUCTION,
        ],
        Opcode.RET: [
            MicroOp.LATCH_A_SP,
            MicroOp.LATCH_MAR_ALU,
            MicroOp.CACHE_READ,
            MicroOp.LATCH_A_SP,
            MicroOp.LATCH_B_CONST_1,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_SP_ALU,
            MicroOp.LATCH_A_MDR,
            MicroOp.LATCH_B_IMM,
            MicroOp.ALU_ADD,
            MicroOp.LATCH_PC_ALU,
            MicroOp.FINISH_INSTRUCTION,
        ],
    }

    rom = MicrocodeMemory()
    for opcode, micro_ops in microcode.items():
        rom.write(opcode.value, fetch_cycle + micro_ops)

    return rom


def get_microcode_rom() -> MicrocodeMemory:
    return _build_microcode_rom()
