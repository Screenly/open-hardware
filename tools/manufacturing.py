#!/usr/bin/env python3
"""Helpers for create-manufacturing-files.sh.

  info PROJECT_DIR VARIANT   print shell variables for the script
  readme PROJECT_DIR OUT_DIR write the PCB fabrication README from the design
                             files and the exported Gerber/drill files
  check-pos PROJECT_DIR POS BOM
                             check that the position file and the BOM list the
                             same assembled parts
  cpl CSV                    rename the columns of KiCad's CSV position file
                             to the common pick-and-place names, in place
  sides POS                  print the board sides that have placements
  asm-readme PROJECT_DIR VARIANT BOM POS OUT_DIR
                             write the assembly README from the design files,
                             the BOM and the position file
  check-class-keys           check that the key tables of docs/part-library-standard.md
                             and library/class-keys.json agree
  key-fields                 print the fields of the per-instance BOM export:
                             the KiCad fields the resolver reads and every class
                             key of library/class-keys.json
  resolve INSTANCES PREFERENCE STRICT BOM HBOM_SOURCE
                             pick a part for each assembled instance (one CSV row
                             per instance, with the key-fields columns) and write
                             the BOM, one line per part number with its
                             distributor, and the HBOM source. Candidates are
                             approved parts of the instance's class that fit its
                             footprint and meet its class key fields. Selection:
                             the earliest distributor in PREFERENCE (a
                             comma-separated list, "" for none), then the
                             design's own part, then the part that fits the most
                             instances, then the lowest part number. A part with
                             none of the listed distributors gets its own
                             preferred one (marked fallback); STRICT=1 fails
                             instead.
  hbom PROJECT_DIR VARIANT BOM OUT_JSON
                             write the CycloneDX 1.6 HBOM of the assembly from
                             the BOM (with Description and Datasheet columns)
                             and the part attributes, read from the part
                             database with tools/partsdb.py; needs
                             cyclonedx-python-lib

Every value in the README comes from the source: the board file (title block,
stackup, finish, outline, net classes, zones), the project file (net class
rules and FAB_* text variables) and the exported fabrication files. Facts that
KiCad can't store are project text variables, see FAB_ROWS and ASM_ROWS.

Standard library only, except hbom (cyclonedx-python-lib, docs/bom-standard.md).
"""

import csv
import fnmatch
import glob
import itertools
import json
import os
import re
import shlex
import subprocess
import sys

# Project text variables for fabrication facts KiCad has no setting for.
# Variable -> README row in the "Board" table. Missing variables are skipped.
FAB_ROWS = {
    "FAB_MATERIAL": "Material",
    "FAB_PANEL": "Panel",
    "FAB_VIAS": "Via note",
    "FAB_ETEST": "Electrical test",
    "FAB_QUALITY": "Quality",
}
# Project text variables for assembly facts KiCad has no setting for.
ASM_ROWS = {
    "ASM_QUALITY": "Quality",
    "ASM_INSPECTION": "Inspection",
    "ASM_NOTES": "Notes",
}
# Other FAB_* variables used elsewhere in the README.
FAB_STACKUP = "FAB_STACKUP"  # stackup name, e.g. "JLCPCB JLC04161H-7628 or equivalent"
FAB_IMPEDANCE_TOLERANCE = "FAB_IMPEDANCE_TOLERANCE"  # e.g. "±10 %"


class Error(Exception):
    pass


# S-expression parsing

TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def parse_sexpr(text):
    stack = [[]]
    for m in TOKEN.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append([])
        elif t == ")":
            node = stack.pop()
            stack[-1].append(node)
        else:
            stack[-1].append(t[1:-1].replace('\\"', '"') if t[0] == '"' else t)
    return stack[0][0]


