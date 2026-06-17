from __future__ import annotations

import base64
import contextlib
import io
import logging
import os
import re
import tempfile

import core.machine as machine
import core.translator as translator

TESTS: list[dict[str, str | int]] = [
    {
        "name": "hello",
        "source": "examples/hello/hello.f",
        "stdin": "",
        "limit": 500000,
        "cache_size": 256,
    },
    {
        "name": "cat",
        "source": "examples/cat/cat.f",
        "stdin": "Hello, World!\n",
        "limit": 500000,
        "cache_size": 256,
    },
    {
        "name": "hello_user_name",
        "source": "examples/hello_user_name/hello_user_name.f",
        "stdin": "Alice\n",
        "limit": 500000,
        "cache_size": 256,
    },
    {
        "name": "euler6",
        "source": "examples/euler6/euler6.f",
        "stdin": "",
        "limit": 500000,
        "cache_size": 256,
    },
    {
        "name": "double_add",
        "source": "examples/double_add/double_add.f",
        "stdin": "",
        "limit": 500000,
        "cache_size": 256,
    },
    {
        "name": "sort",
        "source": "examples/sort/sort.f",
        "stdin": "5 3 1 4 2 7 ",
        "limit": 500000,
        "cache_size": 256,
    },
    {
        "name": "cache_test",
        "source": "examples/cache_test/cache_test.f",
        "stdin": "",
        "limit": 500000,
        "cache_size": 256,
    },
]

MAX_LOG_LINES = 500

def _normalize_log(text: str) -> str:
    text = re.sub(r"([A-Za-z]:)?[/\\].*?[/\\]tmp[\w\-]+", "<tmp>", text)
    text = re.sub(r"root:[^:]+:\d+ ", "", text)
    return text

def _yaml_block_scalar(key: str, value: str, chomp: str = "-") -> str:
    lines = value.split("\n")

    while lines and lines[-1] == "":
        lines.pop()
    suffix = chomp
    if not lines:
        return f"{key}: |{suffix}\n"
    return f"{key}: |{suffix}\n" + "\n".join(f"  {line}" for line in lines) + "\n"

def _yaml_binary(key: str, data: bytes) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    lines = [b64[i : i + 76] for i in range(0, len(b64), 76)]
    return f"{key}: !!binary |\n" + "\n".join(f"  {line}" for line in lines) + "\n"

def _yaml_scalar(key: str, value: str) -> str:
    if value == "":
        return f"{key}: ''\n"
    needs_quoting = (
        "\n" in value
        or value != value.strip()
        or value.startswith(
            ("'", '"', "{", "[", "&", "*", "?", "|", "-", ":", "!", "%", "@", "`")
        )
    )
    if needs_quoting:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'{key}: "{escaped}"\n'
    return f"{key}: {value}\n"

def generate_one(test: dict[str, str | int], out_dir: str) -> None:
    name = str(test["name"])
    source_path = str(test["source"])
    stdin = str(test["stdin"])
    limit = int(test["limit"])
    cache_size = int(test["cache_size"])

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_source = os.path.join(tmp_dir, "source.f")
        tmp_input = os.path.join(tmp_dir, "input.txt")
        tmp_target = os.path.join(tmp_dir, "target.bin")

        with open(source_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        with open(tmp_source, "w", encoding="utf-8") as f:
            f.write(source_code)
        with open(tmp_input, "w", encoding="utf-8") as f:
            f.write(stdin)

        caplog_records: list[str] = []

        def _capture_log(msg: str) -> None:
            caplog_records.append(msg)

        log_handler = logging.Handler()
        log_handler.emit = lambda record: caplog_records.append(
            f"{record.levelname:<8} {record.getMessage()}"
        )
        logging.root.addHandler(log_handler)
        logging.root.setLevel(logging.DEBUG)

        with contextlib.redirect_stdout(io.StringIO()) as stdout_io:
            translator.main(tmp_source, tmp_target)
            print("============================================================")

            with open(tmp_target, "rb") as bin_file:
                binary_code = bin_file.read()

            try:
                output, ticks = machine.simulation(
                    binary_code=binary_code,
                    input_str=stdin,
                    limit=limit,
                    cache_size=cache_size,
                )
            finally:
                logging.root.removeHandler(log_handler)

            print(f"\nSimulation output: '{output}'")
            print(f"Total ticks: {ticks}")

        with open(tmp_target + ".txt", "r", encoding="utf-8", newline="") as f:
            hex_listing = f.read()

        stdout_text = stdout_io.getvalue()
        stdout_text = re.sub(
            r"Successfully translated .*",
            "Successfully translated <source_path> to <target_path>",
            stdout_text,
        )
        stdout_text = re.sub(
            r"([A-Za-z]:)?[/\\].*?[/\\]tmp[\w\-]+", "<tmp>", stdout_text
        )

        log_text = "\n".join(caplog_records)
        log_text = _normalize_log(log_text)
        log_lines = log_text.splitlines()
        log_text = "\n".join(log_lines[:MAX_LOG_LINES])
        log_text = log_text.rstrip("\n") + "\nEOF"

        parts: list[str] = []
        parts.append(_yaml_block_scalar("in_source", source_code.rstrip("\n")))
        parts.append(_yaml_scalar("in_stdin", stdin))
        parts.append(_yaml_scalar("in_limit", str(limit)))
        parts.append(_yaml_scalar("in_cache_size", str(cache_size)))
        parts.append(_yaml_binary("out_code", binary_code))
        parts.append(_yaml_block_scalar("out_code_hex", hex_listing.rstrip("\n")))
        parts.append(_yaml_block_scalar("out_stdout", stdout_text.rstrip("\n")))
        parts.append(_yaml_block_scalar("out_log", log_text.rstrip("\n")))

        out_path = os.path.join(out_dir, f"{name}.yml")
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(parts))

        print(f"Generated {out_path}")

def main() -> None:
    golden_dir = os.path.join(os.path.dirname(__file__), "golden")
    os.makedirs(golden_dir, exist_ok=True)
    for test in TESTS:
        generate_one(test, golden_dir)

if __name__ == "__main__":
    main()
