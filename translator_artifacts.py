from __future__ import annotations

import struct

from isa import Instruction


def write_binary_and_listing(
    source_file: str,
    target_file: str,
    instructions: list[Instruction],
    data_words: list[int],
) -> None:
    with open(target_file, "wb") as f:
        for instr in instructions:
            f.write(instr.to_binary())
        for word_val in data_words:
            f.write(struct.pack(">I", word_val))

    data_section_size_bytes = len(data_words) * 4
    with open(target_file + ".txt", "w", encoding="utf-8", newline="") as f:
        f.write(f"; Source: {source_file}\n")
        f.write(f"; Code section (size: {len(instructions) * 4} bytes)\n")
        for i, instr in enumerate(instructions):
            f.write(instr.to_hex(i * 4) + "\n")
        f.write(f"\n; Data section (size: {data_section_size_bytes} bytes)\n")
        f.write("; Data words (decimal):\n")
        f.write(str(data_words) + "\n")
        f.write("; Data words (hex):\n")
        f.write("[" + ", ".join([f"0x{dw:08X}" for dw in data_words]) + "]\n")
