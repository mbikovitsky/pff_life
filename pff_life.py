#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-

import argparse
import glob
import math
import os
import os.path
import shutil
import sys
from contextlib import ExitStack
from typing import BinaryIO, Optional

import ffmpeg

from pff_parse import PFF, SoundFormat, VideoFormat


def _main():
    args = _parse_command_line()
    args.func(args)


def _handle_extract(args):
    framerate, _ = _extract(args.input_filename, args.output_directory)
    print(f"FPS: {framerate}")


def _handle_convert(args):
    temp_directory = os.path.splitext(args.output_filename)[0]
    os.mkdir(temp_directory)
    try:
        framerate, filename_prefix = _extract(args.input_filename, temp_directory)

        inputs = [ffmpeg.input(f"{filename_prefix}_%d.dds", framerate=framerate)]

        inputs.extend(
            ffmpeg.input(audio_filename)
            for audio_filename in glob.iglob(f"{filename_prefix}*.ogg")
        )

        command = ffmpeg.output(
            *inputs,
            args.output_filename,
            vcodec="libx265" if args.x265 else "libx264",
            crf=args.crf,
            preset=args.preset,
            acodec="copy",
        )

        command.run()
    finally:
        shutil.rmtree(temp_directory)


def _extract(input_filename: str, output_directory: str) -> tuple[float, str]:
    with open(input_filename, mode="rb") as input_file:
        pff = PFF.parse_stream(input_file)

    assert pff.video_format == VideoFormat.DDS

    all(track.format == SoundFormat.VORBIS for track in pff.sound_tracks)

    filename_prefix = os.path.join(
        output_directory,
        os.path.splitext(os.path.basename(input_filename))[0],
    )

    with ExitStack() as stack:
        sound_files = []
        for index, track in enumerate(pff.sound_tracks):
            sound_files.append(
                stack.enter_context(
                    open(f"{filename_prefix}_{track.language}_{index}.ogg", mode="wb")
                )
            )
        framerate = _process_frames(pff, sound_files, filename_prefix)

    if framerate is None:
        raise ValueError("Non-constant framerate!")

    return framerate, filename_prefix


def _process_frames(
    pff: PFF, sound_files: list[BinaryIO], filename_prefix: str
) -> Optional[float]:
    timestamps = []
    image = None
    eof = False
    for index, frame in enumerate(pff.frames):
        if eof:
            raise ValueError(f"Unexpected frame at index {index}")

        timestamps.append(frame.timestamp)

        # If no video in this frame, just repeat the previous one
        # Reason: the last frame in CIN001.PFF has audio only
        if frame.video:
            image = frame.video
        with open(f"{filename_prefix}_{index}.dds", mode="wb") as frame_file:
            frame_file.write(image)

        assert len(frame.sound) == len(sound_files)
        for sound_data, sound_file in zip(frame.sound, sound_files):
            if sound_data:
                sound_file.write(sound_data)

        if not frame.video and not frame.sound:
            eof = True
            continue  # This will check that there are no more frames

    frame_durations = [
        timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))
    ]

    # Yeah, assuming that there're at least two frames
    if all(math.isclose(duration, frame_durations[0]) for duration in frame_durations):
        return 1 / frame_durations[0]
    else:
        return None


def _parse_command_line() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("input_filename", help="Input PFF file")

    subparsers = parser.add_subparsers(required=True)

    parser_extract = subparsers.add_parser("extract", help="Extract frames and sound")

    parser_extract.add_argument("output_directory", help="Output directory")

    parser_extract.set_defaults(func=_handle_extract)

    parser_convert = subparsers.add_parser("convert", help="Convert to video")

    parser_convert.add_argument("output_filename", help="Name of the output file")

    parser_convert.add_argument(
        "--x265", action="store_true", help="Use x265 instead of x264"
    )

    presets = [
        "ultrafast",
        "superfast",
        "veryfast",
        "faster",
        "fast",
        "medium",
        "slow",
        "slower",
        "veryslow",
        "placebo",
    ]
    parser_convert.add_argument(
        "--preset", choices=presets, default="medium", help="x264/x265 preset"
    )

    parser_convert.add_argument(
        "--crf", type=int, default=23, help="x264/x265 CRF value"
    )

    parser_convert.set_defaults(func=_handle_convert)

    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(_main())
