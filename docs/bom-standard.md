# Bill of Materials (BOM) Standard

How Screenly hardware designs specify components, and how BOMs are produced from them for each manufacturing order.

## Overview

BOMs are produced in two stages:

1. **Design.** The KiCad design states *what each component must satisfy*, in the [class key fields](#class-key-fields) of each symbol, not which stock item to buy.
2. **Order.** Just before a manufacturing order, a manually triggered CI job resolves the design: it picks the best approved parts from the company part database and writes a resolved BOM. All exports are generated from it. When company stock is short, the Order Helper finds the best parts to buy from distributors.

```
KiCad design ──► Resolver ◄── Company part database, company stock
(key fields)        │    ◄──► Order Helper ◄── Distributor APIs
                    ▼               │
              Resolved BOM          └──► Purchase list
              (per build)  ──► Manufacturing BOM (.xlsx)
                           ──► HBOM (CycloneDX)
```

This keeps designs valid as parts go out of stock or obsolete. The design never freezes a list of alternates; it is resolved against the parts available at order time.

## Principles

- **The KiCad design is the source of truth for requirements.** The Screenly KiCad Part Library is the source of truth for part data, and the company part database for part numbers and stock.
- **Only approved parts are used.** The resolver selects only from the company part database, never directly from distributor catalogs.
- **The footprint is a hard constraint.** A part placed on the board is only a candidate if it fits the footprint placed in the design. All footprints come from the Screenly KiCad Footprint Library (see [Footprints](part-library-standard.md#footprints)).
- **Every build is recorded.** Each order has its own resolved BOM and exports.
- **Resolution runs only in CI, under quality control.** BOMs for manufacturing are produced only by the manually triggered CI job, never locally. Its artifacts are not edited by hand.
- **A wrong or failed BOM means the source is wrong.** If the job cannot produce a correct BOM, the source is fixed and the job is run again: the KiCad design files for requirements, or the part database for part data. There are no manual workarounds.

## Stage 1: Design

### Screenly KiCad Part Library

The Screenly KiCad Part Library is the KiCad symbol library used by all Screenly designs. Its structure and the definition of each class are specified in the [Screenly KiCad Part Library Standard](part-library-standard.md).

### KiCad fields

| Field              | Set on              | Purpose                                                                |
| ------------------ | ------------------- | ---------------------------------------------------------------------- |
| `Reference`        | Instance            | Reference designator                                                   |
| `Value`            | Instance            | Human-readable value on the schematic                                  |
| `Footprint`        | Instance            | Hard constraint for part selection                                     |
| `Datasheet`        | Library or instance | Datasheet of the part the design is based on, for reference            |
| `Description`      | Library or instance | Short description of the symbol, for reference                         |
| `PartNumber`       | Library             | Screenly part number of the part the symbol is based on; its class code is the class of the symbol |
| `Manufacturer`     | Library             | Manufacturer of that part                                              |
| `MfrPartNum`       | Library             | Manufacturer part number of that part                                  |
| Class key fields   | Library or instance | Requirements the part must satisfy (see [Class key fields](#class-key-fields)) |
| DNP                | Instance            | Footprint placed but not assembled                                     |
| Exclude from BOM   | Instance or library | Not a physical part (e.g. logos)                                       |
| Exclude from board | Instance            | BOM item without a footprint (see [Off-board items](#off-board-items)) |

`Datasheet` and `Description` are informational. The resolver does not use them, and the exports take these values from the resolved part.

### One symbol per BOM item

Every item that is bought for a build has its own symbol, with its own class key fields. A symbol never stands for more than one item.

### Off-board items

Some items are part of the build but have no footprint of their own, such as a module plugged into board connectors or a battery on wire leads. They are drawn as separate symbols with KiCad's *Exclude from board* attribute: the symbol appears in the BOM, but not on the PCB.

- The item it attaches to is a separate symbol with a footprint. Usually the off-board item is plugged into a connector on the board. In the reverse case, a module footprint can hold the pads of the connectors it plugs into, and the connectors are the off-board items.
- An off-board item has no footprint, so it is matched by its class key fields alone. Its `family` and keys must fully define the fit with the board side.

Examples:

| Item                          | Symbols                                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| Raspberry Pi CM5              | `U1`: CM5 (`MOD`, on board), with one footprint that holds both board-to-board connectors at the exact module spacing. `J1`, `J2`: the two connectors (`CON`, off-board). |
| Battery on wire leads         | `J3`: wire-to-board connector (`CON`, on board). `BT1`: battery (`BAT`, off-board).       |
| Coin cell in a holder         | `J4`: battery holder (`CON`, on board). `BT2`: coin cell (`BAT`, off-board).              |

### Assembly variants

Designs use KiCad assembly variants to describe different builds of the same board. A variant can change which instances are DNP or excluded from the BOM, and can override field values, including class key fields. Every BOM is produced for exactly one variant.

### Class key fields

Every symbol has one field per key of its class, named exactly as the key (see [Class Definitions](part-library-standard.md#class-definitions)). The library symbol carries the values of the part it is based on. When the symbol is placed, the fields are copied to the instance and become the requirements for that instance: the resolver accepts any approved part whose values satisfy every field.

- **Edit the values that are critical.** Each key has a fixed comparison defined by its class (see [Comparisons](part-library-standard.md#comparisons)), so a field holds only a value, never an operator. For example, `tolerance` = `10%` always means 10% or better, and `power` = `0.1W` always means at least 0.1 W.
- **Delete the optional fields that are not critical.** A deleted optional field is not checked, so any part matches it.
- **Keep every required field.** A required field cannot be deleted or left empty.
- Values are written as described in [Field values](part-library-standard.md#field-values).
- The package is not a key. It is enforced from `Footprint`.
- **The designer is accountable for the key fields.** Keeping them intact is the designer's responsibility, including after **Update Symbols from Library**, which can re-add deleted fields and reset edited values depending on the options chosen. Check the key fields of updated symbols afterwards.

Example: a resistor placed from the library, after the designer kept the critical values and deleted the rest:

| Field       | Value  |
| ----------- | ------ |
| `value`     | `10K`  |
| `tolerance` | `10%`  |
| `power`     | `0.1W` |

### Classes

Each class defines its keys, which keys are required, and how each is compared. The definitions are in the [Screenly KiCad Part Library Standard](part-library-standard.md#class-definitions).

### Firmware-bearing parts

A part with `ContainsFirmware=Updatable` may only be selected if the product firmware has been verified on that exact manufacturer part number.

## Company Part Database

The company part database is private and is not part of this repository. It is changed only with `tools/partsdb.py` (see [How to Add Parts into the Library](how-to-add-parts-into-the-library.md)) and records:

- **Assigned part numbers.** Each Screenly part number, with the manufacturer, manufacturer part number and description of the part it was assigned to. Part numbers are never removed or reassigned.
- **Company stock.** The quantity per part number and location, including stock held at the contract manufacturer.

Part parameters are not stored in the database. They are the class key fields of the symbols in the [Screenly KiCad Part Library](#screenly-kicad-part-library).

### Part attributes

The HBOM needs these attributes for every part that ships:

| Attribute          | Values                                                    |
| ------------------ | --------------------------------------------------------- |
| `CountryOfOrigin`  | Free text                                                 |
| `LifeCycle`        | `Active`, `NRND`, `LTB`, `Obsolete`, `Preview`, `Unknown` |
| `LTBDate`          | ISO 8601 date, only with `LifeCycle=LTB`                  |
| `ContainsFirmware` | `None`, `Fixed`, `Updatable`, `Unknown`                   |

`ContainsFirmware` values:

- `None`: no firmware.
- `Fixed`: firmware in ROM or OTP, cannot be updated.
- `Updatable`: firmware in flash or EEPROM.
- `Unknown`: not yet determined.

An empty `LifeCycle` or `ContainsFirmware` is treated as `Unknown`. Never default to `None` or `No`.

Distributor data (prices, stock, distributor part numbers) is not stored. It is fetched by manufacturer part number when the job runs.

## Stage 2: Order

### Resolver

The resolver runs as a manually triggered CI job. The job is started with:

- The design revision (git ref) to resolve.
- The assembly variant to build.
- A build identifier.
- The build quantity (number of boards).

1. **Extract** instances and fields for the selected assembly variant with KiCad's own BOM export (`kicad-cli sch export bom`), so DNP, BOM exclusion and field overrides follow the variant.
2. **Find candidates** for each assembled instance: approved parts in the same class (from the `PartNumber`) that satisfy every class key field of the instance. For instances on the board, the part must also fit the instance footprint.
3. **Select** one part per instance using these rules in order:
   1. Parts with enough company stock for the build quantity.
   2. Parts that can be bought from distributors in enough quantity (see [Order Helper](#order-helper)).
   3. Fewer unique parts across the board. One part that satisfies the key fields of several instances is preferred over several parts.
   4. Total cost, including purchases.
   5. Lowest `PartNumber`, to break ties.
4. **Write** the resolved BOM, grouped by `PartNumber`.
5. **Plan purchases** for any shortfall with the [Order Helper](#order-helper).
6. **Export** the manufacturing BOM and HBOM from the resolved BOM.
7. **Validate** all outputs (see [CI Checks](#ci-checks)) and publish them as job artifacts.

The resolver is deterministic: the same design, build quantity, database, company stock and distributor data always produce the same result. It fails if any instance has no candidate.

DNP instances are not resolved.

### Order Helper

The Order Helper runs inside the resolve job. When company stock cannot cover the build, it finds the best way to buy the shortfall from distributors.

1. **Calculate the shortfall** per `PartNumber`: quantity per board × build quantity, minus company stock.
2. **Query distributors** by manufacturer part number for stock, price breaks, minimum order quantity and lead time. Distributor API credentials are stored as CI secrets.
3. **Choose the best offer** for each part: enough stock first, then lowest total cost at the order quantity (taking price breaks and minimum order quantities into account), then shortest lead time.
4. **Consider alternatives.** If another approved part that satisfies the same key fields is cheaper or available while the selected one is not, the resolver uses it instead.
5. **Write the purchase list** as a job artifact.

Buying the shortfall of a part that is partly in stock is preferred over switching to a different part.

If no approved part can be sourced, the job fails. To help fix the source, the Order Helper searches distributor catalogs for parts that match the key fields and footprint and lists them in the job output as candidates for approval. These parts are never used until they are approved and added to the company part database.

The Order Helper never places orders. The purchase list is reviewed and ordered by a person.

#### Purchase list

One row per part to buy:

| Column             | Description                                          |
| ------------------ | ---------------------------------------------------- |
| Part Number        | `PartNumber`                                         |
| Manufacturer       | `Manufacturer`                                       |
| MPN                | `MfrPartNum`                                         |
| Required           | Quantity per board × build quantity                  |
| In Stock           | Company stock                                        |
| Order Quantity     | Quantity to buy, after minimum order and price breaks |
| Distributor        | Selected distributor                                 |
| Distributor PN     | Distributor part number                              |
| Unit Price         | At the order quantity, with currency                 |
| Total Price        | Order quantity × unit price                          |
| Distributor Stock  | Stock at the distributor                             |
| Lead Time          | If the distributor reports one                       |
| Fetched At         | Timestamp of the distributor data                    |

### Resolved BOM

The record of one build. It is kept with the job artifacts and contains:

- The build identifier.
- The design revision (git commit), assembly variant and the state of the part database used.
- The build quantity.
- When company stock and distributor data were fetched.
- The CI job run that produced it and who triggered it.
- One line per `PartNumber`, with its reference designators and quantity.

The manufacturing BOM and HBOM are generated only from the resolved BOM.

### Manufacturing BOM

Excel (`.xlsx`), for the contract manufacturer. One row per line, sorted by `PartNumber`.

| Column        | Source                                    |
| ------------- | ----------------------------------------- |
| Part Number   | `PartNumber`                              |
| Quantity      | Count of instances in the line            |
| Reference     | Reference designators, comma separated    |
| Value         | KiCad `Value`                             |
| Description   | `Description`                             |
| Footprint     | KiCad `Footprint`, empty for off-board items |
| Manufacturer  | `Manufacturer`                            |
| MPN           | `MfrPartNum`                              |
| DNP           | `DNP` if not assembled, otherwise empty   |

DNP instances are listed with their references and footprints so the manufacturer knows the pads are intentionally empty.

### HBOM

An HBOM is the hardware version of an SBOM. It exists for supply-chain transparency and risk management: provenance, part lifecycle, and which parts carry firmware. Because it describes what actually ships, each build has its own HBOM.

Reference: CISA, *Hardware Bill of Materials (HBOM) Framework for Supply Chain Risk Management* (ICT SCRM Task Force, September 2023).

Format: CycloneDX 1.6, JSON, built with [`cyclonedx-python-lib`](https://github.com/CycloneDX/cyclonedx-python-lib). DNP instances are excluded.

Each line becomes one component of type `device`:

| Source                | CycloneDX                                  |
| --------------------- | ------------------------------------------ |
| `PartNumber`          | `bom-ref`                                  |
| `MfrPartNum`          | `name`                                     |
| `Manufacturer`        | `manufacturer` (1.6+)                      |
| `Description`         | `description`                              |
| `Datasheet`           | `externalReferences` of type `documentation` |
| Reference designators | property `screenly:hbom:refdes`            |
| Quantity              | property `screenly:hbom:quantity`          |
| `CountryOfOrigin`     | property `screenly:hbom:countryOfOrigin`   |
| `LifeCycle`           | property `screenly:hbom:lifeCycle`         |
| `LTBDate`             | property `screenly:hbom:ltbDate`           |
| `ContainsFirmware`    | property `screenly:hbom:containsFirmware`  |

Rules:

- HBOM attributes without a native CycloneDX field go into properties under the `screenly:hbom:` namespace.
- Do **not** use `metadata.lifecycles` for part lifecycle. It describes the phase of the BOM itself, not of the parts.
- Every firmware-bearing part (`Fixed` or `Updatable`) has a `bom-ref`, so it can be linked to an SBOM.

## CI Checks

On every design change (pull request), CI checks that the following hold. The same checks are meant to run locally too:

- Every instance on the board has a `Footprint` from the Screenly KiCad Footprint Library, and every off-board instance has none.
- Every instance's reference designator starts with its class's [reference prefix](part-library-standard.md#classes).
- In every assembly variant, every assembled instance has a valid `PartNumber` whose class is defined, has all of the class's required key fields with values, writes every value as described in [Field values](part-library-standard.md#field-values), and uses only listed members for `set` keys. On failure, CI reports each instance and the missing or invalid fields.
- Every assembled instance has at least one candidate part.

In the manually triggered resolve job, before publishing artifacts, CI checks that:

- Every resolved part satisfies the key fields of its instances, and the footprints of instances on the board.
- Exports are intact: the HBOM validates against the CycloneDX 1.6 schema, and the Excel file opens and has the expected columns.
- Exports are in sync with the resolved BOM: same lines, part numbers, quantities, reference designators and field values.

The job fails, and publishes nothing, if any check fails.

## Open Items

- How parts from the [Assembly Part Library](assembly-part-library-standard.md), which are not in KiCad designs, are added to the resolved BOM, manufacturing BOM and HBOM.
- Where the [part attributes](#part-attributes) and the parameters and footprints of each registered part are kept, so the resolver and HBOM can use them.
- Running the design checks locally, ideally as part of KiCad's ERC.
- Moving the part database to PostgreSQL with a proper backend.
- Which distributors the Order Helper queries. Digi-Key and Mouser have official APIs; LCSC does not offer one generally.
- Whether to order extra parts for manufacturing loss (attrition), and how much per class.
- Currency for price comparison across distributors.
- How firmware verification per manufacturer part number is recorded.
- Where resolve job artifacts are stored, how long they are kept, and how builds are named.
- Who may trigger the resolve job, and whether its artifacts need an approval step before they are sent to the manufacturer.
- Confirm `kicad-cli` BOM export options for KiCad 10.0 (the version that saved the current schematic files), including how the assembly variant is selected.
- Final type for `ContainsFirmware`: the enum above, or a boolean (`true`/`false`).
- Optional: backfill `LifeCycle` and `CountryOfOrigin` in the database from the Octopart, Digi-Key or Mouser APIs.
