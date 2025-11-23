#!/usr/bin/env python3

import sys

def normalize(stream):
    buffer = []
    for line in stream:
        stripped = line.rstrip("\n")
        if stripped.strip():  # non-blank line
            buffer.append(stripped)
        else:
            if buffer:
                print(" ".join(buffer))
                buffer = []
            print()  # preserve the blank line
    # flush at end
    if buffer:
        print(" ".join(buffer))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            normalize(f)
    else:
        normalize(sys.stdin)
