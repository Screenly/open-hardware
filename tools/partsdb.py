#!/usr/bin/env python3
"""Screenly part database: assigned part numbers and stock.

The database is a directory, given by --db or the PARTSDB_DIR environment
variable, that holds these JSON files:

  registry.json  every part number in use, with the part attributes the
                 HBOM needs (country of origin, lifecycle, firmware, CPE) and the
                 distributors it is bought from (distributor part numbers, no prices)
  stock.json     quantity per part number and location
  retired.json   deleted part numbers
  distributors.json
                 the distributors parts can be bought from: a single-word name
                 and the website.
                 A distributor is added here before any part refers to it.

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
DB = REGISTRY = STOCK = RETIRED = DISTRIBUTORS_FILE = ""
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
ATTRIBUTE_FIELDS = {
    "country_of_origin",
    "lifecycle",
    "ltb_date",
    "contains_firmware",
    "cpe",
    "firmware_cpe",
    "attributes_validated",
    "distributor_info",
}
# distributor_info: ordered list, most preferred distributor first, of
# {"distributor", "part_number", "link" (optional), "validated"}. Prices and stock
# are not stored; they are fetched when needed or come from purchase records.
DISTRIBUTOR_FIELDS = {"distributor", "part_number", "link", "validated"}
# distributors.json: {name: {"website"}}
DISTRIBUTOR_NAME = re.compile(r"^[A-Za-z0-9]+$")
DISTRIBUTOR_TABLE_FIELDS = {"website"}
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
    global DB, REGISTRY, STOCK, RETIRED, DISTRIBUTORS_FILE
    DB = os.path.abspath(os.path.expanduser(path)) if path else ""
    REGISTRY = os.path.join(DB, "registry.json")
    STOCK = os.path.join(DB, "stock.json")
    RETIRED = os.path.join(DB, "retired.json")
    DISTRIBUTORS_FILE = os.path.join(DB, "distributors.json")


# Validation


def class_codes():
    with open(NUMBERING_DOC, encoding="utf-8") as f:
        return set(re.findall(r"^\| `([A-Z]{3})` \|", f.read(), re.M))


def not_strings(d, keys):
    """Keys of d that are present but don't hold a string."""
    return [k for k in keys if k in d and not isinstance(d[k], str)]


def is_date(v):
    try:
        datetime.date.fromisoformat(v)
        return True
    except (TypeError, ValueError):
        return False


def canonical_distributor(table, name):
    """The table's spelling of a distributor name given in any letter case, or None."""
    return next((n for n in table if n.lower() == name.strip().lower()), None)


def distributor_table_errors(distributors):
    errors, seen = [], {}
    for name, d in distributors.items():
        if not DISTRIBUTOR_NAME.match(name):
            errors.append(f"distributor {name!r}: the name must be a single word of letters and digits")
        if name.lower() in seen:
            errors.append(f"distributor {name}: same name as {seen[name.lower()]}")
        seen[name.lower()] = name
        if not isinstance(d, dict) or set(d) != DISTRIBUTOR_TABLE_FIELDS or not_strings(d, ["website"]):
            errors.append(f"distributor {name}: the only field is website, a string")
            continue
        if not re.match(r"^https://[^\s/]+\.[^\s]+$", d["website"]):
            errors.append(f"distributor {name}: website must be an https URL")
    return errors


def validate(registry, stock, retired, distributors):
    errors = distributor_table_errors(distributors)
    codes = class_codes()
    seen = {}
    for pn, entry in registry.items():
        m = PART_NUMBER.match(pn)
        if not m:
            errors.append(f"{pn}: not a valid part number")
            continue
        if m.group(1) not in codes:
            errors.append(f"{pn}: unknown class {m.group(1)}")
        if not set(entry) >= REGISTRY_FIELDS or set(entry) - REGISTRY_FIELDS - ATTRIBUTE_FIELDS:
            errors.append(f"{pn}: fields must be {sorted(REGISTRY_FIELDS)}, optionally {sorted(ATTRIBUTE_FIELDS)}")
            continue
        wrong = not_strings(entry, sorted(REGISTRY_FIELDS | ATTRIBUTE_FIELDS - {"distributor_info"}))
        if wrong:
            errors.append(f"{pn}: must be strings: {', '.join(wrong)}")
            continue
        errors += [f"{pn}: {e}" for e in attribute_errors(entry, distributors)]
        if not entry["manufacturer"] or not entry["mpn"]:
            errors.append(f"{pn}: manufacturer and mpn are required")
        key = (entry["manufacturer"].lower(), entry["mpn"].lower())
        if key in seen:
            errors.append(f"{pn}: same part as {seen[key]}")
        seen[key] = pn
        if not is_date(entry["assigned"]):
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


