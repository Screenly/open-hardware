#!/usr/bin/env python3
"""Screenly part database: assigned part numbers and stock.

The database is a directory, given by --db or the PARTSDB_DIR environment
variable, that holds these JSON files:

  registry.json  every part number in use, with the part attributes the
                 HBOM needs (country of origin, lifecycle, firmware, CPE)
  stock.json     quantity per part number and location
  retired.json   deleted part numbers

Part numbering is locked (EARLY_STAGE is False): part numbers can't be
deleted, and retired numbers are never reassigned. While EARLY_STAGE was True,
part numbers could be deleted, and a retired number was assigned again once no
file in the repository mentioned it.

Every change made by this tool is validated and written in a fixed format,
so changes give small, stable diffs. Tracking the history of the database,
for example with git, is up to the user.

Standard library only. See docs/part-numbering-standard.md.
"""

import argparse
import datetime
import fnmatch
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = REGISTRY = STOCK = RETIRED = ""
NUMBERING_DOC = os.path.join(ROOT, "docs", "part-numbering-standard.md")

# Early stage of the library: allow deleting part numbers and reusing retired ones.
# Locked on 2026-11-17: part numbers are never deleted or reused.
EARLY_STAGE = False

# Files scanned for mentions of a retired part number before it is reused.
SCAN_SUFFIXES = (".kicad_sch", ".kicad_pcb", ".kicad_sym", ".kicad_mod", ".md", ".json", ".csv", ".txt")
SCAN_SKIP_DIRS = {".git", "tmp", "3d-models", "node_modules"}

PART_NUMBER = re.compile(r"^SRLY-([A-Z]{3})-([0-9]{6})$")
LOCATION = re.compile(r"^[a-z0-9_]+$")
REGISTRY_FIELDS = {"manufacturer", "mpn", "description", "assigned"}
RETIRED_FIELDS = REGISTRY_FIELDS | {"deleted"}
# Part attributes for the HBOM (docs/bom-standard.md, Part attributes). Optional:
# a missing lifecycle or contains_firmware means Unknown.
ATTRIBUTE_FIELDS = {"country_of_origin", "lifecycle", "ltb_date", "contains_firmware", "cpe", "firmware_cpe",
                    "attributes_checked"}
CPE = re.compile(r"^cpe:2\.3:[aho](:[^:\s]+){10}$")
LIFECYCLES = ("Active", "NRND", "LTB", "Obsolete", "Preview", "Unknown")
FIRMWARE = ("None", "Fixed", "Updatable", "Unknown")


class Error(Exception):
    pass


# Files

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(data):
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(dump(data))
    os.replace(tmp, path)


def set_db(path):
    global DB, REGISTRY, STOCK, RETIRED
    DB = os.path.abspath(os.path.expanduser(path)) if path else ""
    REGISTRY = os.path.join(DB, "registry.json")
    STOCK = os.path.join(DB, "stock.json")
    RETIRED = os.path.join(DB, "retired.json")






# Validation

def class_codes():
    with open(NUMBERING_DOC, encoding="utf-8") as f:
        return set(re.findall(r"^\| `([A-Z]{3})` \|", f.read(), re.M))


