#!/usr/bin/env python3
# pyright: reportMissingTypeStubs=false

"""
This script compiles two Rust projects (one with assertions enabled and one without),
extracts function sizes for ring buffer related functions, and outputs:
- The total ELF size for the test harness
- The size of each function in both builds
- The disassembly of each function in both builds

This compiles the projects on three architectures: x86, riscv32, and arm32.
In `rustup` world, these are `i686-unknown-linux-gnu`, `riscv32i-unknown-none-elf`,
and `armv7-unknown-linux-gnueabihf`.

We assume you have the relevant cross-compilation toolchains installed, e.g.
for Ubuntu:
- `gcc-i686-linux-gnu`
- `gcc-arm-linux-gnueabihf`
- `riscv64-unknown-elf`

See this repository's Dockerfile for an example of how to set this up.
"""
import subprocess
import re
import os
import csv
from typing import Optional, List, Dict

WITH_ASSERTIONS_DIR = "with_assertions"
WITHOUT_ASSERTIONS_DIR = "without_assertions"
BINARY_NAME = "ring-buffer-smoketest"
OUT_DIR = "out"
DISASM_OUT_DIR = os.path.join(OUT_DIR, "disasm")

EXPECTED_FUNCTIONS = [
    "available_len",
    "as_slices",
    "has_elements",
    "is_full",
    "len",
    "enqueue",
    "push",
    "dequeue",
    "remove_first_matching",
    "empty",
    "retain",
]

ARCHITECTURES = {
    "x86": {
        "target": "i686-unknown-linux-gnu",
    },
    "arm": {
        "target": "armv7-unknown-linux-gnueabihf",
    },
    "riscv": {
        "target": "riscv32imac-unknown-none-elf",
    },
}

def simple_fn_name(full_name: str) -> str:
    """
    Extracts the last function/method name from a Rust demangled symbol.
    E.g.,
    '<<RingBuffer<T> as Queue<T>>::has_elements>' -> 'has_elements'
    """
    # Remove leading/trailing angle brackets
    name = full_name.strip("<>")

    # Split by '::' and take the last component
    # assert "::" in name, f"Expected '::' in demangled function name, got: {name}"
    parts = name.split("::")
    if parts:
        return parts[-1]
    else:
        return name


def rust_demangle(symbol: str) -> str:
    """
    Demangles a Rust symbol using rustfilt.
    """
    symbol_clean = symbol.split(",")[0]
    try:
        output = subprocess.run(
            ["rustfilt"], input=symbol_clean, text=True, capture_output=True
        )
        if output.returncode == 0:
            return output.stdout.strip()
    except Exception:
        pass
    return symbol_clean


def clean_project(project_path: str):
    clean_proc = subprocess.run(
        ['cargo', 'clean'],
        cwd=project_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if clean_proc.returncode != 0:
        print(f"[cargo clean] failed for {project_path}:\n{clean_proc.stderr}")
        raise RuntimeError(f"cargo clean failed for {project_path}")

def compile_project(project_path: str, arch: str):
    # Build step
    env = os.environ.copy()
    env["RUSTFLAGS"] = "-C link-arg=-nostdlib"
    build_proc = subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--target",
            arch,
        ],
        cwd=project_path,
        env=env,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if build_proc.returncode != 0:
        print(f"[cargo build] failed for {project_path} ({arch}):\n{build_proc.stderr}")
        raise RuntimeError(f"cargo build failed for {project_path} ({arch})")

def add_function_entry(functions: Dict[str, Dict[str, object]], current_fn: Optional[str], start_addr: Optional[int], last_addr: Optional[int], asm_lines: List[str]):
    if current_fn is not None and start_addr is not None and last_addr is not None:
        size = last_addr - start_addr + 1
        demangled = rust_demangle(current_fn)
        short_name = simple_fn_name(demangled)
        # We want to bail early if:
        # 1. The function is not in EXPECTED_FUNCTIONS AND the function does not have the word "call" in it.
        if short_name not in EXPECTED_FUNCTIONS and "call" not in demangled:
            return
        functions[short_name] = {
            "size": size,
            "asm": "\n".join(asm_lines),
        }

