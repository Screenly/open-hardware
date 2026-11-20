#!/usr/bin/env bash
# Create the manufacturing files of a KiCad project with kicad-cli.
#
# Usage: ./create-manufacturing-files.sh PROJECT_DIR VARIANT
#   e.g. ./create-manufacturing-files.sh screenly-cm5-player/electronics eMMC
#
# Part numbers come from the project text variables (File > Project Setup >
# Text Variables): PCB_PN for the bare board, ESP_PN_<VARIANT> for the
# assembly of that variant. The revision comes from the board title block.
#
# Output, inside PROJECT_DIR/outputs:
#   manufacturing/pcb/<PCB_PN>.zip       Gerbers, drill files, job file and README.md,
#                                        ready to upload to a fab
#   manufacturing/assembly/<ESP_PN>.zip  BOM, HBOM (CycloneDX), pick-and-place files (CSV and
#                                        KiCad .pos), assembly drawing (PDF) and README.md
#   3d/<NAME>-<REV>.step.zip             STEP model of the board
#
# The run stops if ERC or DRC reports errors, or if the position file and the
# BOM don't list the same assembled parts.
#
# The HBOM takes the part attributes from the part database through
# tools/partsdb.py, so the tool must be able to reach the database. It needs
# cyclonedx-python-lib: on the first run the script installs it into .venv/ in
# the repository root (git-ignored). Set HBOM_PYTHON to use another Python.

set -euo pipefail