def validate(registry, stock, retired):
    errors = []
    codes = class_codes()
    seen = {}
    for pn, entry in registry.items():
        m = PART_NUMBER.match(pn)
        if not m:
            errors.append(f"{pn}: not a valid part number")
            continue
        if m.group(1) not in codes:
            errors.append(f"{pn}: unknown class {m.group(1)}")
        if not REGISTRY_FIELDS <= set(entry) or set(entry) - REGISTRY_FIELDS - ATTRIBUTE_FIELDS:
            errors.append(f"{pn}: fields must be {sorted(REGISTRY_FIELDS)}, optionally {sorted(ATTRIBUTE_FIELDS)}")
            continue
        errors += [f"{pn}: {e}" for e in attribute_errors(entry)]
        if not entry["manufacturer"] or not entry["mpn"]:
            errors.append(f"{pn}: manufacturer and mpn are required")
        key = (entry["manufacturer"].lower(), entry["mpn"].lower())
        if key in seen:
            errors.append(f"{pn}: same part as {seen[key]}")
        seen[key] = pn
        try:
            datetime.date.fromisoformat(entry["assigned"])
        except ValueError:
            errors.append(f"{pn}: assigned must be an ISO 8601 date")
    for pn, locations in stock.items():
        if pn not in registry:
            errors.append(f"stock {pn}: not in registry")
        for location, qty in locations.items():
            if not LOCATION.match(location):
                errors.append(f"stock {pn}: invalid location {location!r}")
            if not isinstance(qty, int) or isinstance(qty, bool) or qty < 0:
                errors.append(f"stock {pn} {location}: quantity must be a non-negative integer")
    for pn, entry in retired.items():
        if not PART_NUMBER.match(pn):
            errors.append(f"retired {pn}: not a valid part number")
        if pn in registry:
            errors.append(f"retired {pn}: also in registry")
        if set(entry) != RETIRED_FIELDS:
            errors.append(f"retired {pn}: fields must be {sorted(RETIRED_FIELDS)}")
    return errors




def attribute_errors(entry):
    errors = []
    if entry.get("lifecycle", "Unknown") not in LIFECYCLES:
        errors.append(f"lifecycle must be one of {', '.join(LIFECYCLES)}")
    if entry.get("contains_firmware", "Unknown") not in FIRMWARE:
        errors.append(f"contains_firmware must be one of {', '.join(FIRMWARE)}")
    if "ltb_date" in entry and entry.get("lifecycle") != "LTB":
        errors.append("ltb_date is only allowed with lifecycle LTB")
    for key in ("ltb_date", "attributes_checked"):
        if key in entry:
            try:
                datetime.date.fromisoformat(entry[key])
            except ValueError:
                errors.append(f"{key} must be an ISO 8601 date")
    if "cpe" in entry and not (CPE.match(entry["cpe"]) and entry["cpe"].startswith("cpe:2.3:h:")):
        errors.append("cpe must be a CPE 2.3 name of a hardware part (cpe:2.3:h:...)")
    if "firmware_cpe" in entry and not (CPE.match(entry["firmware_cpe"]) and entry["firmware_cpe"].startswith("cpe:2.3:o:")):
        errors.append("firmware_cpe must be a CPE 2.3 name of firmware (cpe:2.3:o:...)")
    if "country_of_origin" in entry and not entry["country_of_origin"].strip():
        errors.append("country_of_origin must not be empty; leave it out if unknown")
    return errors


def save(registry, stock, retired):
    errors = validate(registry, stock, retired)
    if errors:
        raise Error("\n".join(errors))
    write(REGISTRY, registry)
    write(STOCK, stock)
    write(RETIRED, retired)


def require_db_dir():
    if not DB:
        raise Error("give the part database directory with --db or PARTSDB_DIR")


def open_db():
    require_db_dir()
    if not os.path.exists(REGISTRY):
        raise Error("no database, run: partsdb.py init")
    return load(REGISTRY), load(STOCK), load(RETIRED) if os.path.exists(RETIRED) else {}


# Commands

def cmd_init(args):
    require_db_dir()
    if os.path.exists(REGISTRY):
        raise Error(f"database already exists in {DB}")
    if os.path.isdir(DB) and [f for f in os.listdir(DB) if not f.startswith(".")]:
        raise Error(f"{DB} is not empty")
    os.makedirs(DB, exist_ok=True)
    write(REGISTRY, {})
    write(STOCK, {})
    write(RETIRED, {})
    print(f"Initialized {DB}")


def mentioned_in_repo(pn):
    """Return the first repository file that mentions pn, or None."""
    for top, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SCAN_SKIP_DIRS and os.path.join(top, d) != DB]
        for name in files:
            if name.endswith(SCAN_SUFFIXES):
                path = os.path.join(top, name)
                try:
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        if pn in f.read():
                            return os.path.relpath(path, ROOT)
                except OSError:
                    pass
    return None


