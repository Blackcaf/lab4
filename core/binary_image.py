from __future__ import annotations

import struct

from core.isa import Opcode

def bytes_to_words(binary_code: bytes) -> list[int]:
    if len(binary_code) % 4 != 0:
        raise ValueError("Binary image size must be a multiple of 4 bytes.")
    return [
        struct.unpack(">I", binary_code[i : i + 4])[0]
        for i in range(0, len(binary_code), 4)
    ]

def split_code_and_data(words: list[int]) -> tuple[list[int], list[int]]:
    halt_idx = -1
    for i, word in enumerate(words):
        opcode_val = (word >> 26) & 0x3F
        if opcode_val == Opcode.HALT.value:
            halt_idx = i
            break

    if halt_idx == -1:
        raise ValueError("HALT instruction not found in the binary image.")

    return words[: halt_idx + 1], words[halt_idx + 1 :]
