# How to Add Parts into the Library

This guide walks you through adding a new part to the Screenly KiCad Part Library, from choosing its class to opening the pull request. It is written for hardware designers, and AI assistants follow the same steps.

When you are done, the part has:

- a **symbol** in the Screenly KiCad Part Library, with its class keys filled in from the datasheet,
- a **footprint** in the Screenly KiCad Footprint Library (unless it is an [off-board item](bom-standard.md#off-board-items)),
- a **part number** in the Screenly part database.

Related standards:

- [Part Numbering Standard](part-numbering-standard.md): class codes and part numbers.
- [Screenly KiCad Part Library Standard](part-library-standard.md): class definitions, keys and footprint rules.
- [Assembly Part Library Standard](assembly-part-library-standard.md): parts that are not designed in KiCad.
- [BOM Standard](bom-standard.md): how parts are used in designs and BOMs.

## Before You Start

You need:

- **KiCad 10**, with the Screenly libraries added:
  - Symbol library: **Preferences → Manage Symbol Libraries**, add [`library/Screenly.kicad_sym`](../library/Screenly.kicad_sym) with the nickname `Screenly`.
  - Footprint library: **Preferences → Manage Footprint Libraries**, add [`library/Screenly.pretty`](../library/Screenly.pretty) with the nickname `Screenly`.
- **Python 3**, to run `tools/partsdb.py`.
- **Access to the Screenly part database.** The database is private and not part of this repository. Set the `PARTSDB_DIR` environment variable to its directory, for example in your shell profile:

  ```
  export PARTSDB_DIR=<path to the part database>
  ```

  You can also give the directory per command with `--db <path>`. To start a new, empty database, for example to try the workflow, run `tools/partsdb.py --db <empty directory> init`.

- **The part's official datasheet**, downloaded from the manufacturer.

## Ground Rules

- **The official datasheet is the only source of part data.** Note its revision. Distributor pages, search results and summaries can point you to a part, but values are never copied from them.
- **Don't guess.** If a value is not in the datasheet, leave the field out and mention it in the pull request.
- **Change the part database only with `tools/partsdb.py`.** The tool validates every change. Never edit the database files by hand, and never write the database's location into this repository.
- **Ask when in doubt.** If the class, a value or a `family` pattern is unclear, ask the hardware team before continuing.

## 1. Choose the Class

The class decides which fields the symbol needs and which reference prefix it uses.

1. Find the class of the part in the [Part Numbering Standard](part-numbering-standard.md).
2. If the class is in the [Assembly Part Library Standard](assembly-part-library-standard.md), the part has no symbol and no footprint. Skip to [step 5](#5-register-the-part-number).
3. Otherwise, open its definition in the [Screenly KiCad Part Library Standard](part-library-standard.md#class-definitions). If the class has no definition yet, it must be defined there first.

## 2. Check That the Part Is New

Search the part database by manufacturer part number. Wildcards (`*`, `?`) are allowed:

```
tools/partsdb.py find --mpn '<MPN>'
```

If the part already has a part number, don't register it again. If the library already has a symbol for it, update that symbol instead of adding a new one.

## 3. Add the Footprint

Skip this step for [off-board items](bom-standard.md#off-board-items), such as cable-connected displays, batteries on wire leads, or connectors listed only for the BOM.

1. In the **Footprint Editor**, check whether a suitable footprint already exists in the `Screenly` library.
2. If not, create one there. To reuse a footprint from KiCad's built-in or a third-party library, copy it into the `Screenly` library first. Designs never reference other footprint libraries directly.
3. Check the pads against the recommended land pattern in the datasheet.

## 4. Add the Symbol

In the **Symbol Editor**, add the symbol to the `Screenly` library. Open **Symbol Properties** and set the fields:

| Field         | What to enter                                                               |
| ------------- | --------------------------------------------------------------------------- |
| `Reference`   | The class reference prefix followed by `?`, e.g. `U?`, `R?`, `J?`. The `?` lets KiCad number the reference when the schematic is annotated. |
| `Value`       | The manufacturer part number, or the value to show on the schematic         |
| `Footprint`   | The footprint from step 3, e.g. `Screenly:<footprint name>`. Leave it empty for off-board items. |
| `Datasheet`   | URL of the official datasheet                                               |
| `Description` | Short description of the part                                               |
| Keywords      | Search keywords, including the manufacturer part number                     |
| Class keys    | One field per key of the class, named exactly as the key. Add them with the **+** button in the fields table. |

Then:

1. **Fill in every class key from the datasheet.** Write values with units and SI prefixes as described in the [BOM Standard](bom-standard.md#designconstraint-syntax), and use only the listed members for set keys.
2. **Choose the `family` pattern.** Every manufacturer part number the pattern matches must be a drop-in replacement for the part. List the part numbers it matches and check each one against the datasheet. If any of them is not a drop-in replacement, make the pattern narrower.
3. **Remove all other fields.** Manufacturer names, alternative part numbers and supplier data don't belong in the symbol.
4. **Set the attributes** under **Symbol Properties**:
   - Parts on the board: **Exclude from bill of materials** and **Exclude from board** both off.
   - Off-board items: **Exclude from board** on, **Exclude from bill of materials** off.

## 5. Register the Part Number

Register the exact part that will be bought, by its manufacturer part number:

```
tools/partsdb.py new <CLASS> --manufacturer '<Manufacturer>' --mpn '<MPN>' --description '<Description>'
```

The tool checks that the part is not registered yet, assigns the next free part number in the class and prints it.

If the symbol's `family` pattern allows several parts and more than one of them will be bought, register each of them.

## 6. Record Stock

Only if the part is already in stock:

```
tools/partsdb.py stock set <PART NUMBER> <LOCATION> <QUANTITY>
```

Locations are lowercase names, e.g. `screenly` or `contract_manufacturer`.

## 7. Check and Open a Pull Request

1. Run `tools/partsdb.py validate`. It must print `OK`.
2. Reopen the symbol and footprint in KiCad and check that they load without errors.
3. Open a pull request with the symbol and footprint changes. Mention the datasheet revision you used and any values that were not in the datasheet. The part database is not part of this repository, so its changes are not part of the pull request.

## Example: Raspberry Pi CM5

| Step | Result |
| ---- | ------ |
| 1. Class | `MOD` (Modules) |
| 2. New part | `tools/partsdb.py find --mpn 'CM5*'` finds nothing |
| 3. Footprint | One module footprint that holds both board-to-board connectors at the exact module spacing. The two connectors are added to designs as off-board `CON` symbols, so they appear in the BOM. |
| 4. Symbol | `Reference` `U?`, `Value` `CM5104064`, `Datasheet` CM5 datasheet, `family` `CM5*`, `ram` `4GB`, `storage` `64GB`, `wireless` `yes`, `temp_min` `-20C`, `temp_max` `85C` (datasheet section 4.4) |
| 5. Register | `tools/partsdb.py new MOD --manufacturer 'Raspberry Pi' --mpn CM5104064 --description 'Raspberry Pi Compute Module 5, wireless, 4GB RAM, 64GB eMMC'` prints `SRLY-MOD-000001` |

`family CM5*` matches every CM5 variant, including the CM5 Lite, which has no eMMC. The `storage` key keeps the Lite out, so it must stay set on every CM5 instance.

## Checklist

- [ ] Class chosen, and defined in the standard
- [ ] Part not registered yet
- [ ] Footprint in the `Screenly` footprint library and checked against the datasheet, or the part is an off-board item
- [ ] Symbol: `Reference` ends in `?`, official `Datasheet`, every class key from the datasheet, no other fields
- [ ] `family` pattern checked: every match is a drop-in replacement
- [ ] Attributes set for on-board or off-board use
- [ ] Part number registered with `tools/partsdb.py new`
- [ ] `tools/partsdb.py validate` prints `OK`
- [ ] Symbol and footprint load in KiCad
- [ ] Pull request opened, with the datasheet revision

## Open Items

- Naming convention for symbols and footprints.
- Location and format of 3D models.
- How the class of a symbol is recorded, since several classes share a reference prefix (e.g. `U`).
