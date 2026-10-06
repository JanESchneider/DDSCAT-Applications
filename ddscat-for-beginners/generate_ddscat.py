"""
Generate ddscat.par and prepare a DDSCAT run directory.

Normally, you do NOT need to edit this file.
For a new simulation, change the values in input.toml instead.
"""

from pathlib import Path
import shutil
import sys
import tomllib

if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 generate_ddscat.py input.toml")

# ---------------------------------------------------------------------------
# Read configuration
# ---------------------------------------------------------------------------

config_file = Path(sys.argv[1]).expanduser().resolve()

with config_file.open("rb") as file:
    cfg = tomllib.load(file)

paths = cfg["paths"]
target = cfg["target"]
radius = cfg["effective_radius"]
wavelength = cfg["wavelength"]
numerics = cfg["numerics"]
orientation = cfg["orientation"]
output_cfg = cfg["output"]
scattering = cfg["scattering"]

# ---------------------------------------------------------------------------
# Helper for paths
# ---------------------------------------------------------------------------

def resolve_from_config(path_string: str) -> Path:
    """Expand '~' and resolve relative paths relative to input.toml."""
    path = Path(path_string).expanduser()
    if not path.is_absolute():
        path = config_file.parent / path
    return path.resolve()

# ---------------------------------------------------------------------------
# Prepare run directory
# ---------------------------------------------------------------------------

run_directory = resolve_from_config(paths["run_directory"])
run_directory.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Copy dielectric file
# ---------------------------------------------------------------------------

material_source = resolve_from_config(paths["material_file"])

if not material_source.is_file():
    raise FileNotFoundError(f"Material file not found: {material_source}")

shutil.copy2(material_source, run_directory / "diel.dat")

# ---------------------------------------------------------------------------
# Target geometry
# ---------------------------------------------------------------------------

shape = target["shape"].upper()

if shape == "FROM_FILE":
    shape_source = resolve_from_config(target["shape_file"])

    if not shape_source.is_file():
        raise FileNotFoundError(f"Shape file not found: {shape_source}")

    shutil.copy2(shape_source, run_directory / "shape.dat")
    shape_block = "'FROM_FILE' = CSHAPE\n"

elif shape == "ELLIPSOID":
    sx, sy, sz = target["shape_parameters"]
    shape_block = (
        "'ELLIPSOID' = CSHAPE\n"
        f"{sx} {sy} {sz}\n"
    )

else:
    raise ValueError(f"Unsupported target shape: {shape}")

# ---------------------------------------------------------------------------
# Numerical parameters
# ---------------------------------------------------------------------------

memory = numerics["memory"]

if len(memory) != 3:
    raise ValueError("numerics.memory must contain exactly 3 values")

nearfield = 1 if numerics["nearfield"] else 0

# ---------------------------------------------------------------------------
# Orientation
# ---------------------------------------------------------------------------

beta = orientation["beta"]
theta = orientation["theta"]
phi = orientation["phi"]

for name, values in (("beta", beta), ("theta", theta), ("phi", phi)):
    if len(values) != 3:
        raise ValueError(
            f"orientation.{name} must contain [minimum, maximum, count]"
        )

# ---------------------------------------------------------------------------
# Mueller matrix output
# ---------------------------------------------------------------------------

mueller_elements = output_cfg["mueller_elements"]

if not mueller_elements:
    raise ValueError(
        "output.mueller_elements must contain at least one element"
    )

# ---------------------------------------------------------------------------
# Scattering directions
# ---------------------------------------------------------------------------

planes = scattering["planes"]

if not planes:
    raise ValueError(
        "scattering.planes must contain at least one scattering plane"
    )

for plane in planes:
    if len(plane) != 4:
        raise ValueError(
            "Each scattering.plane must contain "
            "[phi, theta_min, theta_max, theta_step]"
        )

plane_lines = "\n".join(
    " ".join(str(value) for value in plane)
    for plane in planes
)

# ---------------------------------------------------------------------------
# Build ddscat.par
# ---------------------------------------------------------------------------

text = f"""'========== Parameter file for DDSCAT 7.3 =========='
'**** Preliminaries ****'
'NOTORQ' = CMDTRQ
'{numerics["solver"]}' = CMDSOL
'{numerics["fft"]}' = CMDFFT
'{numerics["polarizability"]}' = CALPHA
'NOTBIN' = CBINFLAG
'**** Initial Memory Allocation ****'
{memory[0]} {memory[1]} {memory[2]}
'**** Target Geometry and Composition ****'
{shape_block}1 = NCOMP
'diel.dat'
'**** Additional Nearfield calculation? ****'
{nearfield} = NRFLD
0.0 0.0 0.0 0.0 0.0 0.0
'**** Error Tolerance ****'
{numerics["tolerance"]} = TOL
'**** Maximum number of iterations ****'
{numerics["max_iterations"]} = MXITER
'**** Interaction cutoff parameter ****'
{numerics["gamma"]} = GAMMA
'**** Angular resolution ****'
{numerics["eta_sca"]} = ETASCA
'**** Vacuum wavelengths (micron) ****'
{wavelength["minimum_um"]} {wavelength["maximum_um"]} {wavelength["count"]} '{wavelength["spacing"]}'
'**** Refractive index of ambient medium ****'
{numerics["ambient_refractive_index"]} = NAMBIENT
'**** Effective Radii (micron) ****'
{radius["minimum_um"]} {radius["maximum_um"]} {radius["count"]} '{radius["spacing"]}'
'**** Define Incident Polarizations ****'
(0,0) (1.,0.) (0.,0.)
{output_cfg["iorth"]} = IORTH
'**** Specify which output files to write ****'
{output_cfg["write_sca"]} = IWRKSC
'**** Prescribe Target Rotations ****'
{beta[0]} {beta[1]} {beta[2]} = BETAMI BETAMX NBETA
{theta[0]} {theta[1]} {theta[2]} = THETMI THETMX NTHETA
{phi[0]} {phi[1]} {phi[2]} = PHIMIN PHIMAX NPHI
'**** Specify first IWAV, IRAD, IORI ****'
0 0 0
'**** Select Elements of S_ij Matrix to Print ****'
{len(mueller_elements)} = NSMELTS
{" ".join(str(value) for value in mueller_elements)}
'**** Specify Scattered Directions ****'
'{scattering["frame"]}'
{len(planes)}
{plane_lines}
"""

# ---------------------------------------------------------------------------
# Write ddscat.par
# ---------------------------------------------------------------------------

output_file = run_directory / "ddscat.par"
output_file.write_text(text)

print(f"Wrote {output_file}")