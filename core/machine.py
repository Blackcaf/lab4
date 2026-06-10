from __future__ import annotations

import logging
import sys
from collections import deque
from typing import TypedDict

from core.binary_image import bytes_to_words, split_code_and_data
from core.isa import (
    IO_INPUT_PORT,
    IO_OUTPUT_PORT,
    MEMORY_SIZE,
    Instruction,
    Opcode,
    Reg,
)
from core.microcode import MicroOp, get_microcode_rom

CACHE_HIT_LATENCY = 1
CACHE_MISS_LATENCY = 10


class DecodedInstruction(TypedDict):
    opcode: Opcode
    rs: int
    rt: int
    rd: int
    imm: int
    addr: int


class CacheLine:
    def __init__(self) -> None:
        self.valid = False
        self.tag = -1
        self.data = 0

    def __repr__(self) -> str:
        return f"CacheLine(valid={self.valid}, tag={self.tag}, data={hex(self.data)})"


class Cache:
    """
    Модель кеш-памяти. Реализован как direct-mapped кеш.
    Взаимодействует с основной памятью.
    """

    def __init__(self, size_in_lines: int, memory: "Memory", name: str) -> None:
        assert size_in_lines > 0 and (
            size_in_lines & (size_in_lines - 1) == 0
        ), "Cache size must be a power of 2"
        self.size = size_in_lines
        self.lines = [CacheLine() for _ in range(size_in_lines)]
        self.memory = memory
        self.name = name

    def _get_line_and_tag(self, addr: int) -> tuple[int, int]:
        word_addr = addr >> 2
        index_bits = self.size.bit_length() - 1
        line_index = word_addr & ((1 << index_bits) - 1)
        tag = word_addr >> index_bits
        return line_index, tag

    def read(self, addr: int) -> tuple[int, int]:
        line_index, tag = self._get_line_and_tag(addr)
        line = self.lines[line_index]
        if line.valid and line.tag == tag:
            logging.info(f"{self.name}: HIT on read at addr 0x{addr:04X}")
            return line.data, CACHE_HIT_LATENCY
        else:
            logging.warning(
                f"{self.name}: MISS on read at addr 0x{addr:04X}. Accessing memory."
            )
            data = self.memory.read(addr)
            line.valid = True
            line.tag = tag
            line.data = data
            return data, CACHE_MISS_LATENCY

    def write(self, addr: int, data: int) -> int:
        line_index, tag = self._get_line_and_tag(addr)
        line = self.lines[line_index]
        is_hit = line.valid and line.tag == tag
        if is_hit:
            logging.info(
                f"{self.name}: HIT on write at addr 0x{addr:04X}. Updating cache and memory."
            )
            latency = CACHE_HIT_LATENCY
        else:
            logging.warning(
                f"{self.name}: MISS on write at addr 0x{addr:04X}. Writing to memory."
            )
            latency = CACHE_MISS_LATENCY

        self.memory.write(addr, data)

        if is_hit:
            line.data = data

        return latency


