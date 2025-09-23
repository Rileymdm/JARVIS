# Thrust Curves

Use this folder to store motor thrust curves for the simulation.

Supported formats:
- CSV: Two columns: time (s), thrust (N). A header row is optional. Extra columns are ignored.
- RASP/ENG: Standard .eng format used by RASP/ThrustCurve.org. Comments start with `;` or `#`. We parse the first motor block. Header fields are ignored; only the following time/thrust pairs are read.

Folder layout:
- `csv/` — CSV thrust curves
- `rasp/` — RASP/ENG thrust curves (.eng or .rasp)

Examples are provided in each subfolder.
