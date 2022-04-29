#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-

from construct import Const, Int32ul, PaddedString, Struct, Padding


DDS_PIXELFORMAT = Struct(
    Const(32, Int32ul),
    "dwFlags" / Int32ul,
    "dwFourCC" / PaddedString(4, "ASCII"),
    "dwRGBBitCount" / Int32ul,
    "dwRBitMask" / Int32ul,
    "dwGBitMask" / Int32ul,
    "dwBBitMask" / Int32ul,
    "dwABitMask" / Int32ul,
)

DDS_HEADER = Struct(
    Const(124, Int32ul),
    "dwFlags" / Int32ul,
    "dwHeight" / Int32ul,
    "dwWidth" / Int32ul,
    "dwPitchOrLinearSize" / Int32ul,
    "dwDepth" / Int32ul,
    "dwMipMapCount" / Int32ul,
    Padding(11 * 4),
    "ddspf" / DDS_PIXELFORMAT,
    "dwCaps" / Int32ul,
    "dwCaps2" / Int32ul,
    "dwCaps3" / Int32ul,
    "dwCaps4" / Int32ul,
    Padding(4),
)
