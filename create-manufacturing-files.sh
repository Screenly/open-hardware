#!/usr/bin/env bash
# Create the manufacturing files of a KiCad project with kicad-cli.
#
# Usage: ./create-manufacturing-files.sh --project=DIR --variant=NAME
#            [--distributors=LIST] [--strict] [--db=DIR]
#   e.g. ./create-manufacturing-files.sh --project=screenly-cm5-player/electronics \
#            --variant=eMMC --distributors=LCSC,DigiKey
#
#   --project=DIR         KiCad project folder (required)
#   --variant=NAME        assembly variant (required)
#   --distributors=LIST   comma-separated distributor preference list. Parts sold
#                         by an earlier distributor in the list are picked first,
#                         see "Parts" below. A part with none of them gets its
#                         own preferred distributor, reported as a fallback.
#                         Without it, each part gets its own preferred one.
#                         Names come from the distributor table of the part
#                         database (partsdb.py distributors list), not
#                         case-sensitive.
#   --strict              stop instead of falling back, or when a part has no
#                         distributor
#   --db=DIR              part database folder; default: the PARTSDB_DIR
#                         environment variable
#   --help                show this help
#
# Part numbers come from the project text variables (File > Project Setup >
# Text Variables): PCB_PN for the bare board, ESP_PN_<VARIANT> for the
# assembly of that variant. The revision comes from the board title block.
#
# Output, inside PROJECT_DIR/outputs:
#   manufacturing/pcb/<PCB_PN>.zip       Gerbers, drill files, job file and README.md,
#                                        ready to upload to a fab
#   manufacturing/assembly/<ESP_PN>.zip  BOM, HBOM (CycloneDX), pick-and-place files (CSV and
#                                        KiCad .pos), assembly drawing (PDF) and README.md.
#                                        The BOM is <ESP_PN>-bom.csv, or with --distributors
#                                        the list in lowercase, e.g. <ESP_PN>-bom-lcsc-digikey.csv
#   3d/<NAME>-<REV>.step.zip             STEP model of the board
#
# Parts: for each assembled symbol, the candidates are the approved parts (library
# symbols with a part number in the part database) of its class that fit its
# footprint and meet its class key fields, e.g. a `family` pattern such as
# SLB9672?U20FW1624XTMA1 (docs/part-library-standard.md). The pick is the part
# sold by the earliest distributor in --distributors, then the design's own part,
# then the part that fits the most symbols, then the lowest part number. Every
# substitution is listed in the output.
#
# The run stops if ERC or DRC reports errors, or if the position file and the
# BOM don't list the same assembled parts.
#
# The HBOM takes the part attributes from the part database through
# tools/partsdb.py, so the tool must be able to reach the database. It needs
# cyclonedx-python-lib: on the first run the script installs it into .venv/ in
# the repository root (git-ignored). Set HBOM_PYTHON to use another Python.

set -euo pipefail

usage() { sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }
die() { echo "error: $*" >&2; exit 2; }

PROJECT_DIR="" VARIANT="" DISTRIBUTORS="" STRICT=0
while [ $# -gt 0 ]; do
    case $1 in
        --project=*) PROJECT_DIR=${1#*=} ;;
        --variant=*) VARIANT=${1#*=} ;;
        --distributors=*) DISTRIBUTORS=${1#*=} ;;
        --db=*) PARTSDB_DIR=${1#*=} ;;
        --project|--variant|--distributors|--db)
            [ $# -ge 2 ] || die "$1 needs a value"
            case $1 in
                --project) PROJECT_DIR=$2 ;;
                --variant) VARIANT=$2 ;;
                --distributors) DISTRIBUTORS=$2 ;;
                --db) PARTSDB_DIR=$2 ;;
            esac
            shift ;;
        --strict) STRICT=1 ;;
        -h|--help) usage 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage ;;
    esac
    shift
done
[ -n "$PROJECT_DIR" ] || die "--project is required (see --help)"
[ -n "$VARIANT" ] || die "--variant is required (see --help)"
[ -d "$PROJECT_DIR" ] || die "project folder not found: $PROJECT_DIR"
if [ -n "${PARTSDB_DIR:-}" ]; then
    [ -d "$PARTSDB_DIR" ] || die "part database folder not found: $PARTSDB_DIR"
    PARTSDB_DIR=$(cd "$PARTSDB_DIR" && pwd)
    export PARTSDB_DIR
fi

ROOT=$(cd "$(dirname "$0")" && pwd)
PROJECT_DIR=$(cd "$PROJECT_DIR" && pwd)
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

