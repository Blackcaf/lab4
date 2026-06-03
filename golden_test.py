import base64
import contextlib
import hashlib
import io
import logging
import re
import tempfile
from pathlib import Path

import pytest

import machine
import translator

MAX_LOG_LENGTH = 4000
MAX_STDOUT_LENGTH = 1200
MAX_LISTING_LINES = 120


def sanitize_output(text: str) -> str:
    text = text.replace("\r", "")
    return "".join(
        "<NUL>" if (ord(ch) < 32 and ch not in "\n\t") else ch for ch in text
    )


def _compress_repeated_nuls(text: str) -> str:
    return re.sub(r"(?:<NUL>){8,}", "<NUL>xN", text)


def _normalize_stdout(text: str) -> str:
    text = sanitize_output(text)
    text = _compress_repeated_nuls(text)
    if len(text) > MAX_STDOUT_LENGTH:
        return text[:MAX_STDOUT_LENGTH] + "\n... (stdout truncated)"
    return text


def _normalize_log_locations(text: str) -> str:
    return re.sub(r"([A-Za-z_][\w\-]*\.py):\d+", r"\1:<line>", text)


def _normalize_log_content(text: str) -> str:
    text = _normalize_log_locations(text)
    return re.sub(r"([A-Za-z]:)?[/\\].*?[/\\]tmp[\w\-]+", "<tmp>", text)


def _build_normalized_log(caplog: pytest.LogCaptureFixture) -> str:
    lines: list[str] = []
    for record in caplog.records:
        message = sanitize_output(record.getMessage())
        message = _normalize_log_content(message)
        lines.append(f"{record.levelname:<8} {message}")

    normalized = "\n".join(lines)
    if len(normalized) > MAX_LOG_LENGTH:
        return normalized[:MAX_LOG_LENGTH] + "\n... (log truncated)"
    return normalized


def _normalize_expected_log(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = sanitize_output(text)
    text = _normalize_log_content(text)
    lines: list[str] = []
    for raw_line in text.split("\n"):
        if not raw_line:
            continue
        match = re.match(r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+(.*)$", raw_line)
        if not match:
            continue
        level = match.group(1)
        rest = match.group(2)
        rest = re.sub(r"^root:[^:]+:(?:<line>|\d+)\s+", "", rest)
        lines.append(f"{level:<8} {rest}")

    normalized = "\n".join(lines)
    if len(normalized) > MAX_LOG_LENGTH:
        return normalized[:MAX_LOG_LENGTH] + "\n... (log truncated)"
    return normalized


def _normalize_listing(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    def _ensure_trailing_newline(value: str) -> str:
        return value if value.endswith("\n") else value + "\n"

    text = re.sub(r"; Source: .*", "; Source: <source_path>", text)
    lines = text.splitlines()
    if len(lines) <= MAX_LISTING_LINES:
        return _ensure_trailing_newline(text)
    head = lines[:80]
    tail = lines[-40:]
    return _ensure_trailing_newline(
        "\n".join(head + ["... listing truncated ..."] + tail)
    )


@pytest.mark.golden_test("golden/*.yml")
def test_translator_and_machine(golden, caplog):
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        source_path = str(tmp_path / "source.f")
        input_path = str(tmp_path / "input.txt")
        target_path = str(tmp_path / "target.bin")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(golden["in_source"])
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(golden["in_stdin"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout_io:
            translator.main(source_path, target_path)
            print("============================================================")
            limit = golden.get("in_limit", 500000)
            cache_size = golden.get("in_cache_size", 256)

            with open(target_path, "rb") as f_bin:
                binary_code = f_bin.read()

            output, ticks = machine.simulation(
                binary_code=binary_code,
                input_str=golden["in_stdin"],
                limit=limit,
                cache_size=cache_size,
            )
            print(f"\nSimulation output: '{output}'")
            print(f"Total ticks: {ticks}")

        with open(target_path, "rb") as f:
            binary_code_read = f.read()
        binary_code_b64 = base64.b64encode(binary_code_read).decode("utf-8")
        binary_code_preview = (
            binary_code_b64[:96] + "..."
            if len(binary_code_b64) > 96
            else binary_code_b64
        )
        binary_code_sha256 = hashlib.sha256(binary_code_read).hexdigest()
        binary_code_size = len(binary_code_read)

        hex_listing_path = target_path + ".txt"
        with open(hex_listing_path, "r", encoding="utf-8", newline="") as f:
            hex_code_raw = f.read()
        hex_code_normalized = _normalize_listing(hex_code_raw)

        stdout_raw = stdout_io.getvalue()
        stdout_normalized = re.sub(
            r"Successfully translated .*",
            "Successfully translated <source_path> to <target_path>",
            stdout_raw,
        )
        stdout_sanitized = _normalize_stdout(stdout_normalized)

        log_final = _build_normalized_log(caplog)
        if "out_code_preview" in golden.out:
            assert binary_code_preview == str(golden.out["out_code_preview"])
        if "out_code_sha256" in golden.out:
            assert binary_code_sha256 == str(golden.out["out_code_sha256"])
        if "out_code_size" in golden.out:
            assert binary_code_size == golden.out["out_code_size"]
        if "out_code" in golden.out:
            assert binary_code_b64 == str(golden.out["out_code"])
        expected_hex = _normalize_listing(str(golden.out["out_code_hex"]))
        assert hex_code_normalized == expected_hex
        expected_stdout = _normalize_stdout(str(golden.out["out_stdout"]))
        assert stdout_sanitized == expected_stdout
        raw_expected_log = str(golden.out["out_log"])
        expected_log = _normalize_expected_log(raw_expected_log)
        if raw_expected_log.rstrip().endswith("... (log truncated)"):
            expected_prefix = expected_log.replace("\n... (log truncated)", "")
            if "\n" in expected_prefix:
                expected_prefix = expected_prefix.rsplit("\n", 1)[0]
            assert log_final.startswith(expected_prefix)
        else:
            assert log_final == expected_log
