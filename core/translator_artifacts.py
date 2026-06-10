from __future__ import annotations

import struct

from core.isa import Instruction


def write_binary_and_listing(
    target_file: str,
    instructions: list[Instruction],
    data_words: list[int],
) -> None:
    with open(target_file, "wb") as f:
        for instr in instructions:
            f.write(instr.to_binary())
        for word_val in data_words:
            f.write(struct.pack(">I", word_val))

    with open(target_file + ".txt", "w", encoding="utf-8", newline="") as f:
        for i, instr in enumerate(instructions):
            f.write(instr.to_hex(i * 4) + "\n")