def attribute_errors(entry, distributors):
    errors = []
    if entry.get("lifecycle", "Unknown") not in LIFECYCLES:
        errors.append(f"lifecycle must be one of {', '.join(LIFECYCLES)}")
    if entry.get("contains_firmware", "Unknown") not in FIRMWARE:
        errors.append(f"contains_firmware must be one of {', '.join(FIRMWARE)}")
    if "ltb_date" in entry and entry.get("lifecycle") != "LTB":
        errors.append("ltb_date is only allowed with lifecycle LTB")
    for key in ("ltb_date", "attributes_validated"):
        if key in entry and not is_date(entry[key]):
            errors.append(f"{key} must be an ISO 8601 date")
    if "cpe" in entry and not (CPE.match(entry["cpe"]) and entry["cpe"].startswith("cpe:2.3:h:")):
        errors.append("cpe must be a CPE 2.3 name of a hardware part (cpe:2.3:h:...)")
    if "firmware_cpe" in entry and not (
        CPE.match(entry["firmware_cpe"]) and entry["firmware_cpe"].startswith("cpe:2.3:o:")
    ):
        errors.append("firmware_cpe must be a CPE 2.3 name of firmware (cpe:2.3:o:...)")
    info = entry.get("distributor_info", [])
    if not isinstance(info, list):
        return errors + ["distributor_info must be a list"]
    for i, d in enumerate(info):
        where = f"distributor_info[{i}]"
        if (
            not isinstance(d, dict)
            or not {"distributor", "part_number", "validated"} <= set(d)
            or set(d) - DISTRIBUTOR_FIELDS
            or not_strings(d, sorted(DISTRIBUTOR_FIELDS))
        ):
            errors.append(
                f"{where}: fields must be distributor, part_number, validated and optionally link, all strings"
            )
            continue
        if d["distributor"] not in distributors:
            errors.append(
                f"{where}: distributor {d['distributor']!r} is not in the distributor table "
                f"({', '.join(distributors) or 'empty'})"
            )
            continue
        if not d["part_number"].strip():
            errors.append(f"{where}: invalid {d['distributor']} part number {d['part_number']!r}")
        if "link" in d and not d["link"].startswith("https://"):
            errors.append(f"{where}: link must be an https URL")
        if not is_date(d["validated"]):
            errors.append(f"{where}: validated must be an ISO 8601 date")
    names = [d.get("distributor") for d in info if isinstance(d, dict)]
    if len(names) != len(set(names)):
        errors.append("distributor_info lists a distributor more than once")
    if "country_of_origin" in entry and not entry["country_of_origin"].strip():
        errors.append("country_of_origin must not be empty; leave it out if unknown")
    return errors


def load_distributors():
    return load(DISTRIBUTORS_FILE) if os.path.exists(DISTRIBUTORS_FILE) else {}


def save(registry, stock, retired, distributors=None):
    """Validate the whole database and write it. The distributor table is written only when given."""
    table = load_distributors() if distributors is None else distributors
    errors = validate(registry, stock, retired, table)
    if errors:
        raise Error("\n".join(errors))
    write(REGISTRY, registry)
    write(STOCK, stock)
    write(RETIRED, retired)
    if distributors is not None:
        write(DISTRIBUTORS_FILE, distributors)


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
    write(DISTRIBUTORS_FILE, {})
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
    changes = {"description": args.description, "manufacturer": args.manufacturer, "mpn": args.mpn}
    changes = {k: v for k, v in changes.items() if v is not None}
    if not changes:
        raise Error("give a description, --manufacturer or --mpn")
    entry = registry[args.pn]
    if any(k in changes and changes[k] != entry[k] for k in ("manufacturer", "mpn")):
        # A different physical part: only allowed before it is stocked, and the old part's
        # distributors and attributes no longer apply.
        held = {loc: qty for loc, qty in stock.get(args.pn, {}).items() if qty}
        if held:
            raise Error(f"{args.pn}: in stock {held}; a stocked part can't change its manufacturer part number")
        dropped = sorted(k for k in ATTRIBUTE_FIELDS if k in entry)
        for k in dropped:
            del entry[k]
        if dropped:
            print(f"note: removed {', '.join(dropped)}; set them again for the new part", file=sys.stderr)
    entry.update(changes)
    save(registry, stock, retired)


