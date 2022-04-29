#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-

from construct import (
    Byte,
    Bytes,
    Check,
    Const,
    CString,
    Float64l,
    GreedyRange,
    Int32ul,
    Optional,
    Struct,
    this,
    FlagsEnum,
)

from dds import DDS_HEADER


PFF_FILE = Struct(
    Const("PFF0.0", CString("ASCII")),
    "video"
    / Optional(
        Struct(
            "format" / CString("ASCII"),
            Check(lambda ctx: ctx.format.startswith("VIDEO_")),
        )
    ),
    "sound"
    / GreedyRange(
        Struct(
            "format" / CString("ASCII"),
            Check(lambda ctx: ctx.format.startswith("SOUND_")),
            "language" / CString("ASCII"),
        ),
    ),
    Const("ENDHEADER", CString("ASCII")),
    "frames"
    / GreedyRange(
        Struct(
            Const("FRAME", CString("ASCII")),
            "size" / Int32ul,
            "timestamp" / Float64l,
            "video"
            / Optional(
                Struct(
                    Const("VIDEO", CString("ASCII")),
                    "size" / Int32ul,
                    "data" / Bytes(this.size),
                )
            ),
            "sound"
            / GreedyRange(
                Struct(
                    Const("SOUND", CString("ASCII")),
                    "size" / Int32ul,
                    "index" / Byte,
                    "data" / Bytes(this.size - 1),
                ),
            ),
            Const("ENDFRAME", CString("ASCII")),
        ),
    ),
    Const("ENDFILE", CString("ASCII")),
)

VIDEO_DDS_METADATA = Struct(
    "decompressed_size" / Int32ul,
    Const(b"DDS "),
    "dds" / DDS_HEADER,
)

VIDEO_DDS_FLAGS = FlagsEnum(Byte, INTERMEDIATE=1, COMPRESSED=2, RLE=4, TWO_PARTS=8)
