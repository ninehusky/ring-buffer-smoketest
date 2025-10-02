#!/usr/bin/env python3

# 1. Use `cargo build --release` to compile the `with_assertions/` project and report its size.

# 2. Use `cargo build --release` to compile the `without_assertions/` project and report its size.

import os
import subprocess

def get_rlib_size(rlib_path):
    subprocess.run(['ls', '-lh', rlib_path])

def compile_project(project_path):
    subprocess.run(['cargo', 'clean'], cwd=project_path)
    subprocess.run(['cargo', 'build', '--release'], cwd=project_path)

if __name__ == '__main__':
    compile_project('with_assertions')
    compile_project('without_assertions')

    get_rlib_size('with_assertions/target/release/libring_buffer_smoketest.rlib')
    get_rlib_size('without_assertions/target/release/libring_buffer_smoketest.rlib')
