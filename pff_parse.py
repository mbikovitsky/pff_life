#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-

import io
import struct
from enum import Enum, auto
from typing import BinaryIO, Generator, NamedTuple, Optional

from dds import DDS_HEADER
from pff import PFF_FILE, VIDEO_DDS_FLAGS, VIDEO_DDS_METADATA


class VideoFormat(Enum):
    DDS = auto()


class SoundFormat(Enum):
    VORBIS = auto()


class SoundTrack(NamedTuple):
    format: SoundFormat
    language: str


class Frame(NamedTuple):
    timestamp: float
    video: Optional[bytes]
    sound: tuple[Optional[bytes], ...]


class PFF:
    def __init__(self, pff):
        self._pff = pff

        if pff.video:
            if pff.video.format != "VIDEO_DDS":
                raise NotImplementedError("Unsupported video format")
            self._video_format = VideoFormat.DDS
        else:
            self._video_format = None

        for track in pff.sound:
            if track.format != "SOUND_VORBIS":
                raise NotImplementedError(f"Unsupported audio format {track.format}")
        self._sound_tracks = tuple(
            SoundTrack(SoundFormat.VORBIS, track.language) for track in pff.sound
        )

    @staticmethod
    def parse_stream(stream: BinaryIO) -> "PFF":
        pff = PFF_FILE.parse_stream(stream)
        return PFF(pff)

    @property
    def video_format(self) -> Optional[VideoFormat]:
        return self._video_format

    @property
    def sound_tracks(self) -> tuple[SoundTrack, ...]:
        return self._sound_tracks

    @property
    def frames(self) -> Generator[Frame, None, None]:
        dds = None

        previous_frame = None

        for index, frame in enumerate(self._pff.frames):
            sound = [None] * len(self.sound_tracks)
            for track in frame.sound:
                sound[track.index] = track.data
            sound = tuple(sound)

            if frame.video:
                with io.BytesIO(frame.video.data) as video_stream:
                    if dds is None:
                        dds = _parse_dds_metadata(video_stream)

                    video_data = _decode_video_frame(video_stream, previous_frame)
                    previous_frame = video_data

                    video = b"DDS " + DDS_HEADER.build(dds) + video_data
            else:
                video = None

            yield Frame(frame.timestamp, video, sound)


def _parse_dds_metadata(stream: BinaryIO):
    dds = VIDEO_DDS_METADATA.parse_stream(stream).dds

    if not dds.ddspf.dwFlags & 0x4:  # DDPF_FOURCC
        raise ValueError("DDPF_FOURCC not set in video flags")

    if dds.ddspf.dwFourCC != "DXT1":
        raise NotImplementedError(
            f"Unsupported video frame compression '{dds.ddspf.dwFourCC}'"
        )

    return dds


def _decode_video_frame(
    stream: BinaryIO,
    previous_frame: Optional[bytes],
) -> bytes:
    flags = VIDEO_DDS_FLAGS.parse_stream(stream)

    if not flags.COMPRESSED:
        raise NotImplementedError("Uncompressed DDS frame")

    data = _decode_huffman(stream)

    if flags.TWO_PARTS and not flags.RLE:
        data += _decode_huffman(stream)

    if flags.RLE:
        data = _decode_rle(data)

    if flags.TWO_PARTS:
        data = _merge(data)

    if flags.INTERMEDIATE:
        assert previous_frame
        data = _xor_arrays(data, previous_frame)

    return data


def _decode_huffman(stream: BinaryIO) -> bytes:
    length = struct.unpack("<H", stream.read(2))[0]
    nodes = struct.unpack(f"<{length}H", stream.read(length * 2))

    decoded = bytearray()

    mask = 0
    bits = 0
    index = 0
    while True:
        if mask == 0:
            mask = 0x80000000
            bits = struct.unpack("<I", stream.read(4))[0]

        if bits & mask:
            index = nodes[index]
        else:
            index += 1

        if nodes[index] & 0x8000:
            value = nodes[index] & 0x1FF
            if value == 0x100:
                return decoded
            decoded.append(value)
            index = 0

        mask >>= 1


def _decode_rle(buffer: bytes) -> bytes:
    result = bytearray()

    index = 0
    while index < len(buffer):
        if buffer[index] & 0x80:
            result.extend(bytes(buffer[index] & 0x7F))
            index += 1
        else:
            result.extend(buffer[index + 1 : index + 1 + buffer[index]])
            index += 1 + buffer[index]

    return result


def _merge(buffer: bytes) -> bytes:
    # We should be able to split the buffer in two halves, and each half must
    # have a whole number of dwords
    assert len(buffer) % 8 == 0

    dwords = len(buffer) // 8
    first_part = struct.unpack_from(f"<{dwords}I", buffer)
    second_part = struct.unpack_from(f"<{dwords}I", buffer, len(buffer) // 2)

    merged = b"".join(struct.pack("<II", a, b) for a, b in zip(first_part, second_part))

    return merged


def _xor_arrays(first: bytes, second: bytes) -> bytes:
    assert len(first) == len(second)
    return bytes(a ^ b for a, b in zip(first, second))