def children(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def child(node, key):
    found = children(node, key)
    return found[0] if found else None


def value(node, key, default=None):
    c = child(node, key) if node else None
    return c[1] if c and len(c) > 1 else default


# Project


def project_files(project_dir):
    pros = glob.glob(os.path.join(project_dir, "*.kicad_pro"))
    if len(pros) != 1:
        raise Error(f"expected exactly one .kicad_pro in {project_dir}, found {len(pros)}")
    name = os.path.splitext(os.path.basename(pros[0]))[0]
    files = {
        "name": name,
        "pro": pros[0],
        "sch": os.path.join(project_dir, name + ".kicad_sch"),
        "pcb": os.path.join(project_dir, name + ".kicad_pcb"),
    }
    for k in ("sch", "pcb"):
        if not os.path.exists(files[k]):
            raise Error(f"missing {files[k]}")
    return files


def text_variables(pro):
    with open(pro, encoding="utf-8") as f:
        return json.load(f).get("text_variables") or {}


def load_board(pcb):
    with open(pcb, encoding="utf-8") as f:
        return parse_sexpr(f.read())


def title_block(board):
    tb = child(board, "title_block")
    return value(tb, "title", ""), value(tb, "rev", ""), value(tb, "company", "")


# info


def cmd_info(project_dir, variant):
    files = project_files(project_dir)
    tv = text_variables(files["pro"])
    title, rev, _ = title_block(load_board(files["pcb"]))
    missing = [k for k in ("PCB_PN", f"ESP_PN_{variant}") if not tv.get(k)]
    if missing:
        raise Error(f"project text variables not set: {', '.join(missing)} (File > Project Setup > Text Variables)")
    if not rev:
        raise Error("the board title block has no revision")
    out = {
        "NAME": files["name"],
        "SCH": files["sch"],
        "PCB": files["pcb"],
        "PCB_PN": tv["PCB_PN"],
        "ESP_PN": tv[f"ESP_PN_{variant}"],
        "REV": rev,
        "TITLE": title,
    }
    for k, v in out.items():
        print(f"{k}={shlex.quote(v)}")


# readme


def fmt_mm(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s


def copper_weight(mm):
    oz = round(mm / 0.035 * 2) / 2
    return f"{oz:g} oz ({round(mm * 1000):g} µm)"


def board_outline_size(board):
    xs, ys = [], []
    for n in board:
        if isinstance(n, list) and n and n[0].startswith("gr_") and value(n, "layer") == "Edge.Cuts":
            for key in ("start", "end", "mid", "center"):
                c = child(n, key)
                if c:
                    xs.append(float(c[1]))
                    ys.append(float(c[2]))
            pts = child(n, "pts")
            if pts:
                for p in children(pts, "xy"):
                    xs.append(float(p[1]))
                    ys.append(float(p[2]))
    if not xs:
        raise Error("no board outline on Edge.Cuts")
    return max(xs) - min(xs), max(ys) - min(ys)


def stackup(board):
    setup = child(board, "setup")
    st = child(setup, "stackup")
    layers = []
    for layer in children(st, "layer"):
        layers.append(
            {
                "name": layer[1],
                "type": value(layer, "type", ""),
                "thickness": float(value(layer, "thickness", 0) or 0),
                "material": value(layer, "material", ""),
                "er": value(layer, "epsilon_r", ""),
                "color": value(layer, "color", ""),
            }
        )
    return st, layers


def layer_usage(board):
    """For each copper layer: nets with tracks, and nets with zone fills."""
    tracks, zones = {}, {}
    for n in board:
        if not isinstance(n, list) or not n:
            continue
        if n[0] in ("segment", "arc"):
            tracks.setdefault(value(n, "layer"), set()).add(value(n, "net", ""))
        elif n[0] == "zone" and not child(n, "keepout"):
            net = value(n, "net", "")
            lay = child(n, "layers") or child(n, "layer")
            for layer in lay[1:]:
                zones.setdefault(layer, set()).add(net)
    return tracks, zones


def inner_layer_description(layer, tracks, zones):
    signal = {n for n in tracks.get(layer, set()) if n and n != "GND"}
    gnd = "GND" in zones.get(layer, set()) or "GND" in tracks.get(layer, set())
    if not signal and gnd:
        return "GND plane"
    if signal and gnd:
        return "signals and GND"
    return "signals"


def gerber_function(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in itertools.islice(f, 40):
            m = re.search(r"TF\.FileFunction,([^*]*)\*", line)
            if m:
                return m.group(1).split(",")
    return []


def drill_info(path):
    """Tool diameters, hole count and plated slot widths of an Excellon file."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    tools = {m.group(1): float(m.group(2)) for m in re.finditer(r"^(T\d+)C([\d.]+)", text, re.M)}
    holes, slots, cur, in_body = 0, {}, None, False
    for line in text.splitlines():
        if line.strip() == "%":
            in_body = True
            continue
        if not in_body:
            continue
        if re.fullmatch(r"T\d+", line):
            cur = line
        elif line.startswith("G00"):
            slots[tools[cur]] = slots.get(tools[cur], 0) + 1
        elif re.match(r"[XY]", line):
            holes += 1
    return tools, holes, slots


def netclass_of(net, patterns, assignments):
    if net in assignments:
        return assignments[net]
    for p in patterns:
        if fnmatch.fnmatchcase(net, p["pattern"]):
            return p["netclass"]
    return "Default"


def interface_name(pattern):
    name = pattern.lstrip("*").split(".")[0]
    return re.sub(r"[_?*]+$", "", name).rstrip("_?") or pattern


def repo_url(project_dir):
    try:
        url = subprocess.run(
            ["git", "-C", project_dir, "remote", "get-url", "origin"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""
    m = re.match(r"(?:https?://|git@)([^/:]+)[/:](.+?)(?:\.git)?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else url


def cmd_readme(project_dir, out_dir):
    files = project_files(project_dir)
    tv = text_variables(files["pro"])
    with open(files["pro"], encoding="utf-8") as f:
        pro = json.load(f)
    board = load_board(files["pcb"])
    title, rev, _ = title_block(board)
    st, stack = stackup(board)
    copper = [layer["name"] for layer in stack if layer["type"] == "copper"]
    lnum = {name: f"L{i + 1}" for i, name in enumerate(copper)}
    tracks, zones = layer_usage(board)

    job = {}
    jobs = glob.glob(os.path.join(out_dir, "*.gbrjob"))
    if jobs:
        with open(jobs[0], encoding="utf-8") as f:
            job = json.load(f)
    version = job.get("Header", {}).get("GenerationSoftware", {}).get("Version", "")

    out = []
    w = out.append
    w(f"# {title}: PCB Fabrication Notes\n")
    w("| Item | Value |\n| ---- | ----- |")
    w(f"| Part number | {tv.get('PCB_PN', '')} |")
    w(f"| Design / revision | {title} {rev} |")
    url = repo_url(project_dir)
    w(f"| Source | KiCad {version}" + (f", [{url}](https://{url})" if url else "") + " |\n")

    # Files
    w("## Files\n")
    w("Gerber X2 (RS-274X with attributes), metric, absolute coordinates.\n")
    w("| File | Content |\n| ---- | ------- |")
    side = {"Top": "top", "Bot": "bottom"}
    for path in sorted(glob.glob(os.path.join(out_dir, "*"))):
        fn = os.path.basename(path)
        if fn == "README.md":
            continue
        desc = ""
        if fn.endswith(".gbr"):
            ff = gerber_function(path)
            kind = ff[0] if ff else ""
            if kind == "Copper":
                pos = ff[2] if len(ff) > 2 else ""
                lname = ff[1]
                if pos == "Top":
                    desc = f"{lname}, top copper"
                elif pos == "Bot":
                    desc = f"{lname}, bottom copper"
                else:
                    cu = copper[int(lname[1:]) - 1]
                    desc = f"{lname}, inner copper ({inner_layer_description(cu, tracks, zones)})"
            elif kind == "Soldermask":
                desc = f"Solder mask, {side.get(ff[1], ff[1])}"
            elif kind == "Legend":
                desc = f"Silkscreen, {side.get(ff[1], ff[1])}"
            elif kind == "Paste":
                desc = f"Solder paste (stencil), {side.get(ff[1], ff[1])}"
            elif kind == "Profile":
                desc = "Board outline"
            elif kind in ("AssemblyDrawing", "Other") or "Fab" in fn:
                desc = "Assembly drawing, for reference only. Do not fabricate."
            else:
                desc = ",".join(ff)
        elif fn.endswith(".drl"):
            desc = "Non-plated holes (Excellon)" if "NPTH" in fn else "Plated holes and plated slots (Excellon)"
        elif fn.endswith(".gbrjob"):
            desc = "Gerber job file: layer order, stackup, finish, size"
        else:
            continue
        w(f"| `{fn}` | {desc} |")
    w("")

    # Board
    sx, sy = board_outline_size(board)
    thickness = float(value(child(board, "general"), "thickness", 0))
    outer = [layer for layer in stack if layer["type"] == "copper"]
    mask = [layer for layer in stack if "Solder Mask" in layer["type"]]
    silk = [layer for layer in stack if "Silk Screen" in layer["type"]]
    setup = child(board, "setup")
    tent = child(setup, "tenting")
    tented = tent and all(value(tent, s) == "yes" for s in ("front", "back"))
    plugged = any(
        value(child(setup, k), s) == "yes"
        for k in ("plugging", "covering")
        for s in ("front", "back")
        if child(setup, k)
    )
    filled = value(setup, "filling") == "yes" or value(setup, "capping") == "yes"
    pth = [p for p in glob.glob(os.path.join(out_dir, "*.drl")) if "NPTH" not in p]
    slots = drill_info(pth[0])[2] if pth else {}
    castellated = value(st, "castellated_pads") == "yes" or any(
        "pad_prop_castellated" in str(p) for fp in children(board, "footprint") for p in children(fp, "pad")
    )
    edge_plating = value(st, "edge_plating") == "yes"
    edge_conn = value(st, "edge_connector")

    w("## Board\n")
    w("| Item | Value |\n| ---- | ----- |")
    w(f"| Layers | {len(copper)} |")
    w(f"| Size | {sx:.1f} × {sy:.1f} mm |".replace(".0 ×", " ×").replace(".0 mm", " mm"))
    if tv.get("FAB_PANEL"):
        w(f"| Panel | {tv['FAB_PANEL']} |")
    w(f"| Thickness | {thickness:.1f} mm |")
    if tv.get("FAB_MATERIAL"):
        w(f"| Material | {tv['FAB_MATERIAL']} |")
    if outer:
        o = copper_weight(outer[0]["thickness"])
        inner = outer[1:-1]
        w(
            f"| Outer / inner copper | {o} / {copper_weight(inner[0]['thickness'])} finished |"
            if inner
            else f"| Copper | {o} finished |"
        )
    w(f"| Surface finish | {value(st, 'copper_finish', 'not set')} |")
    if mask:
        w(f"| Solder mask | {mask[0]['color'] or 'not set'}, {'both sides' if len(mask) == 2 else 'one side'} |")
    if silk:
        w(f"| Silkscreen | {silk[0]['color'] or 'not set'}, {'both sides' if len(silk) == 2 else 'one side'} |")
    vias = (
        ("Tented" if tented else "Not tented")
        + (", plugged" if plugged else "")
        + (", filled" if filled else ", not filled")
        + (" or plugged" if not plugged and not filled else "")
    )
    note = f" {tv['FAB_VIAS']}" if tv.get("FAB_VIAS") else ""
    w(f"| Vias | {vias}.{note} |")
    w(
        "| Plated slots | "
        + ("Yes: " + ", ".join(f"{fmt_mm(s)}" for s in sorted(slots)) + " mm wide" if slots else "None")
        + " |"
    )
    extras = [
        n
        for n, on in (
            ("castellated holes", castellated),
            ("edge plating", edge_plating),
            ("edge connector (gold fingers)", edge_conn not in (None, "no")),
        )
        if on
    ]
    w(f"| Castellated holes / edge plating / gold fingers | {', '.join(extras).capitalize() if extras else 'None'} |")
    for var, label in FAB_ROWS.items():
        if var in ("FAB_PANEL", "FAB_MATERIAL", "FAB_VIAS"):
            continue
        if tv.get(var):
            w(f"| {label} | {tv[var]} |")
    w("")

    # Stackup
    name = tv.get(FAB_STACKUP, "")
    w(f"## Stackup{f' ({name})' if name else ''}\n")
    w("| Layer | Material | Thickness |\n| ----- | -------- | --------- |")
    for layer in stack:
        if layer["type"] == "copper":
            pos = "top" if layer["name"] == copper[0] else "bottom" if layer["name"] == copper[-1] else "inner"
            w(f"| {lnum[layer['name']]} {pos} copper | Copper | {round(layer['thickness'] * 1000, 1):g} µm |")
        elif layer["type"] in ("prepreg", "core"):
            mat = layer["material"] + (f", Er {layer['er']}" if layer["er"] else "")
            w(f"| {layer['type'].capitalize()} | {mat} | {fmt_mm(layer['thickness'])} mm |")
    w("")

    # Impedance control
    ns = pro.get("net_settings", {})
    patterns = ns.get("netclass_patterns") or []
    assignments = ns.get("netclass_assignments") or {}
    classes = {c["name"]: c for c in ns.get("classes", [])}
    net_layers = {}
    for layer, nets in tracks.items():
        for net in nets:
            net_layers.setdefault(net, set()).add(layer)
    rows = []
    for cname, c in classes.items():
        m = re.search(r"(\d+)\s*Ohm", cname, re.I)
        if not m:
            continue
        layers = set()
        for net, ls in net_layers.items():
            if netclass_of(net, patterns, assignments) == cname:
                layers |= ls
        ifaces = []
        for p in patterns:
            if p["netclass"] == cname:
                i = interface_name(p["pattern"])
                if i not in ifaces:
                    ifaces.append(i)
        lay = ", ".join(lnum[layer] for layer in copper if layer in layers)
        rows.append((int(m.group(1)), c.get("diff_pair_width"), c.get("diff_pair_gap"), lay, ", ".join(ifaces)))
    if rows:
        tol = tv.get(FAB_IMPEDANCE_TOLERANCE, "")
        w(f"## Impedance Control{f' ({tol})' if tol else ''}\n")
        used = sorted({layer for r in rows for layer in r[3].split(", ") if layer})
        outer_used = [layer for layer in used if layer in (lnum[copper[0]], lnum[copper[-1]])]
        refs = [lnum[copper[1]] if layer == lnum[copper[0]] else lnum[copper[-2]] for layer in outer_used]
        gnd_clear = []
        for z in children(board, "zone"):
            if value(z, "net_name", value(z, "net")) == "GND":
                cp = child(z, "connect_pads")
                if cp and child(cp, "clearance"):
                    gnd_clear.append(float(child(cp, "clearance")[1]))
        spacing = f", with {fmt_mm(max(gnd_clear))} mm spacing to the same-layer GND pour" if gnd_clear else ""
        if outer_used:
            w(
                f"All controlled lines are differential pairs on {' or '.join(outer_used)}, referenced to the adjacent "
                f"GND plane ({' or '.join(refs)}){spacing}.\n"
            )
        else:
            w(f"All controlled lines are differential pairs, on the layers listed below{spacing}.\n")
        w("| Target | Trace width | Pair gap | Layers | Interfaces |")
        w("| ------ | ----------- | -------- | ------ | ---------- |")
        for ohm, width, gap, lay, ifaces in sorted(rows):
            w(f"| {ohm} Ω differential | {fmt_mm(width)} mm | {fmt_mm(gap)} mm | {lay} | {ifaces} |")
        w("")

    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out).rstrip() + "\n")
    missing = [v for v in [*FAB_ROWS, FAB_STACKUP, FAB_IMPEDANCE_TOLERANCE] if not tv.get(v)]
    if missing:
        print(f"note: README rows skipped, project text variables not set: {', '.join(missing)}", file=sys.stderr)


# check-pos


def refsort(refs):
    """Reference designators in natural order: C2 before C10."""
    return sorted(refs, key=lambda r: (re.sub(r"\d+", "", r), int(re.sub(r"\D", "", r) or 0)))


def footprint_attrs(board):
    attrs = {}
    for fp in children(board, "footprint"):
        ref = next((p[2] for p in children(fp, "property") if p[1] == "Reference"), None)
        a = child(fp, "attr")
        attrs[ref] = set(a[1:]) if a else set()
    return attrs


def cmd_check_pos(project_dir, pos, bom):
    files = project_files(project_dir)
    attrs = footprint_attrs(load_board(files["pcb"]))
    with open(pos, encoding="utf-8") as f:
        pos_refs = {line.split()[0] for line in f if line.strip() and not line.startswith("#")}
    with open(bom, encoding="utf-8", newline="") as f:
        bom_refs = {r.strip() for row in csv.DictReader(f) for r in row["Reference"].split(",") if r.strip()}
    errors = []
    for ref in sorted(pos_refs - bom_refs):
        if "exclude_from_bom" not in attrs.get(ref, set()):
            errors.append(f"{ref} is in the position file but not in the BOM (DNP in this variant?)")
    for ref in sorted(bom_refs - pos_refs):
        # The position file lists SMD footprints only. Through-hole parts are placed by hand, and
        # off-board items (no footprint) are not placed at all.
        a = attrs.get(ref)
        if a is None or a & {"exclude_from_pos_files", "through_hole"}:
            continue
        if "smd" in a:
            errors.append(f"{ref} is in the BOM but not in the position file")
        else:
            errors.append(f"{ref}: footprint type is unspecified, set it to SMD or through-hole")
    if errors:
        raise Error("position file and BOM disagree:\n  " + "\n  ".join(errors))
    print(f"position file and BOM agree: {len(pos_refs)} placements, {len(bom_refs)} BOM references")


# cpl, sides

CPL_COLUMNS = {
    "Ref": "Designator",
    "Val": "Value",
    "Package": "Package",
    "PosX": "Mid X",
    "PosY": "Mid Y",
    "Rot": "Rotation",
    "Side": "Layer",
}


def cmd_cpl(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise Error(f"{path} is empty")
    rows[0] = [CPL_COLUMNS.get(h, h) for h in rows[0]]
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)


def pos_rows(pos):
    with open(pos, encoding="utf-8") as f:
        return [line.split() for line in f if line.strip() and not line.startswith("#")]


def cmd_sides(pos):
    print(" ".join(sorted({r[-1] for r in pos_rows(pos)}, key=["top", "bottom"].index)))


# asm-readme


def cmd_asm_readme(project_dir, variant, bom, pos, out_dir):
    files = project_files(project_dir)
    tv = text_variables(files["pro"])
    board = load_board(files["pcb"])
    title, rev, _ = title_block(board)
    attrs = footprint_attrs(board)
    with open(bom, encoding="utf-8", newline="") as f:
        bom_rows = list(csv.DictReader(f))
    bom_refs = {r.strip() for row in bom_rows for r in row["Reference"].split(",") if r.strip()}
    placements = pos_rows(pos)
    sides = sorted({r[-1] for r in placements}, key=["top", "bottom"].index)

    tht = refsort(r for r in bom_refs if "through_hole" in attrs.get(r, set()))
    dnp = refsort(r for r, a in attrs.items() if r and r not in bom_refs and "exclude_from_bom" not in a)
    esp = tv.get(f"ESP_PN_{variant}", "")

    out = []
    w = out.append
    w(f"# {title}: Assembly Notes\n")
    w("| Item | Value |\n| ---- | ----- |")
    w(f"| Part number | {esp} |")
    w(f"| Variant | {variant} |")
    w(f"| Bare PCB | {tv.get('PCB_PN', '')} ({title} {rev}) |")
    if esp.startswith("SRLY-ESP-"):
        w("| Programming | None: the assembly is delivered without firmware |")
    w("")

    w("## Files\n")
    w("| File | Content |\n| ---- | ------- |")
    for path in sorted(glob.glob(os.path.join(out_dir, "*"))):
        fn = os.path.basename(path)
        bom_name = re.search(r"-bom((?:-[a-z0-9]+)*)\.csv$", fn)
        if bom_name:
            # The distributor list as written in the file name (lowercase, see create-manufacturing-files.sh).
            names = [n for n in bom_name.group(1).split("-") if n]
            w(
                f"| `{fn}` | Bill of materials, one line per part number, with the distributor and its part number"
                + (f"; parts picked for the distributor preference {', '.join(names)}" if names else "")
                + " |"
            )
            continue
        desc = {
            "-hbom.cdx.json": "Hardware bill of materials (HBOM), CycloneDX 1.6 JSON",
            "-cpl.csv": "Pick-and-place file, CSV (Designator, Mid X, Mid Y, Rotation, Layer), SMD parts only",
            ".pos": "Pick-and-place file, KiCad text format, SMD parts only",
            "-assembly-top.pdf": "Assembly drawing, top side: fabrication and silkscreen layers; "
            "do-not-fit parts are crossed out",
            "-assembly-bottom.pdf": "Assembly drawing, bottom side: fabrication and silkscreen layers; "
            "do-not-fit parts are crossed out",
        }
        d = next((v for k, v in desc.items() if fn.endswith(k)), None)
        if d:
            w(f"| `{fn}` | {d} |")
    w("")
    w(
        "Coordinates are in mm and match the Gerber files of the bare PCB. "
        "The solder paste (stencil) layers are in the bare PCB package.\n"
    )

    w("## Assembly\n")
    w("| Item | Value |\n| ---- | ----- |")
    w(f"| Sides | {' and '.join(sides) if sides else 'none'} |")
    w(f"| SMD placements | {len(placements)} |")
    w(f"| Through-hole parts | {len(tht)} |")
    w(f"| Part numbers (BOM lines) | {len(bom_rows)} |")
    for var, label in ASM_ROWS.items():
        if tv.get(var):
            w(f"| {label} | {tv[var]} |")
    w("")
    if tht:
        w("## Through-Hole Parts\n")
        w("Not in the pick-and-place files; solder by hand, selective or wave soldering:\n")
        w(", ".join(tht) + "\n")
    if dnp:
        w("## Do Not Fit\n")
        w(f"Footprints on the board that stay empty in the {variant} variant:\n")
        w(", ".join(dnp) + "\n")

    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out).rstrip() + "\n")
    missing = [v for v in ASM_ROWS if not tv.get(v)]
    if missing:
        print(
            f"note: assembly README rows skipped, project text variables not set: {', '.join(missing)}", file=sys.stderr
        )


# hbom


def git_commit(project_dir):
    try:
        out = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", project_dir, "status", "--porcelain", "--", "."], capture_output=True, text=True, check=True
        ).stdout.strip()
        return out + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return ""


PARTSDB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "partsdb.py")


def partsdb(*args):
    """JSON output of a tools/partsdb.py command. The tool finds the database itself (PARTSDB_DIR or
    its own configuration), so this works unchanged when the database becomes a web service."""
    r = subprocess.run([sys.executable, PARTSDB, *args], capture_output=True, text=True)
    if r.returncode:
        raise Error(f"part database: {r.stderr.strip() or r.stdout.strip()}")
    return json.loads(r.stdout)


def distributor_names():
    """Names in the distributor table of the part database."""
    return list(partsdb("distributors", "list", "--json"))


def part_records(pns):
    """Registry entries of the given part numbers, in one call. Part numbers that are not in the
    registry are left out; the caller reports them."""
    pns = list(dict.fromkeys(pns))
    return {p["part"]: p for p in partsdb("show", "--skip-missing", *pns)} if pns else {}


# resolve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_STANDARD = os.path.join(ROOT, "docs", "part-library-standard.md")
LIBRARY = os.path.join(ROOT, "library", "Screenly.kicad_sym")
# The class keys the resolver checks: {class: {key: {"required", "comparison"}}}. The key tables of
# LIBRARY_STANDARD are the human-readable copy; check-class-keys keeps the two in step.
CLASS_KEYS = os.path.join(ROOT, "library", "class-keys.json")
PART_NUMBER = re.compile(r"^SRLY-([A-Z]{3})-[0-9]{6}$")
COMPARISONS = ("exact", "max", "min", "set", "pattern", "range", "all")
# Columns of the per-instance export besides the class keys. The `value` key is KiCad's Value field.
INSTANCE_FIELDS = ["Reference", "PartNumber", "Value", "Footprint", "Manufacturer", "MfrPartNum"]
BOM_COLUMNS = [
    "PartNumber",
    "Reference",
    "Value",
    "Manufacturer",
    "MfrPartNum",
    "QUANTITY",
    "Distributor",
    "Distributor part number",
    "Link",
]
HBOM_SOURCE_COLUMNS = [
    "PartNumber",
    "Reference",
    "Value",
    "Manufacturer",
    "MfrPartNum",
    "Description",
    "Datasheet",
    "QUANTITY",
]


def class_keys():
    """{class code: {key: (required, comparison)}} from CLASS_KEYS."""
    with open(CLASS_KEYS, encoding="utf-8") as f:
        data = json.load(f)
    classes = {}
    for cls, keys in data.items():
        for key, k in keys.items():
            if set(k) != {"required", "comparison"} or k["comparison"] not in COMPARISONS:
                raise Error(f"{CLASS_KEYS}: {cls}.{key}: needs required and a comparison of {', '.join(COMPARISONS)}")
        classes[cls] = {key: (k["required"] is True, k["comparison"]) for key, k in keys.items()}
    return classes


def doc_class_keys():
    """{class code: {key: (required, comparison)}} from the key tables of the library standard."""
    with open(LIBRARY_STANDARD, encoding="utf-8") as f:
        doc = f.read()
    classes = {}
    for m in re.finditer(r"^### `([A-Z]{3})`: .*?$(.*?)(?=^##)", doc + "\n##", re.M | re.S):
        table = re.search(r"^\| Key .*\n\|[-| ]+\n((?:\|.*\n)+)", m.group(2), re.M)
        if not table:
            raise Error(f"{LIBRARY_STANDARD}: class {m.group(1)} has no key table")
        keys = {}
        for row in table.group(1).splitlines():
            cells = [c.strip().strip("`") for c in row.strip("|").split("|")]
            if len(cells) != 4 or cells[3] not in COMPARISONS:
                raise Error(f"{LIBRARY_STANDARD}: class {m.group(1)}: bad key row: {row}")
            keys[cells[0]] = (cells[2] == "Yes", cells[3])
        classes[m.group(1)] = keys
    return classes


def cmd_check_class_keys():
    """Check that the key tables of the library standard and CLASS_KEYS agree."""
    doc, data = doc_class_keys(), class_keys()
    errors = [
        f"class {c}: only in {os.path.basename(p)}"
        for c, p in [(c, LIBRARY_STANDARD) for c in doc.keys() - data.keys()]
        + [(c, CLASS_KEYS) for c in data.keys() - doc.keys()]
    ]
    for c in sorted(doc.keys() & data.keys()):
        if doc[c] != data[c]:
            diff = sorted(k for k in doc[c].keys() | data[c].keys() if doc[c].get(k) != data[c].get(k))
            errors.append(f"class {c}: keys differ: {', '.join(diff)}")
    if errors:
        raise Error("the library standard and class-keys.json disagree:\n  " + "\n  ".join(sorted(errors)))
    print(f"class keys agree: {len(data)} classes")


def cmd_key_fields():
    """Print the fields of the per-instance BOM export, for kicad-cli --fields."""
    keys = {k for c in class_keys().values() for k in c if k != "value"}
    print(",".join(INSTANCE_FIELDS + sorted(keys)))


def library_parts():
    """{PartNumber: symbol fields} of the library symbols that carry a part number."""
    with open(LIBRARY, encoding="utf-8") as f:
        lib = parse_sexpr(f.read())
    symbols = {s[1]: s for s in children(lib, "symbol")}

    def fields(sym):
        parent = value(sym, "extends")
        props = fields(symbols[parent]) if parent in symbols else {}
        props.update({p[1]: p[2] for p in children(sym, "property")})
        return props

    parts = {}
    for sym in symbols.values():
        props = fields(sym)
        pn = props.get("PartNumber", "").strip()
        if pn:
            if pn in parts:
                raise Error(f"library: {pn} is on two symbols")
            parts[pn] = props
    return parts


SI = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}
UNITS = {
    "",
    "F",
    "H",
    "V",
    "A",
    "W",
    "Hz",
    "B",
    "C",
    "%",
    "ppm",
    "dB",
    "dBi",
    "dBm",
    "Ah",
    "s",
    "g",
    "N",
    "cd",
    "lm",
    "nit",
    "R",
    "Ω",
    "ohm",
    "mm",
    "m",
    "in",
    "deg",
    "°",
}


def quantity(text):
    """(number, unit) of a field value such as 10uF, 4.7K, 4R7, 4n7, -40C, 62.5mW; None if not numeric.
    RKM notation has no unit, given as None, which matches any unit."""
    t = text.strip().replace(" ", "")
    m = re.fullmatch(r"(\d+)([pnuµmRrKkMG])(\d+)", t)  # RKM notation: 4R7, 4K7, 4n7, 2u2; no unit
    if m:
        return float(f"{m[1]}.{m[3]}") * SI.get(m[2], 1), None
    m = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)(.*)", t)
    if not m:
        return None
    num, rest = float(m[1]), m[2]
    if rest and rest[0] in SI and rest[1:] in UNITS:
        num, rest = num * SI[rest[0]], rest[1:]
    elif rest not in UNITS:
        return None
    return num, "" if rest in ("R", "Ω", "ohm") else rest


def same_unit(a, b):
    return a is None or b is None or a == b


def compare(kind, required, offered, mpn):
    """Whether a part with field value `offered` (and manufacturer part number `mpn`) meets the
    instance field value `required` under comparison `kind` (docs/part-library-standard.md)."""
    if kind == "pattern":
        return fnmatch.fnmatchcase(mpn.upper(), required.upper())
    if not offered.strip():
        return False
    if kind in ("set", "all"):
        want = {v.strip().lower() for v in re.split(r"[|,]", required) if v.strip()}
        have = {v.strip().lower() for v in re.split(r"[|,]", offered) if v.strip()}
        return have <= want if kind == "set" else want <= have
    if kind == "range":

        def within(rail, item):
            lo, _, hi = item.partition("..")
            r, a, b = quantity(rail), quantity(lo), quantity(hi or lo)
            return (
                None not in (r, a, b)
                and same_unit(r[1], a[1])
                and same_unit(r[1], b[1])
                and a[0] - 1e-9 <= r[0] <= b[0] + 1e-9
            )

        return all(
            any(within(rail, item) for item in offered.split(",")) for rail in required.split(",") if rail.strip()
        )
    want, have = quantity(required), quantity(offered)
    if want is None or have is None or not same_unit(want[1], have[1]):
        # Words such as `adj` or `yes`, or values in different units: only an equal value matches.
        return required.strip().lower() == offered.strip().lower()
    tol = 1e-9 * max(abs(want[0]), abs(have[0]), 1e-30)
    if kind == "exact":
        return abs(have[0] - want[0]) <= tol
    return have[0] <= want[0] + tol if kind == "max" else have[0] >= want[0] - tol


def key_value(fields, key):
    """Value of a class key in a symbol's fields; the `value` key is KiCad's Value field."""
    return fields.get("Value" if key == "value" else key, "").strip()


def pick_distributor(entry, pref):
    """(rank, distributor entry) of a part for the preference list: the index of the first listed
    distributor the part has; len(pref) for the part's own preferred one (a fallback when pref is
    given); len(pref) + 1 when it has none."""
    info = entry.get("distributor_info", [])
    for i, name in enumerate(pref):
        for d in info:
            if d["distributor"] == name:
                return i, d
    return (len(pref), info[0]) if info else (len(pref) + 1, None)


def cmd_resolve(instances, preference, strict, bom_out, hbom_source_out):
    """Pick a part for each assembled instance and write the BOM and the HBOM source.

    Candidates are approved parts (library symbols whose part number is in the part database) of
    the instance's class that fit its footprint and meet every class key field of the instance.
    Selection: the earliest distributor in the preference list, then the design's own part, then
    the part that fits the most instances (fewer unique parts), then the lowest part number."""
    table = distributor_names()
    known = {d.lower(): d for d in table}
    names = [p.strip() for p in preference.split(",") if p.strip()]
    unknown = [n for n in names if n.lower() not in known]
    if unknown:
        raise Error(f"unknown distributor: {', '.join(unknown)} (in the part database: {', '.join(table)})")
    pref = [known[n.lower()] for n in names]
    strict = strict == "1"

    classes = class_keys()
    library = library_parts()
    registry = part_records(sorted(library))  # library symbols not in the database are not approved
    with open(instances, encoding="utf-8", newline="") as f:
        rows = []
        for row in csv.DictReader(f):  # one row per symbol; split any grouped references
            rows += [{**row, "Reference": r} for r in row["Reference"].replace(" ", ",").split(",") if r]
    rows = list({r["Reference"]: r for r in reversed(rows)}.values())[::-1]  # units of one symbol

    errors, choices = [], {}
    for row in rows:
        ref, design = row["Reference"].strip(), row["PartNumber"].strip()
        if not design:
            errors.append(f"{ref}: no PartNumber")
            continue
        if not PART_NUMBER.match(design):
            errors.append(f"{ref}: PartNumber {design!r} is not a Screenly part number (SRLY-XXX-000000)")
            continue
        if design not in library:
            errors.append(f"{ref}: {design} is not in the library")
            continue
        if design not in registry:
            errors.append(f"{ref}: {design} is not in the part database")
            continue
        cls = PART_NUMBER.match(design)[1]
        keys = classes.get(cls)
        if keys is None:  # class not defined yet: only the design part
            choices[ref] = (row, design, [design])
            continue

        def field(k, row=row):
            return key_value(row, k)

        missing = [k for k, (req, _) in keys.items() if req and not field(k)]
        if missing:
            errors.append(f"{ref} ({design}): required key fields empty: {', '.join(missing)}")
            continue
        fp = row.get("Footprint", "").strip()
        cands = []
        for pn, props in library.items():
            if (
                pn not in registry
                or not pn.startswith(f"SRLY-{cls}-")
                or (fp and props.get("Footprint", "").strip() != fp)
            ):
                continue
            mpn = registry[pn]["mpn"]
            if all(compare(kind, field(k), key_value(props, k), mpn) for k, (_, kind) in keys.items() if field(k)):
                cands.append(pn)
        if design not in cands:
            props = library[design]
            failed = [
                k
                for k, (_, kind) in keys.items()
                if field(k) and not compare(kind, field(k), key_value(props, k), registry[design]["mpn"])
            ]
            why = f"key fields {', '.join(f'{k}={field(k)!r}' for k in failed)}" if failed else "footprint"
            errors.append(f"{ref}: its own part {design} doesn't meet the instance's {why}")
        if not cands:
            continue
        choices[ref] = (row, design, cands)
    if errors:
        raise Error("cannot resolve the BOM:\n  " + "\n  ".join(errors))

    fits = {}
    for _, _, cands in choices.values():
        for pn in cands:
            fits[pn] = fits.get(pn, 0) + 1
    picked = {}
    for ref, (_row, design, cands) in choices.items():
        # Without a preference list, distributors don't count: the design's own part is kept.
        picked[ref] = min(
            cands, key=lambda pn: (pick_distributor(registry[pn], pref)[0] if pref else 0, pn != design, -fits[pn], pn)
        )

    lines = {}
    for ref, pn in picked.items():
        lines.setdefault(pn, []).append(ref)
    counts, fallbacks, missing, unmatched, swaps = {}, [], [], [], []
    bom, hbom = [], []
    for pn in sorted(lines):
        refs, entry, props = refsort(lines[pn]), registry[pn], library[pn]
        rank, dist = pick_distributor(entry, pref)
        label = f"{pn} ({entry['mpn']})"
        if dist is None:
            missing.append(label)
        else:
            counts[dist["distributor"]] = counts.get(dist["distributor"], 0) + 1
            if pref and rank == len(pref):
                (unmatched if strict else fallbacks).append(f"{label} -> {dist['distributor']}")
        line = {
            "PartNumber": pn,
            "Reference": ",".join(refs),
            "Value": props.get("Value", ""),
            "Manufacturer": entry["manufacturer"],
            "MfrPartNum": entry["mpn"],
            "QUANTITY": str(len(refs)),
            "Description": props.get("Description", ""),
            "Datasheet": props.get("Datasheet", ""),
        }
        bom.append(
            {
                **line,
                "Distributor": dist["distributor"] if dist else "",
                "Distributor part number": dist["part_number"] if dist else "",
                "Link": dist.get("link", "") if dist else "",
            }
        )
        hbom.append(line)
        for design in sorted({choices[r][1] for r in refs} - {pn}):
            moved = refsort(r for r in refs if choices[r][1] == design)
            swaps.append(f"{','.join(moved)}: {design} ({registry[design]['mpn']}) -> {label}")
    if strict and (unmatched or missing):
        raise Error(
            "parts without a distributor from "
            + (", ".join(pref) or "the list")
            + ":\n  "
            + "\n  ".join(unmatched + [m + " -> none" for m in missing])
        )
    for path, columns, data in ((bom_out, BOM_COLUMNS, bom), (hbom_source_out, HBOM_SOURCE_COLUMNS, hbom)):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_ALL, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)
    summary = ", ".join(f"{n} {d}" for d, n in sorted(counts.items(), key=lambda x: -x[1]))
    print(
        f"BOM: {len(bom)} lines, {len(picked)} parts; {len(swaps)} substitution{'s' * (len(swaps) != 1)}; "
        f"distributors: {summary or 'none'}"
        + (f"; {len(fallbacks)} fallback" if fallbacks else "")
        + (f"; {len(missing)} without a distributor" if missing else "")
    )
    for line in swaps:
        print(f"  substituted: {line}")
    for line in fallbacks:
        print(f"  fallback: {line}")
    for line in missing:
        print(f"  no distributor: {line}")


def cmd_hbom(project_dir, variant, bom, out_json):
    try:
        from cyclonedx.model import ExternalReference, ExternalReferenceType, Property, XsUri
        from cyclonedx.model.bom import Bom
        from cyclonedx.model.component import Component, ComponentType
        from cyclonedx.model.contact import OrganizationalEntity
        from cyclonedx.output.json import JsonV1Dot6
    except ImportError:
        raise Error("cyclonedx-python-lib is not installed (pip install cyclonedx-python-lib)") from None
    files = project_files(project_dir)
    tv = text_variables(files["pro"])
    title, rev, company = title_block(load_board(files["pcb"]))
    esp, pcb = tv[f"ESP_PN_{variant}"], tv["PCB_PN"]
    with open(bom, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    registry = part_records([esp, pcb] + [r["PartNumber"].strip() for r in rows if r["PartNumber"].strip()])

    def cpe(pn):
        return registry.get(pn, {}).get("cpe") or None

    def attrs(pn):
        e = registry.get(pn, {})
        props = [
            ("screenly:hbom:countryOfOrigin", e.get("country_of_origin", "Unknown")),
            ("screenly:hbom:lifeCycle", e.get("lifecycle", "Unknown")),
            ("screenly:hbom:containsFirmware", e.get("contains_firmware", "Unknown")),
        ]
        if e.get("ltb_date"):
            props.append(("screenly:hbom:ltbDate", e["ltb_date"]))
        if e.get("firmware_cpe"):
            props.append(("screenly:hbom:firmwareCpe", e["firmware_cpe"]))
        return props

    def component(pn, name, version, manufacturer, description, datasheet, refdes, qty):
        props = ([("screenly:hbom:refdes", refdes)] if refdes else []) + [("screenly:hbom:quantity", str(qty))]
        refs = []
        if datasheet.startswith(("http://", "https://")):
            refs.append(ExternalReference(type=ExternalReferenceType.DOCUMENTATION, url=XsUri(datasheet)))
        return Component(
            type=ComponentType.DEVICE,
            bom_ref=pn,
            name=name or pn,
            version=version or None,
            cpe=cpe(pn),
            manufacturer=OrganizationalEntity(name=manufacturer) if manufacturer else None,
            description=description or None,
            external_references=refs,
            properties=[Property(name=k, value=v) for k, v in props + attrs(pn)],
        )

    errors = []
    components = []
    pcb_entry = registry.get(pcb)
    if not pcb_entry:
        errors.append(f"{pcb} (PCB_PN) is not in the part database")
    else:
        # The bare PCB's version is the design revision.
        components.append(
            component(pcb, pcb_entry["mpn"], rev, pcb_entry["manufacturer"], pcb_entry["description"], "", "", 1)
        )
    for row in rows:
        pn = row["PartNumber"].strip()
        if not pn:
            errors.append(f"BOM line {row['Reference']} has no PartNumber")
            continue
        if pn not in registry:
            errors.append(f"{pn} ({row['Reference']}) is not in the part database")
        refs = ",".join(r.strip() for r in row["Reference"].split(","))
        # A bought part has no version of its own: the version is its manufacturer part number.
        components.append(
            component(
                pn,
                row["MfrPartNum"],
                row["MfrPartNum"],
                row["Manufacturer"],
                row.get("Description", ""),
                row.get("Datasheet", ""),
                refs,
                row["QUANTITY"],
            )
        )
    if errors:
        raise Error("HBOM:\n  " + "\n  ".join(errors))

    esp_entry = registry.get(esp, {})
    top = Component(
        type=ComponentType.DEVICE,
        bom_ref=esp,
        name=esp_entry.get("mpn", esp),
        version=rev,
        cpe=cpe(esp),
        manufacturer=OrganizationalEntity(name=esp_entry.get("manufacturer", company or "Screenly")),
        description=esp_entry.get("description") or None,
        properties=[
            Property(name=k, value=v)
            for k, v in [
                ("screenly:hbom:variant", variant),
                ("screenly:hbom:pcb", pcb),
                ("screenly:hbom:designCommit", git_commit(project_dir) or "unknown"),
            ]
            + attrs(esp)
        ],
    )
    hbom = Bom()
    hbom.metadata.component = top
    for c in components:
        hbom.components.add(c)
        hbom.register_dependency(top, [c])
    with open(out_json, "w", encoding="utf-8") as f:
        f.write(JsonV1Dot6(hbom).output_as_string(indent=2) + "\n")
    try:
        from cyclonedx.schema import SchemaVersion
        from cyclonedx.validation.json import JsonStrictValidator

        with open(out_json, encoding="utf-8") as f:
            err = JsonStrictValidator(SchemaVersion.V1_6).validate_str(f.read())
        if err:
            raise Error(f"HBOM does not validate against CycloneDX 1.6: {err}")
    except ImportError:
        print("note: HBOM schema not validated (pip install 'cyclonedx-python-lib[json-validation]')", file=sys.stderr)
    unknown = sum(
        1
        for c in components
        for p in c.properties
        if p.name in ("screenly:hbom:lifeCycle", "screenly:hbom:containsFirmware") and p.value == "Unknown"
    )
    print(f"HBOM: {len(components)} components" + (f", {unknown} Unknown lifecycle/firmware values" if unknown else ""))


def main(argv):
    cmds = {
        "info": (cmd_info, 2),
        "readme": (cmd_readme, 2),
        "check-pos": (cmd_check_pos, 3),
        "cpl": (cmd_cpl, 1),
        "sides": (cmd_sides, 1),
        "asm-readme": (cmd_asm_readme, 5),
        "hbom": (cmd_hbom, 4),
        "key-fields": (cmd_key_fields, 0),
        "check-class-keys": (cmd_check_class_keys, 0),
        "resolve": (cmd_resolve, 5),
    }
    if len(argv) < 2 or argv[1] not in cmds or len(argv) - 2 != cmds[argv[1]][1]:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        cmds[argv[1]][0](*argv[2:])
    except Error as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
