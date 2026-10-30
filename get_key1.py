#!/usr/bin/env python3
"""Download the latest DeSmuME release, extract the DS KEY1 table into key1.bin, delete the download.

The exe is only read from the zip as data. It is never unpacked to disk or run.
"""
import argparse
import json
import os
import sys
import tempfile
import urllib.request
import zipfile

sys.dont_write_bytecode = True
from extract_key1 import KEY_FILE, find_in_bytes

RELEASE_API = "https://api.github.com/repos/TASEmulators/desmume/releases/latest"
MAX_EXE_SIZE = 256 * 1024 * 1024


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "hails-patcher"})
    return urllib.request.urlopen(request, timeout=60)


def windows_zip(release):
    for asset in release["assets"]:
        name = asset["name"].lower()
        if name.endswith(".zip") and "win64" in name:
            return asset
    raise ValueError("release %s has no Windows x64 zip" % release.get("tag_name"))


def download_table():
    """Returns the table's bytes. Raises OSError or ValueError if it can't get them."""
    with fetch(RELEASE_API) as response:
        release = json.load(response)
    asset = windows_zip(release)
    print("Downloading DeSmuME %s: %s" % (release["tag_name"], asset["name"]))
    with tempfile.TemporaryDirectory(prefix="hails-patcher-") as tmp:
        path = os.path.join(tmp, "desmume.zip")
        with fetch(asset["browser_download_url"]) as response, open(path, "wb") as f:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        if os.path.getsize(path) != asset["size"]:
            raise ValueError("download is incomplete")
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if info.filename.lower().endswith(".exe") and info.file_size <= MAX_EXE_SIZE:
                        table = find_in_bytes(archive.read(info))
                        if table:
                            return table
        except zipfile.BadZipFile as error:
            raise ValueError("download is not a valid zip: %s" % error)
    raise ValueError("no key table in %s" % asset["name"])


def save_table(table, out=KEY_FILE):
    with open(out, "wb") as f:
        f.write(table)
    print("Wrote %s (%d bytes)" % (out, len(table)))


def main():
    parser = argparse.ArgumentParser(description="Get key1.bin from the latest DeSmuME release.")
    parser.add_argument("--out", default=KEY_FILE, help="where to write (default: key1.bin here)")
    parser.add_argument("--force", action="store_true", help="replace the file if it already exists")
    args = parser.parse_args()

    if os.path.exists(args.out) and not args.force:
        sys.exit("%s already exists. Use --force to replace it." % args.out)
    try:
        save_table(download_table(), args.out)
    except (OSError, ValueError) as error:
        sys.exit("Could not get the key table: %s" % error)


if __name__ == "__main__":
    main()
