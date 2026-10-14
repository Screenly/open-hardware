#!/usr/bin/env python3
"""Screenly part database: assigned part numbers and stock.

The database is a directory, given by --db or the PARTSDB_DIR environment
variable, that holds two JSON files:

  registry.json  every assigned part number; entries are never removed
  stock.json     quantity per part number and location

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
DB = REGISTRY = STOCK = ""
NUMBERING_DOC = os.path.join(ROOT, "docs", "part-numbering-standard.md")

PART_NUMBER = re.compile(r"^SRLY-([A-Z]{3})-([0-9]{6})$")
LOCATION = re.compile(r"^[a-z0-9_]+$")
REGISTRY_FIELDS = {"manufacturer", "mpn", "description", "assigned"}


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
    global DB, REGISTRY, STOCK
    DB = os.path.abspath(os.path.expanduser(path)) if path else ""
    REGISTRY = os.path.join(DB, "registry.json")
    STOCK = os.path.join(DB, "stock.json")






# Validation

def class_codes():
    with open(NUMBERING_DOC, encoding="utf-8") as f:
        return set(re.findall(r"^\| `([A-Z]{3})` \|", f.read(), re.M))


def validate(registry, stock):
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
        if set(entry) != REGISTRY_FIELDS:
            errors.append(f"{pn}: fields must be {sorted(REGISTRY_FIELDS)}")
            continue
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
    return errors




def save(registry, stock):
    errors = validate(registry, stock)
    if errors:
        raise Error("\n".join(errors))
    write(REGISTRY, registry)
    write(STOCK, stock)


def require_db_dir():
    if not DB:
        raise Error("give the part database directory with --db or PARTSDB_DIR")


def open_db():
    require_db_dir()
    if not os.path.exists(REGISTRY):
        raise Error("no database, run: partsdb.py init")
    return load(REGISTRY), load(STOCK)


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
    print(f"Initialized {DB}")


def cmd_new(args):
    registry, stock = open_db()
    cls = args.cls.upper()
    if cls not in class_codes():
        raise Error(f"unknown class {cls}, see {NUMBERING_DOC}")
    for pn, entry in registry.items():
        if (entry["manufacturer"].lower(), entry["mpn"].lower()) == (args.manufacturer.lower(), args.mpn.lower()):
            raise Error(f"{args.manufacturer} {args.mpn} already has {pn}")
    numbers = [int(m.group(2)) for m in map(PART_NUMBER.match, registry) if m and m.group(1) == cls]
    pn = f"SRLY-{cls}-{max(numbers, default=0) + 1:06d}"
    registry[pn] = {
        "manufacturer": args.manufacturer,
        "mpn": args.mpn,
        "description": args.description,
        "assigned": datetime.date.today().isoformat(),
    }
    save(registry, stock)
    print(pn)


def cmd_describe(args):
    registry, stock = open_db()
    if args.pn not in registry:
        raise Error(f"{args.pn}: not in registry")
    registry[args.pn]["description"] = args.description
    save(registry, stock)


def print_parts(registry, stock, pns):
    for pn in pns:
        e = registry[pn]
        qty = sum(stock.get(pn, {}).values())
        print(f"{pn}  {e['manufacturer']}  {e['mpn']}  stock {qty}  {e['description']}")


def cmd_list(args):
    registry, stock = open_db()
    pns = sorted(pn for pn in registry if not args.cls or pn.startswith(f"SRLY-{args.cls.upper()}-"))
    print_parts(registry, stock, pns)


def cmd_find(args):
    registry, stock = open_db()
    pns = sorted(pn for pn, e in registry.items()
                 if fnmatch.fnmatchcase(e["mpn"].upper(), args.mpn.upper())
                 and (not args.manufacturer or e["manufacturer"].lower() == args.manufacturer.lower()))
    print_parts(registry, stock, pns)


def cmd_show(args):
    registry, stock = open_db()
    if args.pn not in registry:
        raise Error(f"{args.pn}: not in registry")
    print(dump({"part": args.pn, **registry[args.pn], "stock": stock.get(args.pn, {})}), end="")


def cmd_stock(args):
    registry, stock = open_db()
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
    save(registry, stock)
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

    s = sub.add_parser("list", help="list parts")
    s.add_argument("--class", dest="cls")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("find", help="find parts by manufacturer part number (glob)")
    s.add_argument("--mpn", required=True)
    s.add_argument("--manufacturer")
    s.set_defaults(func=cmd_find)

    s = sub.add_parser("show", help="show one part")
    s.add_argument("pn")
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