class Memory:
    """Однопортовая память: в каждом тике допустима только одна операция (read ИЛИ write)."""

    def __init__(self, size: int) -> None:
        self.size = size
        self.memory = [0] * (size // 4)
        self._port_used = False

    def tick(self):
        self._port_used = False

    def write(self, addr: int, value: int):
        assert 0 <= addr < self.size, f"Invalid memory address: {addr}"
        assert addr % 4 == 0, f"Unaligned write at address: {addr}"
        assert (
            not self._port_used
        ), f"One-port memory: port busy (write at 0x{addr:04X})"
        self._port_used = True
        self.memory[addr >> 2] = value

    def read(self, addr: int) -> int:
        assert 0 <= addr < self.size, f"Invalid memory address: {addr}"
        assert addr % 4 == 0, f"Unaligned read at address: {addr}"
        assert not self._port_used, f"One-port memory: port busy (read at 0x{addr:04X})"
        self._port_used = True
        return self.memory[addr >> 2]


class PortController:
    def __init__(self, input_buffer: list[str]) -> None:
        self.input_buffer: deque[str] = deque(input_buffer)
        self.output_buffer: list[str] = []

    def write(self, port: int, value: int):
        if port == IO_OUTPUT_PORT:
            char = chr(value & 0xFF)
            logging.info(f"PORT I/O: Write to OUTPUT port {port}: '{char}'")
            self.output_buffer.append(char)
        else:
            raise ValueError(f"Unknown output port: {port}")

    def read(self, port: int) -> int | None:
        if port == IO_INPUT_PORT:
            if not self.input_buffer:
                logging.warning("PORT I/O: Input buffer exhausted.")
                return None
            char = self.input_buffer.popleft()
            logging.info(f"PORT I/O: Read from INPUT port {port}: '{char}'")
            return ord(char)
        raise ValueError(f"Unknown input port: {port}")


class DataPath:
    def __init__(self, memory_size: int, cache_size: int, input_buffer: list[str]):
        self.instruction_memory = Memory(memory_size)
        self.data_memory = Memory(memory_size)
        self.instruction_cache = Cache(cache_size, self.instruction_memory, "I-CACHE")
        self.data_cache = Cache(cache_size, self.data_memory, "D-CACHE")
        self.ports = PortController(input_buffer)

        self.gpr = [0] * 8
        self.gpr[Reg.SP.value] = memory_size - 4000
        self.data_sp = memory_size - 20000
        self.pc = 0
        self.mar = 0
        self.mdr = 0
        self.ir_reg = 0
        self.alu_a = 0
        self.alu_b = 0
        self.alu_out = 0
        self.zero_flag = False

    @property
    def sp(self) -> int:
        return self.gpr[Reg.SP.value]

    @sp.setter
    def sp(self, value: int):
        self.gpr[Reg.SP.value] = value

    def decode_ir(self) -> DecodedInstruction:
        opcode_val = (self.ir_reg >> 26) & 0x3F
        rs = (self.ir_reg >> 21) & 0x1F
        rt = (self.ir_reg >> 16) & 0x1F
        rd = (self.ir_reg >> 11) & 0x1F
        imm = self.ir_reg & 0xFFFF
        addr = self.ir_reg & 0x03FFFFFF

        try:
            opcode = Opcode(opcode_val)
        except ValueError:
            logging.error(f"Unknown opcode value: {hex(opcode_val)}. Treating as NOP.")
            opcode = Opcode.NOP

        sign_extended_opcodes = {
            Opcode.ADDI,
            Opcode.LOAD,
            Opcode.STORE,
            Opcode.JZ,
            Opcode.JNZ,
        }
        if opcode in sign_extended_opcodes:
            if (imm & 0x8000) == 0x8000:
                imm -= 1 << 16
        return {
            "opcode": opcode,
            "rs": rs,
            "rt": rt,
            "rd": rd,
            "imm": imm,
            "addr": addr,
        }

    def alu_op(self, op: MicroOp):
        """Выполняет операцию в АЛУ."""
        operations = {
            MicroOp.ALU_ADD: lambda a, b: a + b,
            MicroOp.ALU_SUB: lambda a, b: a - b,
            MicroOp.ALU_MUL: lambda a, b: a * b,
            MicroOp.ALU_DIV: lambda a, b: a // b if b != 0 else 0,
            MicroOp.ALU_MOD: lambda a, b: a % b if b != 0 else 0,
            MicroOp.ALU_OR: lambda a, b: a | b,
            MicroOp.ALU_AND: lambda a, b: a & b,
            MicroOp.ALU_XOR: lambda a, b: a ^ b,
            MicroOp.ALU_CMP: lambda a, b: 1 if a == b else 0,
            MicroOp.ALU_SHL: lambda a, b: a << b,
            MicroOp.ALU_SHR: lambda a, b: a >> b,
            MicroOp.ALU_LUI: lambda a, b: b << 16,
        }

        if op in operations:
            self.alu_out = operations[op](self.alu_a, self.alu_b)
        else:
            raise ValueError(f"Unknown ALU micro-op: {op}")
        self.zero_flag = self.alu_out == 0
        self.gpr[0] = 0


class ControlUnit:
    def __init__(self, datapath: DataPath):
        self.datapath = datapath
        self.microcode_rom = get_microcode_rom()
        self.micro_pc = 0
        self.tick_counter = 0
        self.stall_cycles = 0
        self.halted = False
        self.current_decoded_ir: DecodedInstruction = {
            "opcode": Opcode.NOP,
            "rs": 0,
            "rt": 0,
            "rd": 0,
            "imm": 0,
            "addr": 0,
        }

    def tick(self):
        self.tick_counter += 1

        if self.stall_cycles > 0:
            logging.info(f"STALL: {self.stall_cycles - 1} cycles remaining.")
            self.stall_cycles -= 1
            return

        if self.halted:
            return

        decoded_ir = self.current_decoded_ir
        opcode = decoded_ir["opcode"]
        micro_program = self.microcode_rom.get(opcode)

        if not micro_program:
            raise ValueError(f"No microprogram for opcode: {opcode}")

        if len(micro_program) == 0:
            logging.error(f"Empty microprogram for opcode: {opcode}")
            self.halted = True
            return

        if self.micro_pc >= len(micro_program):
            logging.error(f"MicroPC out of bounds for {opcode}: {self.micro_pc}")
            self.micro_pc = 0
            return

        micro_op = micro_program[self.micro_pc]
        self.execute_micro_op(micro_op, decoded_ir)
        if self.halted:
            return
        next_micro_pc = self.micro_pc + 1

        if micro_op == MicroOp.FINISH_INSTRUCTION:
            next_micro_pc = 0
        if next_micro_pc >= len(micro_program) and next_micro_pc != 0:
            logging.error(
                f"MicroPC for {opcode} will be out of bounds ({next_micro_pc}). Resetting."
            )
            self.micro_pc = 0
        else:
            self.micro_pc = next_micro_pc

    def _handle_pc_operations(
        self, op: MicroOp, ir: DecodedInstruction, dp: "DataPath"
    ):
        if op == MicroOp.LATCH_PC_INC:
            dp.pc += 4
        elif op == MicroOp.LATCH_PC_ADDR:
            logging.info(f"JMP/CALL: Setting PC to 0x{ir['addr']:04X}")
            dp.pc = ir["addr"]
        elif op == MicroOp.LATCH_PC_ALU:
            dp.pc = dp.alu_out

    def _handle_mar_mdr_ir_operations(
        self, op: MicroOp, ir: DecodedInstruction, dp: "DataPath"
    ):
        if op == MicroOp.LATCH_MAR_PC:
            dp.mar = dp.pc
        elif op == MicroOp.LATCH_MAR_ALU:
            if ir["opcode"] == Opcode.RET:
                dp.mar = dp.sp
                logging.debug(f"RET: Reading from call_sp=0x{dp.sp:04X}")
            elif ir["opcode"] == Opcode.POP:
                dp.mar = dp.alu_a
                logging.debug(f"POP: Reading from data_sp=0x{dp.alu_a:04X}")
            else:
                dp.mar = dp.alu_out
        elif op == MicroOp.LATCH_IR:
            dp.ir_reg = dp.mdr
            self.current_decoded_ir = dp.decode_ir()
        elif op == MicroOp.LATCH_MDR_RT:
            dp.mdr = dp.gpr[ir["rt"]]
        elif op == MicroOp.LATCH_MDR_A:
            dp.mdr = dp.alu_a

    def _get_alu_a_value(
        self, op: MicroOp, ir: DecodedInstruction, dp: "DataPath"
    ) -> int:
        if op == MicroOp.LATCH_A_RS:
            return dp.gpr[ir["rs"]]
        elif op == MicroOp.LATCH_A_RT:
            dp.zero_flag = dp.gpr[ir["rt"]] == 0
            return dp.gpr[ir["rt"]]
        elif op == MicroOp.LATCH_A_SP:
            if ir["opcode"] in [Opcode.PUSH, Opcode.POP]:
                return dp.data_sp
            return dp.sp
        elif op == MicroOp.LATCH_A_MDR:
            if ir["opcode"] == Opcode.RET:
                logging.info(f"RET: Read return address 0x{dp.mdr:04X} from stack")
            return dp.mdr
        elif op == MicroOp.LATCH_A_PC:
            if ir["opcode"] == Opcode.CALL:
                logging.info(f"CALL: Saving return address 0x{dp.pc:04X}")
            return dp.pc
        raise ValueError(f"Unknown LATCH_A operation: {op}")

    def _get_alu_b_value(self, op: MicroOp, ir: DecodedInstruction) -> int:
        if op == MicroOp.LATCH_B_RT:
            return self.datapath.gpr[ir["rt"]]
        elif op == MicroOp.LATCH_B_IMM:
            return ir["imm"]
        elif op == MicroOp.LATCH_B_CONST_1:
            return 4
        raise ValueError(f"Unknown LATCH_B operation: {op}")

    def _handle_alu_input_latching(
        self, op: MicroOp, ir: DecodedInstruction, dp: "DataPath"
    ):
        if op.name.startswith("LATCH_A_"):
            dp.alu_a = self._get_alu_a_value(op, ir, dp)
        elif op.name.startswith("LATCH_B_"):
            dp.alu_b = self._get_alu_b_value(op, ir)
        else:
            raise ValueError(f"Unhandled ALU input latching op: {op}")

    def _handle_alu_output_latching(
        self, op: MicroOp, ir: DecodedInstruction, dp: "DataPath"
    ):
        if op == MicroOp.LATCH_RD_ALU:
            dp.gpr[ir["rd"]] = dp.alu_out
        elif op == MicroOp.LATCH_RT_ALU:
            dp.gpr[ir["rt"]] = dp.alu_out
        elif op == MicroOp.LATCH_RT_MDR:
            dp.gpr[ir["rt"]] = dp.mdr
        elif op == MicroOp.LATCH_SP_ALU:
            if not (0 <= dp.alu_out < dp.data_memory.size):
                if ir["opcode"] in [Opcode.PUSH, Opcode.POP]:
                    logging.error(f"Data stack overflow: {dp.alu_out}")
                    raise RuntimeError("Data stack overflow")
                else:
                    logging.error(f"Call stack overflow: {dp.alu_out}")
                    raise RuntimeError("Call stack overflow")

            if ir["opcode"] in [Opcode.PUSH, Opcode.POP]:
                dp.data_sp = dp.alu_out
            else:
                dp.sp = dp.alu_out

    def _handle_branch_operations(
        self, op: MicroOp, ir: DecodedInstruction, dp: "DataPath"
    ):
        if op == MicroOp.BRANCH_IF_ZERO:
            if dp.zero_flag:
                dp.alu_a = dp.pc
                dp.alu_b = ir["imm"]
                dp.alu_op(MicroOp.ALU_ADD)
                dp.pc = dp.alu_out
        elif op == MicroOp.BRANCH_IF_NOT_ZERO:
            if not dp.zero_flag:
                dp.alu_a = dp.pc
                dp.alu_b = ir["imm"]
                dp.alu_op(MicroOp.ALU_ADD)
                dp.pc = dp.alu_out

    def _handle_cache_operations(
        self, op: MicroOp, ir: DecodedInstruction, dp: "DataPath"
    ):
        if op == MicroOp.INSTR_READ:
            data, latency = dp.instruction_cache.read(dp.mar)
            dp.ir_reg = data
            self.current_decoded_ir = dp.decode_ir()
            if latency > 1:
                self.stall_cycles = latency - 1
        elif op == MicroOp.CACHE_READ:
            data, latency = dp.data_cache.read(dp.mar)
            dp.mdr = data
            if latency > 1:
                self.stall_cycles = latency - 1
        elif op == MicroOp.CACHE_WRITE:
            latency = dp.data_cache.write(dp.mar, dp.mdr)
            if latency > 1:
                self.stall_cycles = latency - 1
        elif op == MicroOp.HALT_PROCESSOR:
            self.halted = True
            logging.info("HALT instruction executed. Stopping simulation.")

    def _handle_port_operations(
        self, op: MicroOp, ir: DecodedInstruction, dp: "DataPath"
    ):
        port = ir["imm"]
        if op == MicroOp.PORT_READ:
            port_value = dp.ports.read(port)
            if port_value is None:
                self.halted = True
                logging.info("Simulation stopped: stream input exhausted.")
                return
            dp.mdr = port_value
        elif op == MicroOp.PORT_WRITE:
            logging.info(
                f"PORT I/O: OUT value {dp.mdr} ('{chr(dp.mdr & 0xFF)}') to port {port}"
            )
            dp.ports.write(port, dp.mdr)

    def execute_micro_op(self, op: MicroOp, ir: DecodedInstruction):
        dp = self.datapath
        logging.debug(f"TICK {self.tick_counter}: Executing micro-op: {op.name}")

        if op.name.startswith("LATCH_PC_"):
            self._handle_pc_operations(op, ir, dp)
        elif op.name.startswith(("LATCH_MAR_", "LATCH_MDR_", "LATCH_IR")):
            self._handle_mar_mdr_ir_operations(op, ir, dp)
        elif op.name.startswith(("LATCH_A_", "LATCH_B_")):
            self._handle_alu_input_latching(op, ir, dp)
        elif op.name.startswith(("LATCH_RD_", "LATCH_RT_", "LATCH_SP_")):
            self._handle_alu_output_latching(op, ir, dp)
        elif op.name.startswith("ALU_"):
            dp.alu_op(op)
        elif op.name.startswith("BRANCH_IF_") or op.name.startswith("JUMP_IF_"):
            self._handle_branch_operations(op, ir, dp)
        elif (
            op.name.startswith("CACHE_")
            or op == MicroOp.INSTR_READ
            or op == MicroOp.HALT_PROCESSOR
        ):
            self._handle_cache_operations(op, ir, dp)
        elif op.name.startswith("PORT_"):
            self._handle_port_operations(op, ir, dp)
        elif op == MicroOp.FINISH_INSTRUCTION:
            pass
        else:
            raise ValueError(f"Unknown micro-op during execution: {op}")

        dp.gpr[0] = 0


def _run_simulation_loop(control_unit: "ControlUnit", datapath: "DataPath", limit: int):
    while not control_unit.halted and control_unit.tick_counter < limit:
        datapath.instruction_memory.tick()
        datapath.data_memory.tick()

        try:
            decoded = control_unit.current_decoded_ir
            mnemonic = Instruction(
                decoded["opcode"],
                decoded["rs"],
                decoded["rt"],
                decoded["rd"],
                decoded["imm"],
                decoded["addr"],
            ).get_mnemonic()

            log_msg = (
                f"TICK: {control_unit.tick_counter:4} | "
                f"PC: 0x{datapath.pc:04X} | "
                f"IR: 0x{control_unit.datapath.ir_reg:08X} ({mnemonic}) | "
                f"SP: {datapath.sp} | DSP: {datapath.data_sp} | "
                f"MicroPC: {control_unit.micro_pc} | "
                f"Zero: {datapath.zero_flag}"
            )
            logging.info(log_msg)

            control_unit.tick()

        except (ValueError, IndexError) as e:
            logging.error(f"Error during simulation: {e}")
            break
        except Exception:
            logging.exception("An unexpected error occurred")
            break

    if control_unit.halted:
        logging.info("Simulation halted by HALT instruction.")
    elif control_unit.tick_counter >= limit:
        logging.warning("Simulation limit reached.")


def simulation(binary_code: bytes, input_str: str, limit: int, cache_size: int):
    words = bytes_to_words(binary_code)
    code_words, data_words = split_code_and_data(words)
    datapath = DataPath(MEMORY_SIZE, cache_size, list(input_str))

    for i, word in enumerate(code_words):
        datapath.instruction_memory.tick()
        datapath.instruction_memory.write(i * 4, word)
    for i, word in enumerate(data_words):
        byte_addr = i * 4
        if byte_addr < datapath.data_memory.size:
            datapath.data_memory.tick()
            datapath.data_memory.write(byte_addr, word)
        else:
            logging.warning("Data section overflows memory. Truncating.")
            break

    print(
        "Code size: "
        f"{len(code_words)} words ({len(code_words) * 4} bytes). "
        f"Data size: {len(data_words)} words ({len(data_words) * 4} bytes) "
        "(Harvard: separate instruction/data memories)."
    )

    control_unit = ControlUnit(datapath)

    logging.info("Starting simulation...")
    _run_simulation_loop(control_unit, datapath, limit)

    output = "".join(datapath.ports.output_buffer)
    logging.info(
        f"Simulation finished. Total ticks: {control_unit.tick_counter}. Output: '{output}'"
    )

    return output, control_unit.tick_counter


def main(code_file: str, input_file: str):
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    try:
        with open(code_file, "rb") as f:
            binary_code = f.read()
    except FileNotFoundError:
        logging.critical(f"Error: Code file not found at '{code_file}'")
        sys.exit(1)

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            input_data = f.read()
    except FileNotFoundError:
        logging.warning(f"Input file not found at '{input_file}', using empty input.")
        input_data = ""

    output, ticks = simulation(
        binary_code=binary_code, input_str=input_data, limit=500000, cache_size=32
    )

    print("-" * 40)
    print(f"Simulation output: '{output}'")
    print(f"Total ticks: {ticks}")
    print("-" * 40)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python machine.py <binary_code_file> <input_file>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
