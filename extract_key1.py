#!/usr/bin/env python3
"""Extract the DS KEY1 table into key1.bin, from a DeSmuME exe or an ARM7 BIOS file."""
import argparse
import glob
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "key1.bin")

TABLE_SIZE = 0x1048
TABLE_START = bytes.fromhex("99d5205f")  # first word of the KEY1 table
TABLE_SHA1 = "84e467f2485078e401a17a5f231e3fe6e9686648"


def find_in_bytes(data):
    pos = data.find(TABLE_START)
    while pos >= 0:
        table = data[pos:pos + TABLE_SIZE]
        if hashlib.sha1(table).hexdigest() == TABLE_SHA1:
            return table
        pos = data.find(TABLE_START, pos + 1)
    return None


def find_table(path):
    with open(path, "rb") as f:
        return find_in_bytes(f.read())


def main():
    parser = argparse.ArgumentParser(description="Extract the DS KEY1 table into key1.bin.")
    parser.add_argument("source", nargs="?", help="a DeSmuME exe or an ARM7 BIOS file (default: ..\\desmume*\\*.exe)")
    parser.add_argument("--out", default=KEY_FILE, help="where to write (default: key1.bin here)")
    parser.add_argument("--force", action="store_true", help="replace the file if it already exists")
    args = parser.parse_args()

    if os.path.exists(args.out) and not args.force:
        sys.exit("%s already exists. Use --force to replace it." % args.out)
    sources = [args.source] if args.source else glob.glob(os.path.join(glob.escape(HERE), "..", "desmume*", "*.exe"))
    if not sources:
        sys.exit("DeSmuME not found. Give the path to a DeSmuME exe or an ARM7 BIOS file, or run get_key1.py.")
    for path in sources:
        if not os.path.isfile(path):
            sys.exit("%s not found." % path)
        table = find_table(path)
        if table:
            with open(args.out, "wb") as f:
                f.write(table)
            print("Wrote %s (%d bytes) from %s" % (args.out, len(table), path))
            return
    sys.exit("No key table found in: %s" % ", ".join(sources))


if __name__ == "__main__":
    main()
