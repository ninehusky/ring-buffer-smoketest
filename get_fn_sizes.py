#!/usr/bin/env python3
import subprocess
import sys
import re

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

def get_function_sizes(binary):
    result = subprocess.run(["otool", "-tV", binary], capture_output=True, text=True)
    lines = result.stdout.splitlines()

    sizes = {}
    current_fn = None
    start_addr = None
    last_addr = None

    for line in lines:
        # Function header line: looks like "symbol_name:"
        if re.match(r'^[^ \t].*:$', line):
            # close out previous function
            if current_fn and start_addr and last_addr:
                sizes[current_fn] = int(last_addr, 16) - start_addr

            current_fn = line.strip().rstrip(":")
            start_addr = None
            last_addr = None

        # Assembly line: starts with an address
        m = re.match(r'^\s*([0-9a-f]+)\s', line)
        if m:
            if start_addr is None:
                start_addr = int(m.group(1), 16)
            last_addr = m.group(1)

    # last function
    if current_fn and start_addr and last_addr:
        sizes[current_fn] = int(last_addr, 16) - start_addr

    return sizes



if __name__ == "__main__":
    compile_project(WITH_ASSERTIONS_DIR)
    compile_project(WITHOUT_ASSERTIONS_DIR)

    with_bin = f"{WITH_ASSERTIONS_DIR}/target/release/{BINARY_NAME}"
    without_bin = f"{WITHOUT_ASSERTIONS_DIR}/target/release/{BINARY_NAME}"

    with_sizes = get_function_sizes(with_bin)
    without_sizes = get_function_sizes(without_bin)

    all_funcs = set(with_sizes.keys()) | set(without_sizes.keys())

    total_with = 0
    total_without = 0

    print(f"{'Function':40} {'With (bytes)':>15} {'Without (bytes)':>15} {'Δ (bytes)':>10}")
    print("-" * 85)

    for fn in sorted(all_funcs):
        w = with_sizes.get(fn, 0)
        wo = without_sizes.get(fn, 0)
        if "ring_buffer" in fn:
            demangled = rust_demangle(fn)
            if demangled == "main":
                continue
            delta = w - wo
            total_with += w
            total_without += wo
            print(f"{demangled:40} {w:15} {wo:15} {delta:10}")

    print("-" * 85)
    print(f"{'TOTAL':40} {total_with:15} {total_without:15} {total_with - total_without:10}")
