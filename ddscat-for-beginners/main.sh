#!/bin/bash

# ---------------------------------------------------------------------------
# Slurm settings
#
# These lines are used when running:
#
#     sbatch main.sh input.toml
#
# They are ignored when running:
#
#     bash main.sh input.toml
# ---------------------------------------------------------------------------

#SBATCH --job-name=ddscat
#SBATCH --partition=student-l
#SBATCH --qos=long

#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

#SBATCH --time=1-00:00:00
#SBATCH --mem=8G


# ---------------------------------------------------------------------------
# Shell settings
# ---------------------------------------------------------------------------

set -euo pipefail


# ---------------------------------------------------------------------------
# Check command-line argument
# ---------------------------------------------------------------------------

if [ "$#" -ne 1 ]; then

    echo "Usage:"
    echo "    bash main.sh input.toml"
    echo
    echo "or:"
    echo "    sbatch main.sh input.toml"

    exit 1

fi


# ---------------------------------------------------------------------------
# Determine repository directory
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"


# ---------------------------------------------------------------------------
# Resolve configuration file
# ---------------------------------------------------------------------------

CONFIG="$1"

if [[ "$CONFIG" != /* ]]; then
    CONFIG="$(pwd)/$CONFIG"
fi


if [ ! -f "$CONFIG" ]; then

    echo "ERROR: configuration file not found:"
    echo "       $CONFIG" >&2

    exit 1

fi


# ---------------------------------------------------------------------------
# Generate DDSCAT input files
# ---------------------------------------------------------------------------

python3 "$SCRIPT_DIR/generate_ddscat.py" "$CONFIG"


# ---------------------------------------------------------------------------
# Read and resolve paths from input.toml
#
# Python is used here so that:
#
#     ~
#
# is correctly expanded and relative paths are interpreted relative to
# input.toml.
# ---------------------------------------------------------------------------

mapfile -t PATHS < <(

    python3 - "$CONFIG" <<'PY'

from pathlib import Path
import sys
import tomllib


config_file = Path(sys.argv[1]).expanduser().resolve()

with config_file.open("rb") as file:
    cfg = tomllib.load(file)


def resolve_from_config(value):

    path = Path(value).expanduser()

    if not path.is_absolute():
        path = config_file.parent / path

    return path.resolve()


print(
    resolve_from_config(
        cfg["paths"]["run_directory"]
    )
)

print(
    resolve_from_config(
        cfg["paths"]["ddscat_executable"]
    )
)

PY

)


RUN_DIRECTORY="${PATHS[0]}"
DDSCAT_EXECUTABLE="${PATHS[1]}"


# ---------------------------------------------------------------------------
# Check paths
# ---------------------------------------------------------------------------

if [ ! -d "$RUN_DIRECTORY" ]; then

    echo "ERROR: run directory not found:"
    echo "       $RUN_DIRECTORY" >&2

    exit 1

fi


if [ ! -x "$DDSCAT_EXECUTABLE" ]; then

    echo "ERROR: DDSCAT executable not found or not executable:"
    echo "       $DDSCAT_EXECUTABLE" >&2

    exit 1

fi


# ---------------------------------------------------------------------------
# Information
# ---------------------------------------------------------------------------

echo
echo "============================================================"
echo "DDSCAT run"
echo "============================================================"
echo "Configuration : $CONFIG"
echo "Run directory : $RUN_DIRECTORY"
echo "DDSCAT binary : $DDSCAT_EXECUTABLE"
echo "============================================================"
echo


# ---------------------------------------------------------------------------
# Run DDSCAT
#
# DDSCAT expects ddscat.par in the current working directory.
# ---------------------------------------------------------------------------

cd "$RUN_DIRECTORY"

"$DDSCAT_EXECUTABLE"


# ---------------------------------------------------------------------------
# Finished
# ---------------------------------------------------------------------------

echo
echo "============================================================"
echo "DDSCAT finished"
echo "============================================================"