usage() { sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[ $# -eq 2 ] || usage

ROOT=$(cd "$(dirname "$0")" && pwd)
PROJECT_DIR=$(cd "$1" && pwd)
VARIANT=$2
HELPER="$ROOT/tools/manufacturing.py"

for tool in kicad-cli python3 zip; do
    command -v "$tool" >/dev/null || { echo "error: $tool not found" >&2; exit 1; }
done
if [ -z "${HBOM_PYTHON:-}" ]; then
    HBOM_PYTHON="$ROOT/.venv/bin/python"
    if ! "$HBOM_PYTHON" -c "import cyclonedx" 2>/dev/null; then
        echo "==> Installing cyclonedx-python-lib into .venv (first run only)"
        python3 -m venv "$ROOT/.venv"
        "$ROOT/.venv/bin/pip" install --quiet --disable-pip-version-check 'cyclonedx-python-lib[json-validation]'
    fi
fi
python3 "$ROOT/tools/partsdb.py" validate >/dev/null ||
    { echo "error: tools/partsdb.py cannot use the part database" >&2; exit 1; }
"$HBOM_PYTHON" -c "import cyclonedx" 2>/dev/null ||
    { echo "error: $HBOM_PYTHON has no cyclonedx-python-lib (set HBOM_PYTHON)" >&2; exit 1; }

eval "$(python3 "$HELPER" info "$PROJECT_DIR" "$VARIANT")"
echo "$TITLE $REV, variant $VARIANT: PCB $PCB_PN, assembly $ESP_PN"

OUT="$PROJECT_DIR/outputs"
PCB_DIR="$OUT/manufacturing/pcb/$PCB_PN"
ASM_DIR="$OUT/manufacturing/assembly/$ESP_PN"
STEP_FILE="$OUT/3d/$NAME-$REV.step.zip"
REPORTS=$(mktemp -d)
trap 'rm -rf "$REPORTS"' EXIT

step() { echo "==> $*"; }
start() { printf "==> %s ... " "$*"; }
pass() { echo "✓"; }
fail() { echo "✗"; }

# kicad-cli with wxWidgets' "Adding duplicate image handler" debug noise removed from stderr.
kicad_cli() {
    kicad-cli "$@" 2> >(grep -v 'Debug: Adding duplicate image handler' >&2)
}

start "ERC"
if ! kicad_cli sch erc --severity-error --exit-code-violations \
        -o "$REPORTS/erc.rpt" "$SCH" >/dev/null; then
    fail; cat "$REPORTS/erc.rpt"; echo "error: ERC reports errors" >&2; exit 1
fi
pass

start "DRC"
if ! kicad_cli pcb drc --severity-error --exit-code-violations --schematic-parity \
        -o "$REPORTS/drc.rpt" "$PCB" >/dev/null; then
    fail; cat "$REPORTS/drc.rpt"; echo "error: DRC reports errors" >&2; exit 1
fi
pass

step "Gerbers and drill files -> ${PCB_DIR#$PROJECT_DIR/}.zip"
rm -rf "$PCB_DIR" "$PCB_DIR.zip"
mkdir -p "$PCB_DIR"
kicad_cli pcb export gerbers --board-plot-params -o "$PCB_DIR/" "$PCB" >/dev/null
kicad_cli pcb export drill --format excellon --excellon-separate-th \
    --excellon-units mm --excellon-zeros-format decimal --excellon-oval-format route \
    --drill-origin absolute -o "$PCB_DIR/" "$PCB" >/dev/null
python3 "$HELPER" readme "$PROJECT_DIR" "$PCB_DIR"
(cd "$PCB_DIR" && zip -q -9 -j "../$PCB_PN.zip" ./*)
rm -rf "$PCB_DIR"

step "BOM, HBOM, pick-and-place, assembly drawing -> ${ASM_DIR#$PROJECT_DIR/}.zip"
rm -rf "$ASM_DIR" "$ASM_DIR.zip"
mkdir -p "$ASM_DIR"
kicad_cli sch export bom --variant "$VARIANT" \
    --fields "PartNumber,Reference,Value,Manufacturer,MfrPartNum,\${QUANTITY}" \
    --group-by PartNumber --sort-field PartNumber --sort-asc \
    --exclude-dnp --ref-range-delimiter "" \
    -o "$ASM_DIR/$ESP_PN-bom.csv" "$SCH" >/dev/null
kicad_cli sch export bom --variant "$VARIANT" \
    --fields "PartNumber,Reference,Value,Manufacturer,MfrPartNum,Description,Datasheet,\${QUANTITY}" \
    --group-by PartNumber --sort-field PartNumber --sort-asc \
    --exclude-dnp --ref-range-delimiter "" \
    -o "$REPORTS/hbom-source.csv" "$SCH" >/dev/null
"$HBOM_PYTHON" "$HELPER" hbom "$PROJECT_DIR" "$VARIANT" "$REPORTS/hbom-source.csv" "$ASM_DIR/$ESP_PN-hbom.cdx.json"
kicad_cli pcb export pos --variant "$VARIANT" --exclude-dnp --smd-only \
    --side both --format ascii --units mm \
    -o "$ASM_DIR/$ESP_PN.pos" "$PCB" >/dev/null
python3 "$HELPER" check-pos "$PROJECT_DIR" "$ASM_DIR/$ESP_PN.pos" "$ASM_DIR/$ESP_PN-bom.csv"
kicad_cli pcb export pos --variant "$VARIANT" --exclude-dnp --smd-only \
    --side both --format csv --units mm \
    -o "$ASM_DIR/$ESP_PN-cpl.csv" "$PCB" >/dev/null
python3 "$HELPER" cpl "$ASM_DIR/$ESP_PN-cpl.csv"
for side in $(python3 "$HELPER" sides "$ASM_DIR/$ESP_PN.pos"); do
    case $side in top) layers=F.Fab,F.Silkscreen ;; bottom) layers=B.Fab,B.Silkscreen ;; esac
    kicad_cli pcb export pdf --variant "$VARIANT" --layers "$layers,Edge.Cuts" \
        --include-border-title --black-and-white --exclude-value \
        --crossout-DNP-footprints-on-fab-layers \
        -o "$ASM_DIR/$ESP_PN-assembly-$side.pdf" "$PCB" >/dev/null
done
python3 "$HELPER" asm-readme "$PROJECT_DIR" "$VARIANT" "$ASM_DIR/$ESP_PN-bom.csv" "$ASM_DIR/$ESP_PN.pos" "$ASM_DIR"
(cd "$ASM_DIR" && zip -q -9 -j "../$ESP_PN.zip" ./*)
rm -rf "$ASM_DIR"

step "STEP model -> ${STEP_FILE#$PROJECT_DIR/}"
mkdir -p "$OUT/3d"
kicad_cli pcb export step -o "$REPORTS/$NAME-$REV.step" "$PCB" >/dev/null
rm -f "$STEP_FILE"
zip -q -9 -j "$STEP_FILE" "$REPORTS/$NAME-$REV.step"

step "Done"
