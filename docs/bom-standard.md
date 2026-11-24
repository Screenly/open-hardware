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

### Implementation phases

Stage 2 needs company stock to choose from. Until that stock is built up, every part would be missing and the resolver would replace the parts already chosen for the design. So the stages are introduced in two phases:

1. **Now: design-stage manufacturing files.** `create-manufacturing-files.sh --project=DIR --variant=NAME` produces the manufacturing files of one assembly variant. It already resolves the design: for each assembled instance of the variant, it picks an approved part that meets the instance's [class key fields](#class-key-fields), as in [Find candidates](#resolver), and prefers parts sold by the distributors given with `--distributors` (see [Distributor part numbers](#distributor-part-numbers)). Stock is not checked. The BOM and the [HBOM](#hbom) list the picked parts, with the [part attributes](#part-attributes) from the company part database.
2. **Later, once company stock exists: Stage 2.** The [resolver](#resolver) and [Order Helper](#order-helper) are implemented as described below. They check stock for the build quantity, pick other approved parts from the part database when stock is short, and propose new parts from distributors when no approved part is available. From then on, the manufacturing BOM and HBOM of a build come from the resolved BOM.

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
| Exclude from BOM   | Instance or library | Not a physical part (e.g. logos), or a [module fitted after board assembly](#modules-fitted-after-board-assembly) |
| Exclude from board | Instance            | BOM item without a footprint (see [Off-board items](#off-board-items)) |

`Datasheet` and `Description` are informational. The resolver does not use them, and the exports take these values from the resolved part.

### One symbol per BOM item

Every item that is bought for a build has its own symbol, with its own class key fields. A symbol never stands for more than one item.

### Off-board items

Some items are part of the build but have no footprint of their own, such as a battery on wire leads or a coin cell in a holder. They are drawn as separate symbols with KiCad's *Exclude from board* attribute: the symbol appears in the BOM, but not on the PCB.

- The item it attaches to is a separate symbol with a footprint, usually a connector on the board that the off-board item plugs into.
- An off-board item has no footprint, so it is matched by its class key fields alone. Its `family` and keys must fully define the fit with the board side.

Examples:

| Item                          | Symbols                                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| Battery on wire leads         | `J3`: wire-to-board connector (`CON`, on board). `BT1`: battery (`BAT`, off-board).       |
| Coin cell in a holder         | `J4`: battery holder (`CON`, on board). `BT2`: coin cell (`BAT`, off-board).              |

### Modules fitted after board assembly

A module that plugs into board connectors and is fitted after the board is assembled, such as the Raspberry Pi CM5, is not part of the board assembly:

- The module symbol (`MOD`) has a footprint that holds the pads of all its connectors at the exact module spacing, so it carries the nets. Its instance is set to *Exclude from BOM*.
- Each board connector is a separate `CON` symbol on the board, with a footprint that has no copper: only the courtyard, fabrication outline and 3D model. It is placed at the connector centre of the module footprint, with the same rotation, so the connectors appear in the BOM and the position files.
- The module footprint has no courtyard of its own over the connectors, so the connector footprints can sit on top of it.

| Item                          | Symbols                                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| Raspberry Pi CM5              | `U1`: CM5 (`MOD`, excluded from BOM), with one footprint that holds the pads of both board-to-board connectors. `J1`, `J2`: the two connectors (`CON`, on board, footprints without copper). |

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
- **Part attributes.** The [part attributes](#part-attributes) the HBOM needs, per part number.
- **Distributor part numbers.** The [distributors](#distributor-part-numbers) each part is bought from.

Part parameters are not stored in the database. They are the class key fields of the symbols in the [Screenly KiCad Part Library](#screenly-kicad-part-library).

### Part attributes

The HBOM needs these attributes for every part that ships. They are kept in the company part database, in each part's registry entry, and indexed by the Screenly part number. They are not KiCad symbol fields, because they describe a purchased part, not a design requirement. Set them with `tools/partsdb.py attributes`:

| Attribute          | Values                                                    |
| ------------------ | --------------------------------------------------------- |
| `CountryOfOrigin`  | Free text                                                 |
| `LifeCycle`        | `Active`, `NRND`, `LTB`, `Obsolete`, `Preview`, `Unknown` |
| `LTBDate`          | ISO 8601 date, only with `LifeCycle=LTB`                  |
| `ContainsFirmware` | `None`, `Fixed`, `Updatable`, `Unknown`                   |
| `CPE`              | CPE 2.3 name of the part (`cpe:2.3:h:...`), for firmware-bearing parts |
| `FirmwareCPE`      | CPE 2.3 name of its firmware (`cpe:2.3:o:...`), in NVD's naming |

In the registry they are the fields `country_of_origin`, `lifecycle`, `ltb_date`, `contains_firmware`, `cpe` and `firmware_cpe`, plus `attributes_validated`, the date they were last confirmed against the manufacturer's or a distributor's data. A part without `country_of_origin` has an unknown country of origin. Record a country only when the part is made in one known country; otherwise, the country comes from the shipment and is set per build.

`ContainsFirmware` values:

- `None`: no firmware.
- `Fixed`: firmware in ROM or OTP, cannot be updated.
- `Updatable`: firmware in flash or EEPROM.
- `Unknown`: not yet determined.

An empty `LifeCycle` or `ContainsFirmware` is treated as `Unknown`. Never default to `None` or `No`.

### Distributor part numbers

The distributors are kept in a table in the company part database. Each has a single-word name, such as `LCSC` or `DigiKey`, and its website. A distributor is added to the table before any part refers to it, and can only be removed when no part refers to it:

```
tools/partsdb.py distributors list
tools/partsdb.py distributors add <NAME> --website <https URL>
tools/partsdb.py distributors update <NAME> --website <https URL>
tools/partsdb.py distributors remove <NAME>
```

Each registry entry can list the distributors the part is bought from, in the field `distributor_info`, set with `tools/partsdb.py distributor`. It is an ordered list, the part's preferred distributor first:

| Key | Value |
| --- | ----- |
| `distributor` | A name from the distributor table |
| `part_number` | The distributor's own part number, e.g. `C307331` (LCSC) or `11-CR2032-ND` (DigiKey) |
| `link` | Optional product page URL |
| `validated` | ISO 8601 date the part number was last confirmed to point to this exact part at the distributor |

`validated` is set by the tool whenever an entry is written or re-confirmed. It is not touched by `tools/partsdb.py validate`, which only checks the database format.

`create-manufacturing-files.sh` picks the part of each assembled instance from its candidates (approved parts of the instance's class that fit its footprint and meet its class key fields) and adds the columns `Distributor`, `Distributor part number` and `Link` to the assembly BOM. It takes an optional, comma-separated distributor preference list, e.g. `--distributors=LCSC,DigiKey`. The part is selected using these rules in order:

1. The part sold by the earliest distributor in the list. A part sold by none of them ranks after all others.
2. The design's own part (the `PartNumber` of the instance).
3. The part that is a candidate for the most instances, for fewer unique parts.
4. The lowest `PartNumber`.

So the design's own part is kept unless another candidate is sold by a distributor earlier in the list. For example, the TPM's `family` is `SLB9672?U20FW1624XTMA1`: with `--distributors=LCSC,DigiKey` the script picks the SLB9672AU, which LCSC sells; with `--distributors=DigiKey,LCSC`, the design's SLB9672XU. The script lists every substitution.

- Each BOM line gets the first distributor in the list that the picked part has.
- If the part has none of them, the part's own preferred distributor is used, and the script reports it as a fallback. With `--strict`, the script stops instead.
- Without `--distributors`, each part gets its own preferred distributor, and the design's own parts are kept.
- The distributor list is part of the BOM file name, in lowercase: `--distributors=LCSC,DigiKey` writes `<ESP_PN>-bom-lcsc-digikey.csv`; without the list, the file is `<ESP_PN>-bom.csv`. The assembly README names the list too.
- A part with no distributor gets empty columns and is reported. With `--strict`, the script stops.
- The script stops if a required key field of an instance is empty, or if the instance's own part doesn't meet its key fields.

Prices and stock are not stored: they change within weeks and are fetched when needed. Purchase prices will come from the purchase records of [Stage 2](#implementation-phases).

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

Until [Stage 2](#implementation-phases) is in place, the HBOM is a design HBOM of an assembly variant, made by `create-manufacturing-files.sh` from the design BOM. Its metadata component is the assembly (`ESP_PN_<variant>`), with the variant, the bare PCB (`PCB_PN`) and the design commit as properties. The bare PCB is listed as a component with quantity 1.

Each line becomes one component of type `device`:

| Source                | CycloneDX                                  |
| --------------------- | ------------------------------------------ |
| `PartNumber`          | `bom-ref`                                  |
| `MfrPartNum`          | `name`, and `version`: a bought part has no version of its own, so its manufacturer part number identifies its model |
| `Manufacturer`        | `manufacturer` (1.6+)                      |
| `Description`         | `description`                              |
| `Datasheet`           | `externalReferences` of type `documentation` |
| Reference designators | property `screenly:hbom:refdes`            |
| Quantity              | property `screenly:hbom:quantity`          |
| `CountryOfOrigin`     | property `screenly:hbom:countryOfOrigin`   |
| `LifeCycle`           | property `screenly:hbom:lifeCycle`         |
| `LTBDate`             | property `screenly:hbom:ltbDate`           |
| `ContainsFirmware`    | property `screenly:hbom:containsFirmware`  |
| `CPE`                 | `cpe`, a hardware CPE (`cpe:2.3:h:...`)     |
| `FirmwareCPE`         | property `screenly:hbom:firmwareCpe`       |

Rules:

- HBOM attributes without a native CycloneDX field go into properties under the `screenly:hbom:` namespace.
- Do **not** use `metadata.lifecycles` for part lifecycle. It describes the phase of the BOM itself, not of the parts.
- Every firmware-bearing part (`Fixed` or `Updatable`) has a `bom-ref`, so it can be linked to an SBOM.
- Every device has a `name`, a `manufacturer` and a `version`, as HBOM checkers such as the [sbomify HBOM Validator](https://sbomify.com/tools/hbom-checker/) require. The assembly and the bare PCB use the design revision (the board title block) as `version`.
- Firmware-bearing parts carry a `CPE`, so they can be matched against vulnerability data, and a `FirmwareCPE` when the firmware is listed separately, as NVD does for TPM firmware. Other parts don't need an identifier; the HBOM checker's warnings for their missing CPE are expected.

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
- Where the parameters and footprints of each registered part are kept, so the resolver can use them. (The [part attributes](#part-attributes) are in the part database.)
- Implementing Stage 2 (resolver and Order Helper) once company stock exists, see [Implementation phases](#implementation-phases).
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
