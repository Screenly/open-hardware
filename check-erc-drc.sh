#!/usr/bin/env bash
# Run ERC and DRC on a KiCad project with kicad-cli.
#
# Usage: ./check-erc-drc.sh --project=DIR
#   e.g. ./check-erc-drc.sh --project=screenly-cm5-player/electronics
#
#   --project=DIR   KiCad project folder with exactly one .kicad_pro (required)
#   --help          show this help
#
# ERC checks the schematic; DRC checks the board, including parity with the
# schematic. Only errors fail the check, warnings are ignored. The exit status
# is 1 if either check reports errors, and the reports are printed.

set -euo pipefail

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-2}"; }
die() { echo "error: $*" >&2; exit 2; }

PROJECT_DIR=""
while [ $# -gt 0 ]; do
    case $1 in
        --project=*) PROJECT_DIR=${1#*=} ;;
        --project) [ $# -ge 2 ] || die "--project needs a value"; PROJECT_DIR=$2; shift ;;
        -h|--help) usage 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage ;;
    esac
    shift
done
[ -n "$PROJECT_DIR" ] || die "--project is required (see --help)"
[ -d "$PROJECT_DIR" ] || die "project folder not found: $PROJECT_DIR"

shopt -s nullglob
pros=("$PROJECT_DIR"/*.kicad_pro)
[ ${#pros[@]} -eq 1 ] || die "expected exactly one .kicad_pro in $PROJECT_DIR, found ${#pros[@]}"
SCH=${pros[0]%.kicad_pro}.kicad_sch
PCB=${pros[0]%.kicad_pro}.kicad_pcb
[ -f "$SCH" ] || die "missing $SCH"
[ -f "$PCB" ] || die "missing $PCB"
command -v kicad-cli >/dev/null || { echo "error: kicad-cli not found" >&2; exit 1; }

REPORTS=$(mktemp -d)
trap 'rm -rf "$REPORTS"' EXIT

# kicad-cli with wxWidgets' "Adding duplicate image handler" debug noise removed from stderr.
kicad_cli() {
    kicad-cli "$@" 2> >(grep -v 'Debug: Adding duplicate image handler' >&2)
}

status=0

printf "==> ERC ... "
if kicad_cli sch erc --severity-error --exit-code-violations -o "$REPORTS/erc.rpt" "$SCH" >/dev/null; then
    echo "✓"
else
    echo "✗"; cat "$REPORTS/erc.rpt"; echo "error: ERC reports errors" >&2; status=1
fi

printf "==> DRC ... "
if kicad_cli pcb drc --severity-error --exit-code-violations --schematic-parity \
        -o "$REPORTS/drc.rpt" "$PCB" >/dev/null; then
    echo "✓"
else
    echo "✗"; cat "$REPORTS/drc.rpt"; echo "error: DRC reports errors" >&2; status=1
fi

exit $status
