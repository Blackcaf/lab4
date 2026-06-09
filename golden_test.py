"""Golden тесты транслятора и машины.

Конфигурационные файлы: "golden/*.yml"
"""

import contextlib
import io
import logging
import os
import re
import tempfile

import pytest

import machine
import translator

MAX_LOG_LINES = 500


@pytest.mark.golden_test("golden/*.yml")
def test_translator_and_machine(golden, caplog):
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdirname:
        source = os.path.join(tmpdirname, "source.f")
        input_stream = os.path.join(tmpdirname, "input.txt")
        target = os.path.join(tmpdirname, "target.bin")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["in_stdin"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source, target)
            print("============================================================")
            limit = golden.get("in_limit", 500000)
            cache_size = golden.get("in_cache_size", 256)

            with open(target, "rb") as f:
                binary_code = f.read()

            output, ticks = machine.simulation(
                binary_code=binary_code,
                input_str=golden["in_stdin"],
                limit=limit,
                cache_size=cache_size,
            )
            print(f"\nSimulation output: '{output}'")
            print(f"Total ticks: {ticks}")

        with open(target, "rb") as file:
            code = file.read()
        with open(target + ".txt", encoding="utf-8") as file:
            code_hex = file.read().rstrip("\n")

        stdout_text = stdout.getvalue()
        stdout_text = re.sub(
            r"Successfully translated .*",
            "Successfully translated <source_path> to <target_path>",
            stdout_text,
        )
        stdout_text = re.sub(
            r"([A-Za-z]:)?[/\\].*?[/\\]tmp[\w\-]+", "<tmp>", stdout_text
        )

        log_text = caplog.text
        log_text = re.sub(
            r"([A-Za-z]:)?[/\\].*?[/\\]tmp[\w\-]+", "<tmp>", log_text
        )
        log_text = re.sub(r"root:[^:]+:\d+ ", "", log_text)

        log_lines = log_text.splitlines()
        log_truncated = "\n".join(log_lines[:MAX_LOG_LINES])

        assert code == golden.out["out_code"]
        assert code_hex == golden.out["out_code_hex"]
        assert stdout_text.rstrip("\n") == golden.out["out_stdout"]
        assert log_truncated.rstrip("\n") + "\nEOF" == golden.out["out_log"]