def next_number(cls, registry, retired):
    """Next part number in a class: a reusable retired number first, else the next in sequence."""
    if EARLY_STAGE:
        for pn in sorted(p for p in retired if p.startswith(f"SRLY-{cls}-")):
            where = mentioned_in_repo(pn)
            if where:
                print(f"note: {pn} is retired but still mentioned in {where}, not reused", file=sys.stderr)
            else:
                return pn
    numbers = [int(m.group(2)) for m in map(PART_NUMBER.match, [*registry, *retired]) if m and m.group(1) == cls]
    return f"SRLY-{cls}-{max(numbers, default=0) + 1:06d}"


def cmd_new(args):
    registry, stock, retired = open_db()
    cls = args.cls.upper()
    if cls not in class_codes():
        raise Error(f"unknown class {cls}, see {NUMBERING_DOC}")
    for pn, entry in registry.items():
        if (entry["manufacturer"].lower(), entry["mpn"].lower()) == (args.manufacturer.lower(), args.mpn.lower()):
            raise Error(f"{args.manufacturer} {args.mpn} already has {pn}")
    pn = next_number(cls, registry, retired)
    retired.pop(pn, None)
    registry[pn] = {
        "manufacturer": args.manufacturer,
        "mpn": args.mpn,
        "description": args.description,
        "assigned": datetime.date.today().isoformat(),
    }
    save(registry, stock, retired)
    print(pn)


def cmd_describe(args):
    registry, stock, retired = open_db()
    if args.pn not in registry:
        raise Error(f"{args.pn}: not in registry")
    registry[args.pn]["description"] = args.description
    save(registry, stock, retired)


def cmd_attributes(args):
    registry, stock, retired = open_db()
    if args.pn not in registry:
        raise Error(f"{args.pn}: not in registry")
    entry = registry[args.pn]
    for key, val in (("country_of_origin", args.country), ("lifecycle", args.lifecycle),
                     ("ltb_date", args.ltb_date), ("contains_firmware", args.firmware),
                     ("cpe", args.cpe), ("firmware_cpe", args.firmware_cpe)):
        if val is None:
            continue
        if val == "":
            entry.pop(key, None)
        else:
            entry[key] = val
    if entry.get("lifecycle") != "LTB":
        entry.pop("ltb_date", None)
    entry["attributes_checked"] = datetime.date.today().isoformat()
    save(registry, stock, retired)


def cmd_delete(args):
    if not EARLY_STAGE:
        raise Error("part numbers can't be deleted once the library is released (EARLY_STAGE is False)")
    registry, stock, retired = open_db()
    if args.pn not in registry:
        raise Error(f"{args.pn}: not in registry")
    held = {loc: qty for loc, qty in stock.get(args.pn, {}).items() if qty}
    if held:
        raise Error(f"{args.pn}: still in stock {held}, remove the stock first")
    stock.pop(args.pn, None)
    retired[args.pn] = {**registry.pop(args.pn), "deleted": datetime.date.today().isoformat()}
    save(registry, stock, retired)
    print(f"Deleted {args.pn}, the number is retired" + (" and can be reused" if EARLY_STAGE else ""))


def print_parts(registry, stock, pns):
    for pn in pns:
        e = registry[pn]
        qty = sum(stock.get(pn, {}).values())
        print(f"{pn}  {e['manufacturer']}  {e['mpn']}  stock {qty}  {e['description']}")


def cmd_list(args):
    registry, stock, retired = open_db()
    pns = sorted(pn for pn in registry if not args.cls or pn.startswith(f"SRLY-{args.cls.upper()}-"))
    print_parts(registry, stock, pns)


def cmd_find(args):
    registry, stock, retired = open_db()
    pns = sorted(pn for pn, e in registry.items()
                 if fnmatch.fnmatchcase(e["mpn"].upper(), args.mpn.upper())
                 and (not args.manufacturer or e["manufacturer"].lower() == args.manufacturer.lower()))
    print_parts(registry, stock, pns)


