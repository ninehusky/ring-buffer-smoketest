"""
This script just reads from a file and prints out how many functions (and number of errors) are logged.
"""

import sys

def parse_log(file_path):
    # Look for lines that say "call to <function_name> may panic"
    # error[E0999]: call to core::panicking::panic_fmt may panic
    function_calls = {}
    
    for line in open(file_path, 'r'):
        if "may panic" in line:
            parts = line.split("call to ")
            if len(parts) > 1:
                func_part = parts[1].split(" may panic")[0]
                function_name = func_part.strip()
                if function_name in function_calls:
                    function_calls[function_name] += 1
                else:
                    function_calls[function_name] = 1
    
    return function_calls

if __name__ == "__main__":
    log_file = sys.argv[1]
    function_calls = parse_log(log_file)
    
    total_functions = len(function_calls)
    total_errors = sum(function_calls.values())
    
    print(f"Total unique functions that may panic: {total_functions}")
    print(f"Total panic calls logged: {total_errors}")
    for func, count in function_calls.items():
        print(f"\t{func}: {count}")