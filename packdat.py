#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-

import argparse
import glob
import os.path
import shutil
import sys
from pathlib import Path


KEY = bytes(
    [
        0x29,
        0x23,
        0xBE,
        0x84,
        0xE1,
        0x6C,
        0xD6,
        0xAE,
        0x52,
        0x90,
        0x49,
        0xF1,
        0xF1,
        0xBB,
        0xE9,
        0xEB,
    ]
)


class XORStream:
    def __init__(self, raw, key):
        self._raw = raw
        self._key = key

    def write(self, buffer):
        position = self._raw.tell()
        xored_buffer = bytes(
            byte ^ self._key[(position + index) % len(self._key)]
            for index, byte in enumerate(buffer)
        )
        return self._raw.write(xored_buffer)


def _main():
    args = _parse_command_line()

    archive_names, filenames = _get_input_files(args.input_directory)

    with open(args.output_filename, mode="wb") as output_file:
        output_file = XORStream(output_file, KEY)

        output_file.write(b"GMGB")
        output_file.write(len(archive_names).to_bytes(4, "little"))

        for archive_name, filename in zip(archive_names, filenames):
            output_file.write(archive_name.encode("ASCII") + b"\x00")
            output_file.write(os.path.getsize(filename).to_bytes(4, "little"))

        for archive_name, filename in zip(archive_names, filenames):
            with open(filename, mode="rb") as input_file:
                shutil.copyfileobj(input_file, output_file)


def _get_input_files(directory: str) -> tuple[list[str], list[str]]:
    # Get all files in the source directory
    filenames = glob.iglob("**", root_dir=directory, recursive=True)

    # Filter out the directories
    filenames = [
        filename
        for filename in filenames
        if not os.path.isdir(os.path.join(directory, filename))
    ]

    # Convert to absolute POSIX paths
    archive_names = ["/" + Path(filename).as_posix() for filename in filenames]

    # Create filenames that we can open
    filenames = [os.path.join(directory, filename) for filename in filenames]

    return archive_names, filenames


def _parse_command_line() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input_directory", help="Directory containing the files to pack"
    )
    parser.add_argument("output_filename", help="Name of the file to pack into")

    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(_main())