def get_functions_with_asm(binary: str) -> Dict[str, Dict[str, object]]:
    result = subprocess.run(["llvm-objdump", "-D", binary],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print("llvm-objdump failed:", result.stderr)
        return {}

    lines = result.stdout.splitlines()
    functions: Dict[str, Dict[str, object]] = {}

    current_fn = None
    start_addr = None
    last_addr = None
    asm_lines: List[str] = []

    for line in lines:
        # Function header: "000001a8 <function_name>:"
        m_fn = re.match(r'^([0-9a-f]+) <(.+)>:$', line)
        if m_fn:
            # Save previous function
            add_function_entry(functions, current_fn, start_addr, last_addr, asm_lines)

            start_addr = int(m_fn.group(1), 16)
            current_fn = m_fn.group(2)
            last_addr = start_addr
            asm_lines = []
            continue

        # Assembly line: " 1a8: 04 00  add $0x0,%al"
        m_asm = re.match(r'^\s*([0-9a-f]+):\s+([0-9a-f ]+)\s+(.+)$', line)
        if m_asm and current_fn is not None:
            addr = int(m_asm.group(1), 16)
            last_addr = addr
            asm_lines.append(line)

    # Save last function
    add_function_entry(functions, current_fn, start_addr, last_addr, asm_lines)

    return functions



if __name__ == "__main__":
    # "cd" to the ROOT_DIR in the environment.
    assert "ROOT_DIR" in os.environ, "ROOT_DIR environment variable not set"

    os.chdir(os.environ["ROOT_DIR"])

    # Clean both projects once at the start
    clean_project(WITH_ASSERTIONS_DIR)
    clean_project(WITHOUT_ASSERTIONS_DIR)

    # Prepare CSV writers
    os.makedirs(OUT_DIR, exist_ok=True)
    per_function_csv = os.path.join(OUT_DIR, "function_sizes.csv")
    elf_size_csv = os.path.join(OUT_DIR, "elf_sizes.csv")

    with open(per_function_csv, "w", newline="") as func_csv, open(elf_size_csv, "w", newline="") as elf_csv:
        func_writer = csv.writer(func_csv)
        elf_writer = csv.writer(elf_csv)


        all_func_rows = []

        for arch_name, arch_info in ARCHITECTURES.items():
            print(f"Compiling for architecture: {arch_name}")
            compile_project(WITH_ASSERTIONS_DIR, arch_info["target"])
            compile_project(WITHOUT_ASSERTIONS_DIR, arch_info["target"])
            print(f"Done compiling for {arch_name}!")

            # Get ELF sizes
            with_bin = f"{WITH_ASSERTIONS_DIR}/target/{arch_info['target']}/release/{BINARY_NAME}"
            without_bin = f"{WITHOUT_ASSERTIONS_DIR}/target/{arch_info['target']}/release/{BINARY_NAME}"

            # Get file sizes
            try:
                total_elf_with = os.path.getsize(with_bin)
            except Exception:
                total_elf_with = 0
            try:
                total_elf_without = os.path.getsize(without_bin)
            except Exception:
                total_elf_without = 0

            elf_writer.writerow([arch_name, total_elf_with, total_elf_without])

            # Get per-function sizes
            with_sizes = get_functions_with_asm(with_bin)
            without_sizes = get_functions_with_asm(without_bin)
            all_funcs = set(with_sizes.keys()) | set(without_sizes.keys())

            for fn in all_funcs:
                size_with = with_sizes.get(fn, {}).get("size", 0)
                size_without = without_sizes.get(fn, {}).get("size", 0)
                delta = size_with - size_without
                all_func_rows.append([fn, arch_name, size_with, size_without, delta])

                for which, sizes in [("with", with_sizes), ("without", without_sizes)]:
                    if fn in sizes:
                        asm = sizes[fn].get("asm", "")
                        if asm:
                            # Directory: out/disasm/{function}
                            func_dir = os.path.join(DISASM_OUT_DIR, fn)
                            os.makedirs(func_dir, exist_ok=True)
                            # File: out/disasm/{function}/{arch}-{function}.asm
                            # Optionally, add -with or -without to the filename for clarity
                            filename = f"{arch_name}-{fn}-{which}.asm"
                            file_path = os.path.join(func_dir, filename)
                            with open(file_path, "w") as f:
                                f.write(asm)

        # Sort by function name, then architecture
        all_func_rows.sort(key=lambda row: (row[0], row[1]))

        # Write header
        elf_writer.writerow(["arch", "total_elf_with", "total_elf_without"])
        func_writer.writerow(["function", "arch", "size_with", "size_without", "delta"])

        # Write sorted rows
        for row in all_func_rows:
            func_writer.writerow(row)

        # Append summary rows
        func_writer.writerow([])  # Blank line for separation
        func_writer.writerow(["arch", "total_diff", "percent_change"])

        for arch_name in ARCHITECTURES.keys():
            # Only consider EXPECTED_FUNCTIONS
            arch_rows = [row for row in all_func_rows if row[1] == arch_name and row[0] in EXPECTED_FUNCTIONS]
            total_with = sum(row[2] for row in arch_rows)
            total_without = sum(row[3] for row in arch_rows)
            total_diff = total_with - total_without
            percent_change = (total_diff / total_without * 100) if total_without != 0 else 0
            func_writer.writerow([
                arch_name,
                total_diff,
                f"{percent_change:.2f}%"
            ])