# Plain assignments, so set -e stops the run when a helper fails.
INFO=$(python3 "$HELPER" info "$PROJECT_DIR" "$VARIANT")
eval "$INFO"
echo "$TITLE $REV, variant $VARIANT: PCB $PCB_PN, assembly $ESP_PN"

OUT="$PROJECT_DIR/outputs"
PCB_DIR="$OUT/manufacturing/pcb/$PCB_PN"
ASM_DIR="$OUT/manufacturing/assembly/$ESP_PN"
STEP_FILE="$OUT/3d/$NAME-$REV.step.zip"
# The distributor list is part of the BOM name, lowercase: LCSC,DigiKey -> <ESP_PN>-bom-lcsc-digikey.csv
BOM_SUFFIX=$(printf '%s' "$DISTRIBUTORS" | tr '[:upper:]' '[:lower:]' | tr -d ' ' | tr -s ',' | sed 's/^,//; s/,$//; s/,/-/g')
BOM_FILE="$ASM_DIR/$ESP_PN-bom${BOM_SUFFIX:+-$BOM_SUFFIX}.csv"
REPORTS=$(mktemp -d)
trap 'rm -rf "$REPORTS"' EXIT

step() { echo "==> $*"; }

# kicad-cli with wxWidgets' "Adding duplicate image handler" debug noise removed from stderr.
kicad_cli() {
    kicad-cli "$@" 2> >(grep -v 'Debug: Adding duplicate image handler' >&2)
}

"$ROOT/check-erc-drc.sh" --project="$PROJECT_DIR"

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
# One row per assembled symbol with its class key fields; the resolver picks the parts.
FIELDS=$(python3 "$HELPER" key-fields)
kicad_cli sch export bom --variant "$VARIANT" \
    --fields "$FIELDS" \
    --sort-field Reference --sort-asc \
    --exclude-dnp --ref-range-delimiter "" \
    -o "$REPORTS/instances.csv" "$SCH" >/dev/null
python3 "$HELPER" resolve "$REPORTS/instances.csv" "$DISTRIBUTORS" "$STRICT" \
    "$BOM_FILE" "$REPORTS/hbom-source.csv"
"$HBOM_PYTHON" "$HELPER" hbom "$PROJECT_DIR" "$VARIANT" "$REPORTS/hbom-source.csv" "$ASM_DIR/$ESP_PN-hbom.cdx.json"
kicad_cli pcb export pos --variant "$VARIANT" --exclude-dnp --smd-only \
    --side both --format ascii --units mm \
    -o "$ASM_DIR/$ESP_PN.pos" "$PCB" >/dev/null
python3 "$HELPER" check-pos "$PROJECT_DIR" "$ASM_DIR/$ESP_PN.pos" "$BOM_FILE"
kicad_cli pcb export pos --variant "$VARIANT" --exclude-dnp --smd-only \
    --side both --format csv --units mm \
    -o "$ASM_DIR/$ESP_PN-cpl.csv" "$PCB" >/dev/null
python3 "$HELPER" cpl "$ASM_DIR/$ESP_PN-cpl.csv"
SIDES=$(python3 "$HELPER" sides "$ASM_DIR/$ESP_PN.pos")
for side in $SIDES; do
    case $side in top) layers=F.Fab,F.Silkscreen ;; bottom) layers=B.Fab,B.Silkscreen ;; esac
    kicad_cli pcb export pdf --variant "$VARIANT" --layers "$layers,Edge.Cuts" \
        --include-border-title --black-and-white --exclude-value \
        --crossout-DNP-footprints-on-fab-layers \
        -o "$ASM_DIR/$ESP_PN-assembly-$side.pdf" "$PCB" >/dev/null
done
python3 "$HELPER" asm-readme "$PROJECT_DIR" "$VARIANT" "$BOM_FILE" "$ASM_DIR/$ESP_PN.pos" "$ASM_DIR"
(cd "$ASM_DIR" && zip -q -9 -j "../$ESP_PN.zip" ./*)
rm -rf "$ASM_DIR"

step "STEP model -> ${STEP_FILE#$PROJECT_DIR/}"
mkdir -p "$OUT/3d"
kicad_cli pcb export step -o "$REPORTS/$NAME-$REV.step" "$PCB" >/dev/null
rm -f "$STEP_FILE"
zip -q -9 -j "$STEP_FILE" "$REPORTS/$NAME-$REV.step"

step "Done"
