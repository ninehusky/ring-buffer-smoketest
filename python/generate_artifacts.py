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
import rust_demangler
WITH_ASSERTIONS_DIR = "../with_assertions"
WITHOUT_ASSERTIONS_DIR = "../without_assertions"
BINARY_NAME = "ring-buffer-smoketest"
OUT_DIR = "../out"


# x86_64, riscv64, arm64.

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

def rust_demangle(name: str) -> str:
    return rust_demangler.demangle(name)


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



def get_functions_with_asm(binary):
    result = subprocess.run(["otool", "-tV", binary], capture_output=True, text=True)
    lines = result.stdout.splitlines()

    functions = {}
    current_fn = None
    start_addr = None
    last_addr = None
    asm_lines = []

    for line in lines:
        # Function header line
        if re.match(r'^[^ \t].*:$', line):
            if current_fn and start_addr and last_addr:
                # ARM64: instructions are always 4 bytes
                size = int(last_addr, 16) - start_addr + 4
                functions[current_fn] = {
                    "size": size,
                    "asm": asm_lines,
                }

            current_fn = line.strip().rstrip(":")
            start_addr = None
            last_addr = None
            asm_lines = []

        # Assembly line
        m = re.match(r'^\s*([0-9a-f]+)\s', line)
        if m:
            if start_addr is None:
                start_addr = int(m.group(1), 16)
            last_addr = m.group(1)
            asm_lines.append(line)

    # last function
    if current_fn and start_addr and last_addr:
        size = int(last_addr, 16) - start_addr
        functions[current_fn] = {
            "size": size,
            "asm": asm_lines,
        }

    return functions


if __name__ == "__main__":
    # Clean both projects once at the start
    clean_project(WITH_ASSERTIONS_DIR)
    clean_project(WITHOUT_ASSERTIONS_DIR)

    # Compile both projects
    for arch_name, arch_info in ARCHITECTURES.items():
        print(f"Compiling for architecture: {arch_name}")
        compile_project(WITH_ASSERTIONS_DIR, arch_info["target"])
        compile_project(WITHOUT_ASSERTIONS_DIR, arch_info["target"])
        print(f"Done compiling for {arch_name}!")

    # # Paths to binaries
    # with_bin = f"{WITH_ASSERTIONS_DIR}/target/release/{BINARY_NAME}"
    # without_bin = f"{WITHOUT_ASSERTIONS_DIR}/target/release/{BINARY_NAME}"

    # # Parse functions + assembly
    # with_funcs = get_functions_with_asm(with_bin)
    # without_funcs = get_functions_with_asm(without_bin)

    # all_funcs = set(with_funcs.keys()) | set(without_funcs.keys())

    # total_with = 0
    # total_without = 0

    # # Make output dirs
    # os.makedirs(f"{OUT_DIR}/with", exist_ok=True)
    # os.makedirs(f"{OUT_DIR}/without", exist_ok=True)

    # # Print header
    # print(f"{'Function':40} {'With (bytes)':>15} {'Without (bytes)':>15} {'Δ (bytes)':>10}")
    # print("-" * 85)

    # for fn in sorted(all_funcs):
    #     if "ring_buffer" not in fn:
    #         continue

    #     demangled = rust_demangle(fn)
    #     if demangled == "main":
    #         continue

    #     w = with_funcs.get(fn, {}).get("size", 0)
    #     wo = without_funcs.get(fn, {}).get("size", 0)
    #     delta = w - wo
    #     total_with += w
    #     total_without += wo
    #     print(f"{demangled:40} {w:15} {wo:15} {delta:10}")

    #     # Write assembly files
    #     safe_name = demangled.replace("::", "_")
    #     with open(f"{OUT_DIR}/with/{safe_name}.s", "w") as f:
    #         f.write("\n".join(with_funcs.get(fn, {}).get("asm", [])))
    #     with open(f"{OUT_DIR}/without/{safe_name}.s", "w") as f:
    #         f.write("\n".join(without_funcs.get(fn, {}).get("asm", [])))

    # print("-" * 85)
    # print(f"{'TOTAL':40} {total_with:15} {total_without:15} {total_with - total_without:10}")
