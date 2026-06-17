import struct

import pytest

from core.binary_image import bytes_to_words, split_code_and_data
from core.isa import Opcode

def _pack_words(words: list[int]) -> bytes:
    return b"".join(struct.pack(">I", word) for word in words)

def test_bytes_to_words_requires_word_alignment():
    with pytest.raises(ValueError, match="multiple of 4"):
        bytes_to_words(b"\x00\x01")

def test_split_code_and_data_splits_on_first_halt():
    halt = Opcode.HALT.value << 26
    fake_data_word_with_halt_opcode = Opcode.HALT.value << 26
    words = [0x00000000, halt, fake_data_word_with_halt_opcode, 0x12345678]
    code_words, data_words = split_code_and_data(words)
    assert code_words == [0x00000000, halt]
    assert data_words == [fake_data_word_with_halt_opcode, 0x12345678]

def test_split_code_and_data_fails_without_halt():
    with pytest.raises(ValueError, match="HALT"):
        split_code_and_data([0x00000000, 0x10000000])

def test_bytes_to_words_roundtrip():
    words = [0x01020304, 0xAABBCCDD]
    encoded = _pack_words(words)
    assert bytes_to_words(encoded) == words
