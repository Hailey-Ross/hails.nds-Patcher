#!/usr/bin/env python3
"""Decrypt the secure area of .nds ROMs so that emulators without a BIOS can boot them.

Only the 2 KB at the start of the ARM9 code changes. The original bytes are saved in the
backups folder first, so --restore can put them back.
"""
import argparse
import glob
import os
import struct
import sys

sys.dont_write_bytecode = True
from extract_key1 import TABLE_SIZE, find_table
from get_key1 import download_table, save_table

HERE =os.path.dirname(os.path.abspath(__file__))
BACKUPS = os.path.join(HERE, "backups")

M = 0xFFFFFFFF
AREA_SIZE = 0x800
DECRYPTED_MARK = bytes.fromhex("ffdeffe7ffdeffe7")


def key_candidates(explicit):
    if explicit:
        if not os.path.isfile(explicit):
            sys.exit("%s not found." % explicit)
        return [explicit]
    found = []
    for name in ("key1.bin", "biosnds7.rom", "bios7.bin"):
        found.append(os.path.join(HERE, name))
    found += glob.glob(os.path.join(HERE, "..", "desmume*", "*.exe"))
    return [path for path in found if os.path.isfile(path)]


def load_table(explicit):
    for path in key_candidates(explicit):
        table = find_table(path)
        if table:
            print("Key table: %s" % path)
            return list(struct.unpack("<%dI" % (TABLE_SIZE // 4), table))
    if explicit:
        sys.exit("No key table in %s." % explicit)
    print("No key table here, getting one from the latest DeSmuME release.")
    try:
        table = download_table()
        save_table(table)
    except (OSError, ValueError) as error:
        sys.exit("Could not get the key table: %s\nUse --key with a DeSmuME exe or an ARM7 BIOS file." % error)
    return list(struct.unpack("<%dI" % (TABLE_SIZE // 4), table))


def round_f(kb, z):
    x = kb[0x12 + ((z >> 24) & 0xFF)]
    x = (kb[0x112 + ((z >> 16) & 0xFF)] + x) & M
    x ^= kb[0x212 + ((z >> 8) & 0xFF)]
    return (kb[0x312 + (z & 0xFF)] + x) & M


def encrypt(kb, d, o=0):
    y, x = d[o], d[o + 1]
    for i in range(0x10):
        z = kb[i] ^ x
        x = y ^ round_f(kb, z)
        y = z
    d[o], d[o + 1] = x ^ kb[0x10], y ^ kb[0x11]


def decrypt(kb, d, o=0):
    y, x = d[o], d[o + 1]
    for i in range(0x11, 1, -1):
        z = kb[i] ^ x
        x = y ^ round_f(kb, z)
        y = z
    d[o], d[o + 1] = x ^ kb[1], y ^ kb[0]


def bswap(v):
    return struct.unpack("<I", struct.pack(">I", v))[0]


def apply_keycode(kb, kc):
    encrypt(kb, kc, 1)
    encrypt(kb, kc, 0)
    for i in range(0x12):
        kb[i] ^= bswap(kc[i % 2])
    s = [0, 0]
    for i in range(0, 0x412, 2):
        encrypt(kb, s)
        kb[i], kb[i + 1] = s[1], s[0]


def init_key(table, idcode, level):
    kb = list(table)
    kc = [idcode, idcode >> 1, (idcode << 1) & M]
    apply_keycode(kb, kc)
    apply_keycode(kb, kc)
    kc[1] = (kc[1] << 1) & M
    kc[2] >>= 1
    if level >= 3:
        apply_keycode(kb, kc)
    return kb


def decrypt_area(table, area, idcode):
    words = list(struct.unpack("<%dI" % (AREA_SIZE // 4), area))
    decrypt(init_key(table, idcode, 2), words)
    kb = init_key(table, idcode, 3)
    for i in range(0, len(words), 2):
        decrypt(kb, words, i)
    return struct.pack("<%dI" % (AREA_SIZE // 4), *words)


def read_area(path):
    """Returns (game code as text, game code as number, ARM9 offset, area), or None if not a usable ROM."""
    with open(path, "rb") as f:
        head = f.read(0x200)
        if len(head) < 0x200:
            return None
        off = struct.unpack_from("<I", head, 0x20)[0]
        if not 0x4000 <= off <= 0x8000 - AREA_SIZE:
            return None
        f.seek(off)
        area = f.read(AREA_SIZE)
    if len(area) != AREA_SIZE:
        return None
    return head[12:16].decode("latin-1"), struct.unpack_from("<I", head, 12)[0], off, area


def backup_path(path):
    return os.path.join(BACKUPS, os.path.splitext(os.path.basename(path))[0] + ".secure-area.bin")


def write_area(path, off, area):
    with open(path, "r+b") as f:
        f.seek(off)
        f.write(area)
    with open(path, "rb") as f:
        f.seek(off)
        return f.read(AREA_SIZE) == area


def patch(path, table, dry_run):
    """Returns True unless something went wrong."""
    name = os.path.basename(path)
    info = read_area(path)
    if info is None:
        print("SKIP    %s: no secure area" % name)
        return True
    code, idcode, off, area = info
    if area[:8] == DECRYPTED_MARK:
        print("OK      %s (%s): already decrypted" % (name, code))
        return True
    out = decrypt_area(table, area, idcode)
    if out[:8] != b"encryObj":
        print("FAILED  %s (%s): did not decrypt, ROM left unchanged" % (name, code))
        return False
    if dry_run:
        print("WOULD   %s (%s): needs decrypting" % (name, code))
        return True
    backup = backup_path(path)
    if os.path.exists(backup):
        print("FAILED  %s (%s): backup already exists, ROM left unchanged: %s" % (name, code, backup))
        return False
    os.makedirs(BACKUPS, exist_ok=True)
    with open(backup, "wb") as f:
        f.write(area)
    if not write_area(path, off, DECRYPTED_MARK + out[8:]):
        print("FAILED  %s (%s): write did not verify, restore from %s" % (name, code, backup))
        return False
    print("FIXED   %s (%s), backup: %s" % (name, code, backup))
    return True


def restore(path):
    name = os.path.basename(path)
    info = read_area(path)
    backup = backup_path(path)
    if info is None or not os.path.isfile(backup) or os.path.getsize(backup) != AREA_SIZE:
        print("FAILED  %s: no usable backup at %s" % (name, backup))
        return False
    with open(backup, "rb") as f:
        area = f.read()
    if not write_area(path, info[2], area):
        print("FAILED  %s: write did not verify" % name)
        return False
    os.remove(backup)
    print("RESTORED %s" % name)
    return True


def collect(targets):
    roms = []
    for target in targets:
        if os.path.isdir(target):
            roms += sorted(glob.glob(os.path.join(glob.escape(target), "*.nds")))
        elif os.path.isfile(target):
            roms.append(target)
        else:
            print("FAILED  %s: not found" % target)
    return roms


def main():
    parser = argparse.ArgumentParser(description="Decrypt the secure area of .nds ROMs.")
    parser.add_argument("targets", nargs="+", help=".nds files or folders holding them")
    parser.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    parser.add_argument("--restore", action="store_true", help="put the original bytes back from the backup")
    parser.add_argument("--key", help="file holding the key table: key1.bin, a DeSmuME exe or an ARM7 BIOS")
    args = parser.parse_args()

    roms = collect(args.targets)
    if args.restore:
        results = [restore(path) for path in roms]
    else:
        table = load_table(args.key)
        results = [patch(path, table, args.dry_run) for path in roms]
    if not roms or not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