def cmd_attributes(args):
    registry, stock, retired = open_db()
    if args.pn not in registry:
        raise Error(f"{args.pn}: not in registry")
    entry = registry[args.pn]
    changes = (
        ("country_of_origin", args.country),
        ("lifecycle", args.lifecycle),
        ("ltb_date", args.ltb_date),
        ("contains_firmware", args.firmware),
        ("cpe", args.cpe),
        ("firmware_cpe", args.firmware_cpe),
    )
    if all(val is None for _, val in changes) and not args.confirm:
        raise Error("give at least one attribute, or --confirm to mark the current attributes as validated")
    for key, val in changes:
        if val is None:
            continue
        if val == "":
            entry.pop(key, None)
        else:
            entry[key] = val
    if entry.get("lifecycle") != "LTB":
        if args.ltb_date:
            raise Error("--ltb-date is only allowed with lifecycle LTB")
        entry.pop("ltb_date", None)  # the part left LTB: the old date no longer applies
    entry["attributes_validated"] = datetime.date.today().isoformat()
    save(registry, stock, retired)


def cmd_distributor(args):
    """Add, update, reorder or remove one distributor of a part. Writing an entry sets its
    validated date (today, or --validated): the date its data was confirmed at the distributor."""
    registry, stock, retired = open_db()
    if args.pn not in registry:
        raise Error(f"{args.pn}: not in registry")
    table = load_distributors()
    name = canonical_distributor(table, args.name)
    if not name:
        raise Error(
            f"{args.name}: not in the distributor table ({', '.join(table) or 'empty'}); "
            f"add it first with: partsdb.py distributors add NAME --website URL"
        )
    args.name = name
    entry = registry[args.pn]
    info = entry.get("distributor_info", [])
    old = next((d for d in info if d["distributor"] == args.name), None)
    if args.remove:
        if not old:
            raise Error(f"{args.pn}: no {args.name} entry")
        info.remove(old)
    else:
        if not args.part_number and not old:
            raise Error("--part-number is required for a new distributor")
        d = old or {"distributor": args.name}
        if args.part_number:
            d["part_number"] = args.part_number
        if args.link is not None:
            if args.link:
                d["link"] = args.link
            else:
                d.pop("link", None)
        d["validated"] = args.validated or datetime.date.today().isoformat()
        # Keep an existing entry's place in the preference order; new entries go last.
        pos = info.index(old) if old else len(info)
        if old:
            info.remove(old)
        info.insert(0 if args.first else pos, d)
    if info:
        entry["distributor_info"] = info
    else:
        entry.pop("distributor_info", None)
    save(registry, stock, retired)


def cmd_distributors(args):
    """The distributor table: list, add, update or remove a distributor."""
    registry, stock, retired = open_db()
    table = load_distributors()
    if args.action == "list":
        if args.json:
            print(dump(table), end="")
        else:
            for name, d in table.items():
                print(f"{name:10} {d['website']}")
        return
    if not args.name:
        raise Error(f"distributors {args.action}: give the distributor name")
    name = canonical_distributor(table, args.name)
    if args.action == "add":
        if name:
            raise Error(f"{args.name}: already in the table as {name}")
        if not args.website:
            raise Error("--website is required")
        table[args.name] = {"website": args.website}
        name = args.name
    elif not name:
        raise Error(f"{args.name}: not in the distributor table")
    elif args.action == "remove":
        users = sorted(
            pn for pn, e in registry.items() if any(d["distributor"] == name for d in e.get("distributor_info", []))
        )
        if users:
            raise Error(f"{name} is used by {len(users)} parts, remove it from them first: {', '.join(users)}")
        del table[name]
    if args.action == "update":
        if not args.website:
            raise Error("--website is required")
        table[name]["website"] = args.website
    save(registry, stock, retired, dict(sorted(table.items(), key=lambda x: x[0].lower())))


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
    print(f"Deleted {args.pn}, the number is retired and can be reused")


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
    pns = sorted(
        pn
        for pn, e in registry.items()
        if fnmatch.fnmatchcase(e["mpn"].upper(), args.mpn.upper())
        and (not args.manufacturer or e["manufacturer"].lower() == args.manufacturer.lower())
    )
    print_parts(registry, stock, pns)


