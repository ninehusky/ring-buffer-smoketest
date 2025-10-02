#!/usr/bin/env python3

import os
import subprocess

def get_harness_size(executable_path):
    subprocess.run(['ls', '-lh', executable_path])

def compile_project(project_path):
    subprocess.run(['cargo', 'clean'], cwd=project_path)
    subprocess.run(['cargo', 'build', '--release'], cwd=project_path)

if __name__ == '__main__':
    compile_project('with_assertions')
    compile_project('without_assertions')

    get_harness_size('with_assertions/target/release/ring-buffer-smoketest')
    get_harness_size('without_assertions/target/release/ring-buffer-smoketest')
