#!/usr/bin/env python3
import subprocess
import sys
import re

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

if len(sys.argv) != 3:
    print("Usage: python compare_funcs.py <with_assertions_bin> <without_assertions_bin>")
    sys.exit(1)

with_bin = sys.argv[1]
without_bin = sys.argv[2]

with_sizes = get_function_sizes(with_bin)
without_sizes = get_function_sizes(without_bin)

all_funcs = set(with_sizes.keys()) | set(without_sizes.keys())

for fn in sorted(all_funcs):
    w = with_sizes.get(fn, 0)
    wo = without_sizes.get(fn, 0)
    if "ring_buffer" in fn:
        print(f"{fn}: with={w} bytes, without={wo} bytes (delta = {w-wo})")