def cmd_show(args):
    """One part: a JSON object. Several parts: a JSON list of objects, in the order given."""
    registry, stock, retired = open_db()
    missing = [pn for pn in args.pn if pn not in registry]
    if missing:
        raise Error(f"not in registry: {', '.join(missing)}")
    parts = [{"part": pn, **registry[pn], "stock": stock.get(pn, {})} for pn in args.pn]
    print(dump(parts[0] if len(parts) == 1 else parts), end="")


def cmd_stock(args):
    registry, stock, retired = open_db()
    if args.action == "show":
        for pn in sorted(stock) if not args.pn else [args.pn]:
            for location, qty in sorted(stock.get(pn, {}).items()):
                print(f"{pn}  {location}  {qty}")
        return
    if args.pn not in registry:
        raise Error(f"{args.pn}: not in registry")
    locations = stock.setdefault(args.pn, {})
    current = locations.get(args.location, 0)
    qty = {"set": args.qty, "add": current + args.qty, "remove": current - args.qty}[args.action]
    if qty < 0:
        raise Error(f"{args.pn} {args.location}: only {current} in stock")
    locations[args.location] = qty
    save(registry, stock, retired)
    print(f"{args.pn}  {args.location}  {qty}")


def cmd_validate(args):
    errors = validate(*open_db())
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        sys.exit(1)
    print("OK")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--db", default=os.environ.get("PARTSDB_DIR", ""),
                   help="part database directory (default: PARTSDB_DIR)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create an empty database").set_defaults(func=cmd_init)

    s = sub.add_parser("new", help="assign the next part number in a class")
    s.add_argument("cls", metavar="CLASS")
    s.add_argument("--manufacturer", required=True)
    s.add_argument("--mpn", required=True)
    s.add_argument("--description", required=True)
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("describe", help="change the description of a part")
    s.add_argument("pn")
    s.add_argument("description")
    s.set_defaults(func=cmd_describe)

    s = sub.add_parser("attributes", help="set the HBOM attributes of a part; an empty value removes one")
    s.add_argument("pn")
    s.add_argument("--country", help="country of origin, free text")
    s.add_argument("--lifecycle", help=", ".join(LIFECYCLES))
    s.add_argument("--ltb-date", help="last time buy date, ISO 8601; only with --lifecycle LTB")
    s.add_argument("--firmware", help=", ".join(FIRMWARE))
    s.add_argument("--cpe", help="CPE 2.3 name of the part, cpe:2.3:h:...; for firmware-bearing parts")
    s.add_argument("--firmware-cpe", help="CPE 2.3 name of the firmware, cpe:2.3:o:..., as used by NVD")
    s.set_defaults(func=cmd_attributes)

    s = sub.add_parser("delete", help="delete a part number (early stage only); the number is retired")
    s.add_argument("pn")
    s.set_defaults(func=cmd_delete)

    s = sub.add_parser("list", help="list parts")
    s.add_argument("--class", dest="cls")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("find", help="find parts by manufacturer part number (glob)")
    s.add_argument("--mpn", required=True)
    s.add_argument("--manufacturer")
    s.set_defaults(func=cmd_find)

    s = sub.add_parser("show", help="show parts as JSON: an object for one part, a list for several")
    s.add_argument("pn", nargs="+")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("stock", help="show or change stock")
    s.add_argument("action", choices=["show", "set", "add", "remove"])
    s.add_argument("pn", nargs="?")
    s.add_argument("location", nargs="?")
    s.add_argument("qty", nargs="?", type=int)
    s.set_defaults(func=cmd_stock)

    sub.add_parser("validate", help="check the whole database").set_defaults(func=cmd_validate)

    args = p.parse_args()
    set_db(args.db)
    if args.command == "stock" and args.action != "show" and None in (args.pn, args.location, args.qty):
        p.error(f"stock {args.action} needs PN LOCATION QTY")
    try:
        args.func(args)
    except Error as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
