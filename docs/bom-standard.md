# Bill of Materials (BOM) Standard

How Screenly hardware designs specify components, and how BOMs are produced from them for each manufacturing order.

## Overview

BOMs are produced in two stages:

1. **Design.** The KiCad design states *what each component must satisfy* (`DesignConstraint`), not which stock item to buy.
2. **Order.** Just before a manufacturing order, a manually triggered CI job resolves the design: it picks the best approved parts from the company part database and writes a resolved BOM. All exports are generated from it. When company stock is short, the Order Helper finds the best parts to buy from distributors.

```
KiCad design ──► Resolver ◄── Company part database, company stock
(constraints)       │    ◄──► Order Helper ◄── Distributor APIs
                    ▼               │
              Resolved BOM          └──► Purchase list
              (per build)  ──► Manufacturing BOM (.xlsx)
                           ──► HBOM (CycloneDX)
```

This keeps designs valid as parts go out of stock or obsolete. The design never freezes a list of alternates; it is resolved against the parts available at order time.

## Principles

- **The KiCad design is the source of truth for requirements.** The company part database is the source of truth for parts.
- **Only approved parts are used.** The resolver selects only from the company part database, never directly from distributor catalogs.
- **The footprint is a hard constraint.** A part placed on the board is only a candidate if it fits the footprint placed in the design. All footprints come from the Screenly KiCad Footprint Library (see [Footprints](part-library-standard.md#footprints)).
- **Every build is recorded.** Each order has its own resolved BOM and exports.
- **Resolution runs only in CI, under quality control.** BOMs for manufacturing are produced only by the manually triggered CI job, never locally. Its artifacts are not edited by hand.
- **A wrong or failed BOM means the source is wrong.** If the job cannot produce a correct BOM, the source is fixed and the job is run again: the KiCad design files for requirements, or the part database for part data. There are no manual workarounds.

## Stage 1: Design

### Screenly KiCad Part Library

The Screenly KiCad Part Library is the KiCad symbol library used by all Screenly designs. Its structure and the definition of each class are specified in the [Screenly KiCad Part Library Standard](part-library-standard.md).

### KiCad fields

| Field              | Set on               | Purpose                                                        |
| ------------------ | -------------------- | -------------------------------------------------------------- |
| `Reference`        | Instance             | Reference designator                                           |
| `Value`            | Instance             | Human-readable value on the schematic                          |
| `Footprint`        | Instance             | Hard constraint for part selection                             |
| `Datasheet`        | Library or instance  | Datasheet of the part the design is based on, for reference    |
| `Description`      | Library or instance  | Short description of the symbol, for reference                 |
| `DesignConstraint` | Instance             | Requirements the part must satisfy (see below)                 |
| DNP                | Instance             | Footprint placed but not assembled                             |
| Exclude from BOM   | Instance or library  | Not a physical part (e.g. logos)                               |
| Exclude from board | Instance             | BOM item without a footprint (see [Off-board items](#off-board-items)) |

`DesignConstraint` is design-specific and is never set in the Screenly KiCad Part Library.

`Datasheet` and `Description` are informational. The resolver does not use them, and the exports take these values from the resolved part in the company part database.

### One symbol per BOM item

Every item that is bought for a build has its own symbol, with its own `DesignConstraint`. A symbol never stands for more than one item.

### Off-board items

Some items are part of the build but have no footprint of their own, such as a module plugged into board connectors or a battery on wire leads. They are drawn as separate symbols with KiCad's *Exclude from board* attribute: the symbol appears in the BOM, but not on the PCB.

- The item it attaches to is a separate symbol with a footprint. Usually the off-board item is plugged into a connector on the board. In the reverse case, a module footprint can hold the pads of the connectors it plugs into, and the connectors are the off-board items.
- An off-board item has no footprint, so it is matched by its `DesignConstraint` alone. Its `family` and keys must fully define the fit with the board side.

Examples:

| Item                          | Symbols                                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| Raspberry Pi CM5              | `U1`: CM5 (`MOD`, on board), with one footprint that holds both board-to-board connectors at the exact module spacing. `J1`, `J2`: the two connectors (`CON`, off-board). |
| Battery on wire leads         | `J3`: wire-to-board connector (`CON`, on board). `BT1`: battery (`BAT`, off-board).       |
| Coin cell in a holder         | `J4`: battery holder (`CON`, on board). `BT2`: coin cell (`BAT`, off-board).              |

### Assembly variants

Designs use KiCad assembly variants to describe different builds of the same board. A variant can change which instances are DNP or excluded from the BOM, and can override field values such as `DesignConstraint`. Every BOM is produced for exactly one variant.

### DesignConstraint syntax

```
class <CODE>; <key> <value>; <key> <value>;
```

- Starts with `class`, a code from the [Part Numbering Standard](part-numbering-standard.md). The class defines which keys are allowed and which are required.
- Each term is a key and a value separated by a space, and ends with `;`.
- There are no operators. Each key has a fixed comparison defined by its class (see [Comparisons](part-library-standard.md#comparisons)). For example, `tolerance 10%` always means 10% or better, and `power 0.1W` always means at least 0.1 W.
- A set of allowed values is separated by `|`: `dielectric X7R|X5R`.
- `family` takes a glob pattern on the manufacturer part number (see [Family patterns](part-library-standard.md#family-patterns)).
- Numeric values always include a unit (except resistance, which is written without the Ω symbol, e.g. `10K`), with SI prefixes (`p`, `n`, `u`, `m`, `k`, `M`). `K` is also accepted for kilo. Prefixes are case-sensitive, so `m` (milli) and `M` (mega) are different. Memory and storage sizes use `KB`, `MB`, `GB`. Temperatures use `C` (e.g. `-20C`). Counts, such as mating cycles, are plain numbers (e.g. `5000`).
- The package is not repeated in the constraint. It is enforced from `Footprint`.

Examples:

```
class RES; value 10K; tolerance 10%; power 0.1W;
class CAP; value 100nF; tolerance 10%; voltage 16V; dielectric X7R|X5R;
class MCU; family STM32L0?1C?T?; flash 32KB;
```

### Classes

Each class defines its keys, which keys are required, and how each is compared. The definitions are in the [Screenly KiCad Part Library Standard](part-library-standard.md#class-definitions).

### Firmware-bearing parts

A part with `ContainsFirmware=Updatable` may only be selected if the product firmware has been verified on that exact manufacturer part number.

## Company Part Database

Each approved part has one record:

| Field              | Description                                                                     |
| ------------------ | ------------------------------------------------------------------------------- |
| `PartNumber`       | Screenly part number, see [Part Numbering Standard](part-numbering-standard.md) |
| `Manufacturer`     | Manufacturer name                                                               |
| `MfrPartNum`       | Manufacturer part number                                                        |
| `Description`      | Short description                                                               |
| `Datasheet`        | Datasheet URL                                                                   |
| `Footprints`       | Footprints the part fits, from the Screenly KiCad Footprint Library            |
| `Parameters`       | Values for the class keys (e.g. `value`, `tolerance`, `flash`), see below       |
| `CountryOfOrigin`  | Free text                                                                       |
| `LifeCycle`        | `Active`, `NRND`, `LTB`, `Obsolete`, `Preview`, `Unknown`                       |
| `LTBDate`          | ISO 8601 date, only with `LifeCycle=LTB`                                        |
| `ContainsFirmware` | `None`, `Fixed`, `Updatable`, `Unknown`                                         |

`Parameters` are represented differently in each place:

- **[Screenly KiCad Part Library](#screenly-kicad-part-library):** one field per class key, so each value is easy to read and edit (`value` = `10K`, `tolerance` = `1%`, `power` = `0.1W`).
- **Database:** a single JSON field (PostgreSQL `jsonb`), since each class has a different set of keys. The values are validated against the class definition.

```json
{"value": "10K", "tolerance": "1%", "power": "0.1W"}
```

`ContainsFirmware` values:

- `None`: no firmware.
- `Fixed`: firmware in ROM or OTP, cannot be updated.
- `Updatable`: firmware in flash or EEPROM.
- `Unknown`: not yet determined.

An empty `LifeCycle` or `ContainsFirmware` is treated as `Unknown`. Never default to `None` or `No`.

Company stock levels are tracked per `PartNumber`, including stock held at the contract manufacturer.

Distributor data (prices, stock, distributor part numbers) is not stored. It is fetched by manufacturer part number when the job runs.

## Stage 2: Order

### Resolver

The resolver runs as a manually triggered CI job. The job is started with:

- The design revision (git ref) to resolve.
- The assembly variant to build.
- A build identifier.
- The build quantity (number of boards).

1. **Extract** instances and fields for the selected assembly variant with KiCad's own BOM export (`kicad-cli sch export bom`), so DNP, BOM exclusion and field overrides follow the variant.
2. **Find candidates** for each assembled instance: approved parts in the same class (from the `PartNumber`) that satisfy every constraint term. For instances on the board, the part's `Footprints` must also include the instance footprint.
3. **Select** one part per instance using these rules in order:
   1. Parts with enough company stock for the build quantity.
   2. Parts that can be bought from distributors in enough quantity (see [Order Helper](#order-helper)).
   3. Fewer unique parts across the board. One part that satisfies several constraints is preferred over several parts.
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
4. **Consider alternatives.** If another approved part that satisfies the same constraints is cheaper or available while the selected one is not, the resolver uses it instead.
5. **Write the purchase list** as a job artifact.

Buying the shortfall of a part that is partly in stock is preferred over switching to a different part.

If no approved part can be sourced, the job fails. To help fix the source, the Order Helper searches distributor catalogs for parts that match the constraints and footprint and lists them in the job output as candidates for approval. These parts are never used until they are approved and added to the company part database.

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
- The design revision (git commit), assembly variant and database revision used.
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

On every design change (pull request), CI checks that:

- Every instance on the board has a `Footprint` from the Screenly KiCad Footprint Library, and every off-board instance has none.
- Every instance's reference designator starts with its class's [reference prefix](part-library-standard.md#classes).
- In every assembly variant, every assembled instance has a `DesignConstraint` that parses, uses a known class, includes all of the class's required keys, and uses only listed members for `set` keys. On failure, CI reports each instance and the missing or invalid keys.
- Every constraint has at least one candidate in the company part database.

In the manually triggered resolve job, before publishing artifacts, CI checks that:

- Every resolved part satisfies its instances' constraints, and the footprints of instances on the board.
- Exports are intact: the HBOM validates against the CycloneDX 1.6 schema, and the Excel file opens and has the expected columns.
- Exports are in sync with the resolved BOM: same lines, part numbers, quantities, reference designators and field values.

The job fails, and publishes nothing, if any check fails.

## Open Items

- How parts from the [Assembly Part Library](assembly-part-library-standard.md), which are not in KiCad designs, are added to the resolved BOM, manufacturing BOM and HBOM.
- Company part database: PostgreSQL table schema and hosting.
- Where company stock levels are tracked.
- Which distributors the Order Helper queries. Digi-Key and Mouser have official APIs; LCSC does not offer one generally.
- Whether to order extra parts for manufacturing loss (attrition), and how much per class.
- Currency for price comparison across distributors.
- How firmware verification per manufacturer part number is recorded.
- Where resolve job artifacts are stored, how long they are kept, and how builds are named.
- Who may trigger the resolve job, and whether its artifacts need an approval step before they are sent to the manufacturer.
- Confirm `kicad-cli` BOM export options for KiCad 10.0 (the version that saved the current schematic files), including how the assembly variant is selected.
- Final type for `ContainsFirmware`: the enum above, or a boolean (`true`/`false`).
- Optional: backfill `LifeCycle` and `CountryOfOrigin` in the database from the Octopart, Digi-Key or Mouser APIs.