def cmd_show(args):
    """One part: a JSON object. Several parts: a JSON list of objects, in the order given.
    With --skip-missing: always a list, of the given parts that are in the registry."""
    registry, stock, retired = open_db()
    missing = [pn for pn in args.pn if pn not in registry]
    if missing and not args.skip_missing:
        raise Error(f"not in registry: {', '.join(missing)}")
    parts = [{"part": pn, **registry[pn], "stock": stock.get(pn, {})} for pn in args.pn if pn in registry]
    print(dump(parts[0] if len(parts) == 1 and not args.skip_missing else parts), end="")


def cmd_stock(args):
    registry, stock, retired = open_db()
    if args.action == "show":
        for pn in sorted(stock) if not args.pn else [args.pn]:
            for location, qty in sorted(stock.get(pn, {}).items()):
                print(f"{pn}  {location}  {qty}")
        return
    if args.qty < 0:
        raise Error(f"stock {args.action}: the quantity must not be negative")
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
    errors = validate(*open_db(), load_distributors())
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        sys.exit(1)
    print("OK")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--db", default=os.environ.get("PARTSDB_DIR", ""), help="part database directory (default: PARTSDB_DIR)"
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create an empty database").set_defaults(func=cmd_init)

    s = sub.add_parser("new", help="assign the next part number in a class")
    s.add_argument("cls", metavar="CLASS")
    s.add_argument("--manufacturer", required=True)
    s.add_argument("--mpn", required=True)
    s.add_argument("--description", required=True)
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("describe", help="change the description, manufacturer or manufacturer part number of a part")
    s.add_argument("pn")
    s.add_argument("description", nargs="?")
    s.add_argument("--manufacturer")
    s.add_argument(
        "--mpn", help="a different part: only while it is not in stock; removes the old distributors and attributes"
    )
    s.set_defaults(func=cmd_describe)

    s = sub.add_parser("attributes", help="set the HBOM attributes of a part; an empty value removes one")
    s.add_argument("pn")
    s.add_argument("--country", help="country of origin, free text")
    s.add_argument("--lifecycle", help=", ".join(LIFECYCLES))
    s.add_argument("--ltb-date", help="last time buy date, ISO 8601; only with --lifecycle LTB")
    s.add_argument("--firmware", help=", ".join(FIRMWARE))
    s.add_argument("--cpe", help="CPE 2.3 name of the part, cpe:2.3:h:...; for firmware-bearing parts")
    s.add_argument("--firmware-cpe", help="CPE 2.3 name of the firmware, cpe:2.3:o:..., as used by NVD")
    s.add_argument(
        "--confirm",
        action="store_true",
        help="the attributes were checked and are unchanged: only set attributes_validated to today",
    )
    s.set_defaults(func=cmd_attributes)

    s = sub.add_parser(
        "distributor",
        help="add, update, reorder or remove a distributor of a part; "
        "the list order is the part's distributor preference",
    )
    s.add_argument("pn")
    s.add_argument("--name", required=True, help="a name from the distributor table (not case-sensitive)")
    s.add_argument("--part-number", help="the distributor's part number, e.g. C307331")
    s.add_argument("--link", help="product page URL; an empty value removes it")
    s.add_argument("--validated", help="date the data was confirmed at the distributor, ISO 8601 (default: today)")
    s.add_argument("--first", action="store_true", help="make this the part's preferred distributor")
    s.add_argument("--remove", action="store_true", help="remove this distributor from the part")
    s.set_defaults(func=cmd_distributor)

    s = sub.add_parser(
        "distributors",
        help="list, add, update or remove distributors in the distributor table; "
        "a distributor must be in the table before a part refers to it",
    )
    s.add_argument("action", choices=("list", "add", "update", "remove"))
    s.add_argument("name", nargs="?", help="single-word name, e.g. LCSC or DigiKey")
    s.add_argument("--website", help="https URL of the distributor's website")
    s.add_argument("--json", action="store_true", help="list: print the table as JSON")
    s.set_defaults(func=cmd_distributors)

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
    s.add_argument(
        "--skip-missing",
        action="store_true",
        help="leave out part numbers that are not in the registry; always print a list",
    )
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
