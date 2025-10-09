#!/usr/bin/env python3
import subprocess
import sys
import re
import os

WITH_ASSERTIONS_DIR = "with_assertions"
WITHOUT_ASSERTIONS_DIR = "without_assertions"
BINARY_NAME = "ring-buffer-smoketest"
OUT_DIR = "out"

try:
    from rust_demangler import demangle as rust_demangle
except ImportError:
    # fallback if rust_demangler not installed
    def rust_demangle(name: str) -> str:
        try:
            # use external `rustfilt` if available
            result = subprocess.run(["rustfilt"], input=name, capture_output=True, text=True)
            if result.returncode == 0:
                # return everything after the last ::
                return result.stdout.strip().split("::")[-1]
        except FileNotFoundError:
            pass
        return name  # fallback to raw name


def compile_project(project_path):
    subprocess.run(['cargo', 'clean'], cwd=project_path)
    subprocess.run(['cargo', 'build', '--release'], cwd=project_path)


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
    # Compile both projects
    compile_project(WITH_ASSERTIONS_DIR)
    compile_project(WITHOUT_ASSERTIONS_DIR)

    # Paths to binaries
    with_bin = f"{WITH_ASSERTIONS_DIR}/target/release/{BINARY_NAME}"
    without_bin = f"{WITHOUT_ASSERTIONS_DIR}/target/release/{BINARY_NAME}"

    # Parse functions + assembly
    with_funcs = get_functions_with_asm(with_bin)
    without_funcs = get_functions_with_asm(without_bin)

    all_funcs = set(with_funcs.keys()) | set(without_funcs.keys())

    total_with = 0
    total_without = 0

    # Make output dirs
    os.makedirs(f"{OUT_DIR}/with", exist_ok=True)
    os.makedirs(f"{OUT_DIR}/without", exist_ok=True)

    # Print header
    print(f"{'Function':40} {'With (bytes)':>15} {'Without (bytes)':>15} {'Δ (bytes)':>10}")
    print("-" * 85)

    for fn in sorted(all_funcs):
        if "ring_buffer" not in fn:
            continue

        demangled = rust_demangle(fn)
        if demangled == "main":
            continue

        w = with_funcs.get(fn, {}).get("size", 0)
        wo = without_funcs.get(fn, {}).get("size", 0)
        delta = w - wo
        total_with += w
        total_without += wo
        print(f"{demangled:40} {w:15} {wo:15} {delta:10}")

        # Write assembly files
        safe_name = demangled.replace("::", "_")
        with open(f"{OUT_DIR}/with/{safe_name}.s", "w") as f:
            f.write("\n".join(with_funcs.get(fn, {}).get("asm", [])))
        with open(f"{OUT_DIR}/without/{safe_name}.s", "w") as f:
            f.write("\n".join(without_funcs.get(fn, {}).get("asm", [])))

    print("-" * 85)
    print(f"{'TOTAL':40} {total_with:15} {total_without:15} {total_with - total_without:10}")
