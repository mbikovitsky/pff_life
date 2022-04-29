# PFF Life

Various Python scripts to assist in working with Still Life 2 .PFF files.

- `pff_life.py` can extract all frames and audio from a PFF file, and optionally
  invoke FFmpeg to convert the extracted data to a playable video file.
  Kinda slow.
- `packdat.py` can pack a directory into a `.DAT` archive that the game uses
  for storing it its assets. Really slow.

Run the scripts with `--help` for usage. Or read their code. Their hacky and ugly,
though.
