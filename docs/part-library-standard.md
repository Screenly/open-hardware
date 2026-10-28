# Screenly KiCad Part Library Standard

How the Screenly KiCad Part Library is organized, and the definition of each part class.

## Library

The Screenly KiCad Part Library is a KiCad symbol library, [`library/Screenly.kicad_sym`](../library/Screenly.kicad_sym), used by all Screenly designs.

Every symbol in the library is based on one specific part and carries its identity:

| Field          | Content                                                                          |
| -------------- | -------------------------------------------------------------------------------- |
| `PartNumber`   | Screenly part number, see [Part Numbering Standard](part-numbering-standard.md) |
| `Manufacturer` | Manufacturer name                                                                |
| `MfrPartNum`   | Manufacturer part number                                                         |

The part must be registered in the company part database with the same manufacturer and manufacturer part number.

Symbols that are not parts, such as test points, fiducials and logos, are the only exception. They have no `PartNumber`, `Manufacturer`, `MfrPartNum` or class keys, are excluded from the BOM and position files (see [KiCad fields](bom-standard.md#kicad-fields)), and their names have no manufacturer part number, e.g. `Test Point Pad 2.0mm`. Those that are on the board still use a Screenly footprint.

### Symbol names

Symbol names say what the part is, so designers can find it in the symbol chooser:

```
<Kind> <main values> <package> (<manufacturer part number>)
```

- `<Kind>` is a plain word for the part, e.g. `Resistor`, `Capacitor`, `Module`.
- `<main values>` are the few values a designer picks the part by, not every key. The full detail is in the fields.
- `<package>` is the package size, when the part has a standard one (e.g. `0402`).
- The manufacturer part number in brackets keeps names unique.

| Class | Name pattern                                                   | Example                                  |
| ----- | -------------------------------------------------------------- | ---------------------------------------- |
| `CAP` | `Capacitor <value> <voltage> <dielectric or technology> <package> (<MPN>)` | `Capacitor 100nF 50V X7R 0402 (CL05B104KB54PNC)`, `Capacitor 150uF 35V Polymer Radial 6.3x8mm (PA35V150M6X8)` |
| `CON` | `<Interface name> <size or positions> <mounting> (<MPN>)`     | `Battery Holder CR2032 THT (BS-02-A1AJ010)` |
| `RES` | `Resistor <value> <tolerance> <package> (<MPN>)`               | `Resistor 470R 5% 0402 (0402WGJ0471TCE)` |
| `DIO` | `<Type> Diode <main values> <package> (<MPN>)`                | `TVS Diode Bidirectional 18V 600W SMB (SMBJ18CA)`, `Zener Diode 12V 370mW SOD-123 (BZT52C12-7-F)` |
| `FBD` | `Ferrite Bead <impedance> <current> <package> (<MPN>)`         | `Ferrite Bead 50R 12A 1206 (BLM31SN500SZ1L)` |
| `FET` | `<N/P>-MOSFET <vds> <id> <rds_on> <package> (<MPN>)`          | `P-MOSFET 40V 40A 15mOhm TO-252 (AOD4185)` |
| `IND` | `Inductor <value> <saturation current> <body size> (<MPN>)`    | `Inductor 4.7uH 15A 10x11.5mm (AAPS1050M4R7A)` |
| `ITC` | `<Function> <main values> <package> (<MPN>)`                  | `USB SS Mux IC Type-C Port Controller 10Gbps WQFN-30 (HD3SS3220IRNHR)`, `Audio DAC Stereo 112dB I2S TSSOP-20 (PCM5102APWR)` |
| `LED` | `LED <color> <dominant wavelength or color temperature> <package> <mounting if not top view> (<MPN>)` | `LED Red 631nm 0603 Side View (LTST-S270KRKT)` |
| `MOD` | `Module <model> <main options> (<MPN>)`                        | `Module CM5 4GB 64GB WiFi (CM5104064)`   |
| `PWR` | `<Topology> Converter <input range> <output current> <package> (<MPN>)`, `Power Switch <input range> <output current> <package> (<MPN>)` | `Buck Converter 4-36V 5A WSON-12 (LMR51450SDRRR)`, `Power Switch 3-5.5V 2.1A SOT-23-6 (AP22653W6-7)` |
| `STO` | `EEPROM <capacity> <bus> <package> (<MPN>)`                    | `EEPROM 8KB I2C SOIC-8 (M24C64-RMN6TP)` |
| `SWC` | `<Type> Switch <size> <force> <actuator height> <mounting> (<MPN>)` | `Tactile Switch 6x6mm 1.6N 3.15mm Right Angle THT (PTS645VM31-2 LFS)` |

The pattern of other classes is defined when their first part is added.

The `Value` field shows the main value on the schematic in the usual notation (e.g. `470R`), while the `value` key keeps the [field value](#field-values) format (`470`). The class of the symbol is the class code in its `PartNumber`.

When the symbol is placed, these fields name the part the design is based on. The resolver can still choose another approved part that satisfies the instance's class key fields.

Related standards:

- [Part Numbering Standard](part-numbering-standard.md): class codes and part numbers.
- [BOM Standard](bom-standard.md): how designs use class key fields, and how BOMs are resolved.

## Footprints

The Screenly KiCad Footprint Library is a KiCad footprint library, [`library/Screenly.pretty`](../library/Screenly.pretty).

Every part placed on the board must be linked to a footprint in the Screenly KiCad Footprint Library:

- Every symbol in the Screenly KiCad Part Library for a part on the board has its `Footprint` field set to a Screenly footprint.
- Off-board items, such as plug-in modules and batteries on wire leads, have no footprint. See [Off-board items](bom-standard.md#off-board-items).
- Footprints from KiCad's built-in libraries or third-party libraries are not used directly. If one is needed, it is copied into the Screenly KiCad Footprint Library first.

3D models are STEP files in [`library/3d-models`](../library/3d-models). Footprints reference them as `${SCREENLY_LIB}/3d-models/<file>`, where `SCREENLY_LIB` is a path variable that points to the `library` directory.

## Classes

Every class is a code from the [Part Numbering Standard](part-numbering-standard.md). A class defines a reference prefix and a set of keys.

The reference prefix is the letter or letters of the reference designator (`R` in `R1`). Prefixes follow common industry usage (IEEE 315 and KiCad conventions) and are not unique: several classes can share one, such as `U`.

Each key has:

| Attribute  | Description                                                                  |
| ---------- | ---------------------------------------------------------------------------- |
| Unit       | Unit of the value. Values are written as described in [Field values](#field-values). |
| Required   | Whether every instance of the class must keep the field, with a value.       |
| Comparison | How a part's value is checked against the field value.                      |

Each key is an individual symbol field with the same name as the key. Every symbol in the Screenly KiCad Part Library carries all keys of its class, filled in from the datasheet of the part the symbol is based on. When the symbol is placed in a design, the fields become the requirements for that instance (see [Class key fields](bom-standard.md#class-key-fields)).

This document is the specification of each class. The design checks and the resolver implement it.

A class that has no definition below cannot be used in designs yet. Classes for parts that are not designed in KiCad are in the [Assembly Part Library Standard](assembly-part-library-standard.md).

### Rules

- **Required keys have no defaults.** If an instance is missing a required key field, or the field is empty, the design check fails and reports the instance and the missing keys.
- **Some keys are required per type.** A class can make keys required only for certain members of a `set` key (for example, `vz` for Zener diodes). These are listed in the class definition and enforced like other required keys.
- **Optional keys can be deleted.** A designer deletes an optional key field on an instance when its value is not critical. A deleted or empty optional field is not checked, so any part matches it.
- **References use the class prefix.** Every instance's reference designator starts with its class's reference prefix. A mismatch fails the design check.
- **Sets have defined members.** Every key with a `set` comparison lists its allowed members in the class definition. A value that is not a listed member fails the design check.

### Comparisons

| Comparison | A part matches when its value is…                  | Typical keys                |
| ---------- | -------------------------------------------------- | --------------------------- |
| `exact`    | equal to the field value                           | `value`                     |
| `max`      | less than or equal to the field value              | `tolerance`                 |
| `min`      | greater than or equal to the field value           | `power`, `voltage`, `flash` |
| `set`      | one of the listed values                           | `dielectric`                |
| `pattern`  | matched by the glob pattern                        | `family`                    |
| `range`    | a rated range that includes the field value        | `vdd`                       |
| `all`      | a set on the part that includes every listed value | `bands`                     |

### Family patterns

The `pattern` comparison uses a glob pattern matched against the manufacturer part number:

| Pattern | Matches                          |
| ------- | -------------------------------- |
| `?`     | Any single character             |
| `[68]`  | One character from the set       |
| `*`     | Any sequence, including empty    |

Rule: **every part number the pattern matches must be a drop-in replacement** (pinout, package, footprint and function). If any match is not, tighten the pattern. Other keys then filter within the family.

To allow only one specific part, use its full part number with no wildcards.

### Field values

- Numeric values always include a unit, with SI prefixes (`p`, `n`, `u`, `m`, `k`, `M`): `10pF`, `4.7uF`, `0.1W`, `16V`, `10%`. `K` is also accepted for kilo.
- Prefixes are case-sensitive, so `m` (milli) and `M` (mega) are different.
- Resistance is written without the Ω symbol: `10K`, `4.7K`, `10m` (10 mΩ).
- Memory and storage sizes use `KB`, `MB`, `GB`, `TB`.
- Temperatures use `C`: `-20C`, `85C`.
- Counts, such as mating cycles, are plain numbers: `5000`.
- A set of values is separated by `|`: `X7R|X5R`.
- `family` takes a glob pattern, see [Family patterns](#family-patterns).

## Class Definitions

Classes are listed in alphabetical order.

### `ANT`: Antennas

Antennas for wireless modules and radios: chip antennas on the board, and flexible (FPC), rigid PCB and external antennas connected by cable.

Reference prefix: `AE`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `type`      | –    | Yes      | `set`      |
| `family`    | –    | Yes      | `pattern`  |
| `bands`     | –    | Yes      | `all`      |
| `connector` | –    | Yes      | `set`      |
| `gain`      | dBi  | No       | `min`      |
| `vswr`      | –    | No       | `max`      |
| `cable`     | mm   | No       | `exact`    |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `type` is the antenna type (members below).
- `family` defines drop-in compatibility. The matching network, the enclosure and radio certification are designed for one antenna, so the pattern must be narrow and `family *` is never used.
- `bands` is one or more frequency bands, separated by `|` (members below). A part matches when it covers every listed band.
- `connector` is the cable connector (members below). Chip antennas use `none`.
- `gain` is the minimum peak gain, e.g. `2dBi`.
- `vswr` is the maximum voltage standing wave ratio in the listed bands, written as a plain number (e.g. `2` for 2:1).
- `cable` is the cable length, e.g. `100mm`. It must match exactly, because the cable is routed in the enclosure.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.
- Antennas connected by cable are [off-board items](bom-standard.md#off-board-items) with no footprint. The board connector is a separate `CON` symbol with `interface rf_coaxial`. Only chip antennas have a footprint.

`type` members:

| Member     | Description                                                   |
| ---------- | ------------------------------------------------------------- |
| `chip`     | Ceramic chip antenna soldered to the board                    |
| `fpc`      | Flexible adhesive antenna with cable                          |
| `pcb`      | Rigid PCB antenna with cable                                  |
| `patch`    | Ceramic patch antenna, e.g. for GNSS                          |
| `external` | External antenna outside the enclosure, e.g. a whip or dipole |

`bands` members:

| Member     | Description                                |
| ---------- | ------------------------------------------ |
| `wifi_2g4` | 2.4 GHz Wi-Fi and Bluetooth, 2400–2500 MHz |
| `wifi_5g`  | 5 GHz Wi-Fi, 5150–5850 MHz                 |
| `wifi_6g`  | 6 GHz Wi-Fi, 5925–7125 MHz                 |
| `lte`      | Cellular LTE bands, 698–2690 MHz           |
| `gnss`     | GNSS L1, 1559–1610 MHz                     |
| `sub_ghz`  | Sub-GHz ISM, e.g. 868 MHz and 915 MHz      |
| `uwb`      | Ultra-wideband, 6–8.5 GHz                  |

`connector` members:

| Member   | Description                                |
| -------- | ------------------------------------------ |
| `none`   | No cable connector, soldered to the board  |
| `ufl`    | U.FL (I-PEX MHF I) micro coaxial connector |
| `mhf4`   | I-PEX MHF 4 micro coaxial connector        |
| `sma`    | SMA connector                              |
| `rp_sma` | Reverse-polarity SMA connector             |

Examples:

```
type       chip
family     2450AT18A100*
bands      wifi_2g4
connector  none
```

```
type       fpc
family     1461530100*
bands      wifi_2g4|wifi_5g
connector  ufl
cable      100mm
```

### `BAT`: Batteries

Primary and rechargeable batteries: coin cells (e.g. for RTC backup), cylindrical cells and battery packs.

Reference prefix: `BT`

| Key           | Unit | Required | Comparison |
| ------------- | ---- | -------- | ---------- |
| `chemistry`   | –    | Yes      | `set`      |
| `family`      | –    | Yes      | `pattern`  |
| `size`        | –    | Yes      | `set`      |
| `voltage`     | V    | Yes      | `exact`    |
| `capacity`    | Ah   | Yes      | `min`      |
| `current`     | A    | No       | `min`      |
| `protection`  | –    | No       | `exact`    |
| `un38_3`      | –    | No       | `exact`    |
| `temp_min`    | °C   | No       | `max`      |
| `temp_max`    | °C   | No       | `min`      |

- `chemistry` is the cell chemistry (members below). It also decides whether the battery is rechargeable.
- `family` defines drop-in compatibility. Write `family *` only when `chemistry`, `size` and the other keys fully define compatibility, such as standard coin cells. Battery packs have no standard size or connector, so their pattern must be narrow.
- `size` is the standard cell size (members below).
- A battery on wire leads or in a holder is an [off-board item](bom-standard.md#off-board-items) with no footprint. The board connector or holder is a separate `CON` symbol. Only batteries soldered to the board have a footprint.
- `voltage` is the nominal voltage, e.g. `3V`, `3.7V`.
- `capacity` is the rated capacity, e.g. `220mAh`.
- `current` is the rated continuous discharge current, e.g. `1A`.
- `protection` is `yes` when a built-in protection circuit (overcharge, overdischarge, short circuit) is required. `yes` is its only value; leave it out otherwise.
- `un38_3` is `yes` when UN 38.3 transport test certification is required, which is needed to ship lithium batteries. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`chemistry` members:

| Member         | Rechargeable | Description                                              |
| -------------- | ------------ | -------------------------------------------------------- |
| `li_mno2`      | No           | Lithium manganese dioxide, e.g. CR coin cells, 3 V       |
| `li_socl2`     | No           | Lithium thionyl chloride, long life, 3.6 V               |
| `alkaline`     | No           | Alkaline, 1.5 V                                          |
| `silver_oxide` | No           | Silver oxide, e.g. SR button cells, 1.55 V               |
| `mn_li`        | Yes          | Manganese lithium, e.g. ML coin cells for RTC backup, 3 V |
| `li_ion`       | Yes          | Lithium-ion, cylindrical or prismatic, 3.6–3.7 V         |
| `li_polymer`   | Yes          | Lithium polymer, pouch cells and packs, 3.7 V            |
| `lifepo4`      | Yes          | Lithium iron phosphate, 3.2 V                            |
| `nimh`         | Yes          | Nickel-metal hydride, 1.2 V                              |

`size` members:

| Member   | Description                                     |
| -------- | ----------------------------------------------- |
| `cr1220` | Coin cell, 12.5 mm × 2.0 mm                     |
| `cr2016` | Coin cell, 20 mm × 1.6 mm                       |
| `cr2025` | Coin cell, 20 mm × 2.5 mm                       |
| `cr2032` | Coin cell, 20 mm × 3.2 mm                       |
| `ml1220` | Rechargeable coin cell, 12.5 mm × 2.0 mm        |
| `ml2020` | Rechargeable coin cell, 20 mm × 2.0 mm          |
| `aaa`    | Cylindrical, 10.5 mm × 44.5 mm                  |
| `aa`     | Cylindrical, 14.5 mm × 50.5 mm                  |
| `18650`  | Cylindrical, 18 mm × 65 mm                      |
| `pack`   | Non-standard pack, defined by `family`          |

Examples:

```
chemistry  li_mno2
family     *
size       cr2032
voltage    3V
capacity   220mAh
```

```
chemistry  mn_li
family     ML2020*
size       ml2020
voltage    3V
capacity   45mAh
```

### `BJT`: Bipolar Junction Transistors

Discrete bipolar junction transistors: single, dual, complementary and pre-biased (digital) transistors.

Reference prefix: `Q`

| Key        | Unit | Required | Comparison |
| ---------- | ---- | -------- | ---------- |
| `type`     | –    | Yes      | `set`      |
| `family`   | –    | Yes      | `pattern`  |
| `vce`      | V    | Yes      | `min`      |
| `ic`       | A    | Yes      | `min`      |
| `hfe`      | –    | No       | `min`      |
| `power`    | W    | No       | `min`      |
| `aec_q101` | –    | No       | `exact`    |
| `temp_min` | °C   | No       | `max`      |
| `temp_max` | °C   | No       | `min`      |

- `type` is the transistor type (members below).
- `family` defines drop-in compatibility. Transistor pinouts are not standard, even within one package such as SOT-23, so the pattern must fix the pinout. Industry-standard part numbers made by several manufacturers with the same pinout (e.g. `MMBT3904`) make good cross-manufacturer patterns. For pre-biased transistors, the pattern also fixes the built-in resistor values.
- `vce` is the rated collector-emitter voltage, e.g. `40V`.
- `ic` is the rated continuous collector current, e.g. `200mA`.
- `hfe` is the minimum DC current gain, written as a plain number (e.g. `100`).
- `power` is the rated power dissipation, e.g. `0.35W`.
- `aec_q101` is `yes` when automotive qualification (AEC-Q101) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

For dual and complementary types, the values apply to every transistor in the package.

`type` members:

| Member          | Description                                               |
| --------------- | --------------------------------------------------------- |
| `npn`           | NPN, single or dual                                       |
| `pnp`           | PNP, single or dual                                       |
| `npn_pnp`       | Complementary pair, one NPN and one PNP                   |
| `npn_prebiased` | NPN with built-in bias resistors (digital transistor)     |
| `pnp_prebiased` | PNP with built-in bias resistors (digital transistor)     |

Example:

```
type    npn
family  MMBT3904*
vce     40V
ic      200mA
```

### `BUZ`: Buzzers

Magnetic and piezo buzzers and sounders for audible signals.

Reference prefix: `BZ`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `type`      | –    | Yes      | `set`      |
| `drive`     | –    | Yes      | `set`      |
| `family`    | –    | Yes      | `pattern`  |
| `voltage`   | V    | Yes      | `range`    |
| `frequency` | Hz   | No       | `exact`    |
| `spl`       | dB   | No       | `min`      |
| `current`   | A    | No       | `max`      |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `type` is the transducer type (members below).
- `drive` is `active` or `passive` (members below).
- `family` defines drop-in compatibility. Write `family *` only when `type`, `drive`, the footprint and the other keys fully define compatibility. Buzzers sound through the enclosure, so fix the family when the sound must stay the same.
- `voltage` is the drive voltage of the design, e.g. `5V`. A part matches when its rated voltage range includes it.
- `frequency` is the resonant frequency, e.g. `2.7kHz`. For `passive` buzzers, the design drives the buzzer at this frequency.
- `spl` is the minimum sound pressure level at 10 cm, e.g. `85dB`.
- `current` is the maximum current at the drive voltage, e.g. `30mA`.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`type` members:

| Member     | Description                        |
| ---------- | ---------------------------------- |
| `magnetic` | Electromagnetic buzzer             |
| `piezo`    | Piezoelectric buzzer or transducer |

`drive` members:

| Member    | Description                                            |
| --------- | ------------------------------------------------------ |
| `active`  | Built-in oscillator, sounds when DC voltage is applied |
| `passive` | No oscillator, driven with an AC or PWM signal         |

Example:

```
type       magnetic
drive      passive
family     *
voltage    3.3V
frequency  2.7kHz
spl        80dB
```

### `CAB`: Cables and Cable Assemblies

Cables that ship with or are built into the product: flat flexible cables, wire harnesses and standard interface cables.

Reference prefix: `W`

| Key          | Unit | Required | Comparison |
| ------------ | ---- | -------- | ---------- |
| `type`       | –    | Yes      | `set`      |
| `family`     | –    | Yes      | `pattern`  |
| `length`     | mm   | Yes      | `exact`    |
| `conductors` | –    | No       | `exact`    |
| `pitch`      | mm   | No       | `exact`    |
| `contacts`   | –    | No       | `set`      |
| `shielded`   | –    | No       | `exact`    |

- `type` is the cable type (members below).
- `family` defines drop-in compatibility, including the connectors on both ends. Cables must mate with the connectors on the board, so the pattern must be narrow for harnesses and flat cables. Write `family *` only for standard interface cables where `type` and the other keys fully define compatibility.
- `length` is the cable length, e.g. `150mm`. It must match exactly, because the cable is routed in the enclosure.
- `conductors` is the number of conductors, written as a plain number (e.g. `30`).
- `pitch` is the conductor pitch of a flat cable, e.g. `0.5mm`.
- `contacts` is the contact side of a flat cable (members below).
- `shielded` is `yes` when a shielded cable is required. `yes` is its only value; leave it out otherwise.
- A cable is an [off-board item](bom-standard.md#off-board-items) with no footprint. The connectors it plugs into are separate `CON` symbols.

`type` members:

| Member         | Description                                 |
| -------------- | ------------------------------------------- |
| `ffc`          | Flat flexible cable                         |
| `fpc`          | Flexible printed circuit used as a cable    |
| `wire_harness` | Custom wire harness with crimped connectors |
| `usb`          | Standard USB cable                          |
| `hdmi`         | Standard HDMI cable                         |
| `ethernet`     | Ethernet patch cable                        |
| `coaxial`      | RF coaxial cable assembly                   |
| `power`        | Power cable, e.g. DC or mains cord          |

`contacts` members:

| Member          | Description                                         |
| --------------- | --------------------------------------------------- |
| `same_side`     | Contacts on the same side at both ends (type A)     |
| `opposite_side` | Contacts on opposite sides at the two ends (type B) |

Example:

```
type        ffc
family      0151660?00*
length      100mm
conductors  22
pitch       0.5mm
contacts    opposite_side
```

### `CAP`: Capacitors

Discrete capacitors: ceramic (MLCC), aluminum electrolytic, polymer, tantalum and film.

Reference prefix: `C`

| Key          | Unit | Required | Comparison |
| ------------ | ---- | -------- | ---------- |
| `value`      | F    | Yes      | `exact`    |
| `tolerance`  | %    | Yes      | `max`      |
| `voltage`    | V    | Yes      | `min`      |
| `dielectric` | –    | No       | `set`      |
| `technology` | –    | No       | `set`      |
| `esr`        | Ω    | No       | `max`      |
| `ripple`     | A    | No       | `min`      |
| `aec_q200`   | –    | No       | `exact`    |
| `temp_min`   | °C   | No       | `max`      |
| `temp_max`   | °C   | No       | `min`      |

- `value` is the nominal capacitance, written with `F` and an SI prefix: `10pF`, `100nF`, `4.7uF`. Ceramic capacitors lose capacitance under DC bias; account for it with a higher `voltage` or a larger footprint.
- `voltage` is the rated voltage.
- `dielectric` is one or more ceramic dielectric codes (members below). It only applies to ceramic capacitors; other technologies are not checked against it.
- `technology` is one or more capacitor technologies (members below).
- `esr` is the maximum equivalent series resistance at 100 kHz and 20–25 °C, written without the Ω symbol: `30m` (30 mΩ), `1.5`. Take the datasheet's maximum where it gives one, as for electrolytic and polymer capacitors. For ceramic capacitors, which usually have only a typical curve, read the manufacturer's ESR curve at 100 kHz and round up. Fill it in on every library symbol, because power circuits and filters depend on it.
- `ripple` is the rated ripple current at 100 kHz, e.g. `1.2A`. For ceramic capacitors, it is the current that heats the part by 20 °C, read from the manufacturer's curve and rounded down. Leave it out if the manufacturer gives no value at 100 kHz.
- `aec_q200` is `yes` when automotive qualification (AEC-Q200) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`dielectric` members:

| Member | Temperature range | Capacitance change over range |
| ------ | ----------------- | ----------------------------- |
| `C0G`  | −55 to 125 °C     | ±30 ppm/°C (stable, Class 1)  |
| `X8R`  | −55 to 150 °C     | ±15%                          |
| `X7R`  | −55 to 125 °C     | ±15%                          |
| `X7S`  | −55 to 125 °C     | ±22%                          |
| `X6S`  | −55 to 105 °C     | ±22%                          |
| `X5R`  | −55 to 85 °C      | ±15%                          |
| `Y5V`  | −30 to 85 °C      | +22% / −82%                   |
| `Z5U`  | 10 to 85 °C       | +22% / −56%                   |

`technology` members:

| Member                  | Description                                     |
| ----------------------- | ----------------------------------------------- |
| `ceramic`               | Multilayer ceramic (MLCC)                       |
| `aluminum_electrolytic` | Aluminum electrolytic, liquid electrolyte       |
| `aluminum_polymer`      | Aluminum with conductive polymer electrolyte    |
| `tantalum`              | Tantalum with manganese dioxide cathode         |
| `tantalum_polymer`      | Tantalum with conductive polymer cathode        |
| `film`                  | Plastic film                                    |

Examples:

```
value       100nF
tolerance   10%
voltage     16V
dielectric  X7R|X5R
```

```
value       10uF
tolerance   10%
voltage     50V
dielectric  X7R
esr         10m
ripple      2A
```

```
value       100uF
tolerance   20%
voltage     25V
technology  aluminum_polymer
esr         30m
```

### `CMC`: Common Mode Chokes

Common mode chokes for filtering data lines (e.g. USB, HDMI, Ethernet) and power lines.

Reference prefix: `L`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `family`    | –    | Yes      | `pattern`  |
| `impedance` | Ω    | Yes      | `exact`    |
| `current`   | A    | Yes      | `min`      |
| `dcr`       | Ω    | No       | `max`      |
| `voltage`   | V    | No       | `min`      |
| `cutoff`    | Hz   | No       | `min`      |
| `aec_q200`  | –    | No       | `exact`    |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `family` defines drop-in compatibility. Common mode chokes have several windings and no standard pinout, so the pattern must fix the pinout.
- `impedance` is the nominal common mode impedance at 100 MHz, written without the Ω symbol: `90`, `2.2K`.
- `current` is the rated current per line, e.g. `0.4A`.
- `dcr` is the maximum DC resistance per line, written without the Ω symbol: `300m` (300 mΩ).
- `voltage` is the rated voltage, e.g. `50V`.
- `cutoff` is the minimum differential mode cutoff frequency, e.g. `6GHz`. Use it for high-speed data lines, so the data signal passes undistorted.
- `aec_q200` is `yes` when automotive qualification (AEC-Q200) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

Example:

```
family     DLW21SN900HQ2*
impedance  90
current    0.33A
cutoff     3GHz
```

### `CON`: Connectors

Board-mounted connectors: board-to-board, wire-to-board, FFC/FPC, pin headers and sockets, and standard interface connectors such as USB, HDMI and RJ45.

Reference prefix: `J`

| Key            | Unit   | Required | Comparison |
| -------------- | ------ | -------- | ---------- |
| `interface`    | –      | Yes      | `set`      |
| `family`       | –      | Yes      | `pattern`  |
| `current`      | A      | No       | `min`      |
| `voltage`      | V      | No       | `min`      |
| `durability`   | cycles | No       | `min`      |
| `plating`      | –      | No       | `set`      |
| `size`         | –      | Per type | `set`      |
| `switch`       | –      | Per type | `set`      |
| `stack_height` | mm     | No       | `exact`    |
| `temp_min`     | °C     | No       | `max`      |
| `temp_max`     | °C     | No       | `min`      |

- `interface` is the connector type (members below).
- `family` defines mating and drop-in compatibility. For proprietary series (board-to-board, wire-to-board, FFC/FPC), it must be narrow enough that every match mates with the counterpart. Write `family *` only when `interface`, the footprint and the other keys fully define compatibility, such as standard pin headers, barrel jacks with `size` and `switch`, and battery holders with `size`.
- `current` is the rated current per contact, e.g. `3A`.
- `voltage` is the rated voltage.
- `durability` is the rated number of mating cycles, written as a plain number (e.g. `5000`).
- `plating` is one or more contact platings (members below). Use it when the plating must match the mating part.
- `size` is the mating size of a barrel jack or the cell size of a battery holder (members below).
- `switch` is the built-in switch contact of a barrel or audio jack (members below).
- `stack_height` is the distance between the two boards when mated, for board-to-board connectors, e.g. `1.5mm`.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

Required keys per `interface`:

| Interface        | Required keys      |
| ---------------- | ------------------ |
| `dc_barrel`      | `size`, `switch`   |
| `battery_holder` | `size`             |
| `audio_jack`     | `switch`           |
| others           | –                  |

`interface` members:

| Member           | Description                                         |
| ---------------- | --------------------------------------------------- |
| `board_to_board` | Mezzanine or stacking connector between two boards  |
| `wire_to_board`  | Board side of a cable connector (e.g. JST, Molex)   |
| `ffc_fpc`        | Flat flexible cable or flexible circuit connector   |
| `pin_header`     | Male pin header                                     |
| `pin_socket`     | Female socket header                                |
| `terminal_block` | Screw or spring terminal block                      |
| `usb_a`          | USB Type-A receptacle                               |
| `usb_c`          | USB Type-C receptacle                               |
| `usb_micro_b`    | USB Micro-B receptacle                              |
| `hdmi`           | HDMI Type A (standard) receptacle                   |
| `hdmi_micro`     | HDMI Type D (micro) receptacle                      |
| `rj45`           | RJ45 Ethernet jack, with or without magnetics       |
| `dc_barrel`      | DC barrel power jack                                |
| `audio_jack`     | 3.5 mm or 2.5 mm audio jack                         |
| `battery_holder` | Battery holder or clip (e.g. for a coin cell)       |
| `memory_card`    | Memory card socket (e.g. microSD)                   |
| `m2`             | M.2 edge connector socket                           |
| `rf_coaxial`     | RF coaxial connector (e.g. U.FL, SMA)               |

`plating` members:

| Member   | Description            |
| -------- | ---------------------- |
| `gold`   | Gold plated contacts   |
| `tin`    | Tin plated contacts    |
| `silver` | Silver plated contacts |
| `nickel` | Nickel plated contacts |

`size` members:

| Member       | Description                                      |
| ------------ | ------------------------------------------------ |
| `5.5x2.1mm`  | Barrel jack, 5.5 mm outer and 2.1 mm center pin  |
| `5.5x2.5mm`  | Barrel jack, 5.5 mm outer and 2.5 mm center pin  |
| `3.5x1.35mm` | Barrel jack, 3.5 mm outer and 1.35 mm center pin |
| `cr2032`     | Coin cell holder, 20 mm × 3.2 mm cell            |
| `cr2025`     | Coin cell holder, 20 mm × 2.5 mm cell            |
| `cr2016`     | Coin cell holder, 20 mm × 1.6 mm cell            |
| `cr1220`     | Coin cell holder, 12.5 mm × 2.0 mm cell          |

`switch` members:

| Member            | Description                                         |
| ----------------- | --------------------------------------------------- |
| `none`            | No switch contact                                   |
| `normally_closed` | Switch contact closed when no plug is inserted      |
| `normally_open`   | Switch contact open when no plug is inserted        |

Examples:

```
interface  board_to_board
family     DF40C-100DS-0.4V(51)
```

```
interface   usb_c
family      *
current     3A
durability  10000
```

```
interface  pin_header
family     *
plating    gold
```

```
interface  dc_barrel
family     *
size       5.5x2.1mm
switch     normally_closed
voltage    48V
current    6A
```

```
interface  battery_holder
family     *
size       cr2032
```

### `DIO`: Diodes

Discrete diodes: signal, rectifier, Schottky, Zener, TVS and ESD protection diodes, including multi-channel ESD arrays. LEDs are in `LED`.

Reference prefix: `D`

| Key           | Unit | Required  | Comparison |
| ------------- | ---- | --------- | ---------- |
| `type`        | –    | Yes       | `set`      |
| `family`      | –    | Yes       | `pattern`  |
| `vr`          | V    | Per type  | `min`      |
| `if`          | A    | Per type  | `min`      |
| `vf`          | V    | No        | `max`      |
| `trr`         | s    | No        | `max`      |
| `vz`          | V    | Per type  | `exact`    |
| `tolerance`   | %    | Per type  | `max`      |
| `power`       | W    | Per type  | `min`      |
| `vrwm`        | V    | Per type  | `min`      |
| `vclamp`      | V    | Per type  | `max`      |
| `ppk`         | W    | Per type  | `min`      |
| `direction`   | –    | Per type  | `set`      |
| `capacitance` | F    | No        | `max`      |
| `aec_q101`    | –    | No        | `exact`    |
| `temp_min`    | °C   | No        | `max`      |
| `temp_max`    | °C   | No        | `min`      |

- `type` is the diode type (members below). It decides which keys are required.
- `family` defines drop-in compatibility. Write `family *` only when `type`, the footprint and the other keys fully define compatibility, such as single diodes in two-terminal packages. Three-terminal packages such as SOT-23 come in several pin configurations (single, dual common cathode, series), so their pattern must fix the configuration.
- `vr` is the rated reverse voltage, e.g. `40V`.
- `if` is the rated average forward current, e.g. `1A`.
- `vf` is the maximum forward voltage at the rated forward current, e.g. `0.5V`.
- `trr` is the maximum reverse recovery time, e.g. `4ns`.
- `vz` is the nominal Zener voltage, e.g. `5.1V`.
- `tolerance` is the Zener voltage tolerance, e.g. `5%`.
- `power` is the rated power dissipation, e.g. `0.5W`.
- `vrwm` is the reverse standoff voltage of a TVS or ESD diode. It must be at least the working voltage of the protected line, e.g. `5V`.
- `vclamp` is the maximum clamping voltage at the rated peak pulse current, e.g. `38.9V`.
- `ppk` is the rated peak pulse power, e.g. `400W`.
- `direction` is `unidirectional` or `bidirectional` (members below).
- `capacitance` is the maximum junction capacitance, e.g. `0.5pF`. Use it for ESD protection on high-speed lines.
- `aec_q101` is `yes` when automotive qualification (AEC-Q101) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

Required keys per `type`:

| Type        | Required keys                              |
| ----------- | ------------------------------------------ |
| `signal`    | `vr`, `if`                                 |
| `rectifier` | `vr`, `if`                                 |
| `schottky`  | `vr`, `if`                                 |
| `zener`     | `vz`, `tolerance`, `power`                 |
| `tvs`       | `vrwm`, `vclamp`, `ppk`, `direction`       |
| `esd`       | `vrwm`, `direction`                        |

`type` members:

| Member      | Description                                                    |
| ----------- | -------------------------------------------------------------- |
| `signal`    | Small-signal and switching diode                               |
| `rectifier` | Standard or fast recovery rectifier                            |
| `schottky`  | Schottky barrier diode                                         |
| `zener`     | Zener voltage reference or clamp                               |
| `tvs`       | Transient voltage suppressor for surges on power and I/O lines |
| `esd`       | ESD protection diode or multi-channel array for data lines     |

`direction` members:

| Member           | Description                                 |
| ---------------- | ------------------------------------------- |
| `unidirectional` | Clamps in one direction, for DC lines       |
| `bidirectional`  | Clamps in both directions, for AC or signal lines that swing both ways |

Examples:

```
type    signal
family  *
vr      75V
if      150mA
```

```
type    schottky
family  *
vr      40V
if      1A
vf      0.5V
```

```
type       tvs
family     SMAJ24A*
vrwm       24V
vclamp     38.9V
ppk        400W
direction  unidirectional
```

### `DIS`: Displays

Display panels and modules: LCD, OLED, e-paper and segment displays, with or without a touch panel.

Reference prefix: `DS`

| Key          | Unit | Required | Comparison |
| ------------ | ---- | -------- | ---------- |
| `type`       | –    | Yes      | `set`      |
| `family`     | –    | Yes      | `pattern`  |
| `diagonal`   | in   | Yes      | `exact`    |
| `resolution` | –    | Yes      | `exact`    |
| `interface`  | –    | Yes      | `set`      |
| `touch`      | –    | Yes      | `set`      |
| `brightness` | nit  | No       | `min`      |
| `temp_min`   | °C   | No       | `max`      |
| `temp_max`   | °C   | No       | `min`      |

- `type` is the display technology (members below).
- `family` defines drop-in compatibility: outline, mounting, flex cable pinout and the initialization used by Screenly software. The pattern must be narrow and `family *` is never used.
- `diagonal` is the active area diagonal in inches, e.g. `7in`.
- `resolution` is the native resolution, written as width `x` height in pixels (e.g. `1024x600`).
- `interface` is the video interface (members below).
- `touch` is the touch panel type (members below).
- `brightness` is the minimum luminance, e.g. `400nit` (cd/m²).
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.
- A display connected by cable is an [off-board item](bom-standard.md#off-board-items) with no footprint. The board connector is a separate `CON` symbol. Only displays soldered to the board, such as segment displays, have a footprint.

`type` members:

| Member    | Description                               |
| --------- | ----------------------------------------- |
| `lcd`     | TFT liquid crystal display with backlight |
| `oled`    | Organic LED display                       |
| `epaper`  | Electrophoretic (e-paper) display         |
| `segment` | Seven-segment or other segment display    |

`interface` members:

| Member     | Description                             |
| ---------- | --------------------------------------- |
| `mipi_dsi` | MIPI DSI                                |
| `hdmi`     | HDMI                                    |
| `lvds`     | LVDS                                    |
| `edp`      | Embedded DisplayPort                    |
| `rgb`      | Parallel RGB                            |
| `spi`      | SPI                                     |
| `i2c`      | I²C                                     |
| `direct`   | Segments driven directly, no controller |

`touch` members:

| Member       | Description                |
| ------------ | -------------------------- |
| `none`       | No touch panel             |
| `capacitive` | Projected capacitive touch |
| `resistive`  | Resistive touch            |

Example:

```
type        lcd
family      SC1635*
diagonal    7in
resolution  720x1280
interface   mipi_dsi
touch       capacitive
```

### `FBD`: Ferrite Beads

Chip ferrite beads for noise suppression on signal and power lines.

Reference prefix: `FB`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `family`    | –    | Yes      | `pattern`  |
| `impedance` | Ω    | Yes      | `exact`    |
| `current`   | A    | Yes      | `min`      |
| `dcr`       | Ω    | No       | `max`      |
| `aec_q200`  | –    | No       | `exact`    |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `family` defines drop-in compatibility. Write `family *` only when the footprint and the other keys fully define compatibility, such as general-purpose beads in standard chip sizes. Beads with the same impedance at 100 MHz can behave differently at other frequencies, so fix the family when the filter design depends on the full impedance curve.
- `impedance` is the nominal impedance at 100 MHz, written without the Ω symbol: `120`, `600`, `1K`.
- `current` is the rated current, e.g. `2A`.
- `dcr` is the maximum DC resistance, written without the Ω symbol: `50m` (50 mΩ). Use it on power lines, where the voltage drop matters.
- `aec_q200` is `yes` when automotive qualification (AEC-Q200) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

Examples:

```
family     *
impedance  600
current    0.5A
```

```
family     *
impedance  120
current    3A
dcr        40m
```

### `FET`: Field-Effect Transistors

Discrete MOSFETs: single, dual and complementary.

Reference prefix: `Q`

| Key        | Unit | Required | Comparison |
| ---------- | ---- | -------- | ---------- |
| `type`     | –    | Yes      | `set`      |
| `family`   | –    | Yes      | `pattern`  |
| `vds`      | V    | Yes      | `min`      |
| `id`       | A    | Yes      | `min`      |
| `rds_on`   | Ω    | Yes      | `max`      |
| `vgs`      | V    | Yes      | `max`      |
| `vgs_max`  | V    | No       | `min`      |
| `qg`       | C    | No       | `max`      |
| `power`    | W    | No       | `min`      |
| `aec_q101` | –    | No       | `exact`    |
| `temp_min` | °C   | No       | `max`      |
| `temp_max` | °C   | No       | `min`      |

- `type` is the transistor type (members below).
- `family` defines drop-in compatibility. Transistor pinouts are not standard, even within one package such as SOT-23, so the pattern must fix the pinout.
- `vds` is the rated drain-source voltage, e.g. `30V`.
- `id` is the rated continuous drain current, e.g. `3A`.
- `rds_on` is the maximum on-resistance, written without the Ω symbol: `50m` (50 mΩ). It must be met at the gate voltage given in `vgs`.
- `vgs` is the gate-source voltage the design drives the gate with, e.g. `2.5V`. A part matches when its `rds_on` is specified at this voltage or lower, so logic-level drive is respected.
- `vgs_max` is the rated maximum gate-source voltage, e.g. `12V`. Use it when the gate drive is high.
- `qg` is the maximum total gate charge, e.g. `10nC`. Use it for switching applications.
- `power` is the rated power dissipation, e.g. `1.4W`.
- `aec_q101` is `yes` when automotive qualification (AEC-Q101) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

For dual and complementary types, the values apply to every transistor in the package.

`type` members:

| Member      | Description                                      |
| ----------- | ------------------------------------------------ |
| `nmos`      | N-channel MOSFET, single or dual                 |
| `pmos`      | P-channel MOSFET, single or dual                 |
| `nmos_pmos` | Complementary pair, one N-channel and one P-channel |

Example:

```
type    nmos
family  AO3400*
vds     30V
id      3A
rds_on  50m
vgs     2.5V
```

### `FUS`: Fuses and Protectors

Overcurrent protection: one-time fuses and resettable PTC fuses (polyfuses). TVS and ESD diodes are in `DIO`.

Reference prefix: `F`

| Key          | Unit | Required | Comparison |
| ------------ | ---- | -------- | ---------- |
| `type`       | –    | Yes      | `set`      |
| `family`     | –    | Yes      | `pattern`  |
| `current`    | A    | Yes      | `exact`    |
| `voltage`    | V    | Yes      | `min`      |
| `breaking`   | A    | No       | `min`      |
| `speed`      | –    | No       | `set`      |
| `trip`       | A    | No       | `max`      |
| `resistance` | Ω    | No       | `max`      |
| `aec_q200`   | –    | No       | `exact`    |
| `temp_min`   | °C   | No       | `max`      |
| `temp_max`   | °C   | No       | `min`      |

- `type` is the protector type (members below).
- `family` defines drop-in compatibility. Write `family *` only when `type`, the footprint and the other keys fully define compatibility, such as chip fuses in standard sizes. Fuses with the same rating can differ in their time-current curve, so fix the family when the protection depends on it.
- `current` is the rated current: the fuse rating, or the hold current of a PTC fuse, e.g. `2A`. It must match exactly, because a higher rating no longer protects the circuit and a lower one trips in normal use.
- `voltage` is the rated voltage, e.g. `32V`. It must be at least the voltage of the protected circuit.
- `breaking` is the rated breaking capacity (interrupting rating), the highest fault current the part can safely interrupt, e.g. `50A`.
- `speed` is the fuse speed (members below). It only applies to `fuse`.
- `trip` is the maximum trip current of a PTC fuse, e.g. `4A`. It only applies to `ptc`.
- `resistance` is the maximum resistance in normal operation, written without the Ω symbol: `50m` (50 mΩ). Use it when the voltage drop matters.
- `aec_q200` is `yes` when automotive qualification (AEC-Q200) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`type` members:

| Member | Description                                                         |
| ------ | ------------------------------------------------------------------- |
| `fuse` | One-time fuse, replaced after it opens                              |
| `ptc`  | Resettable PTC fuse (polyfuse), recovers after the fault is removed |

`speed` members:

| Member      | Description                                                 |
| ----------- | ----------------------------------------------------------- |
| `very_fast` | Very fast acting, for semiconductor protection              |
| `fast`      | Fast acting, general purpose                                |
| `slow`      | Slow blow (time delay), tolerates inrush and startup surges |

Examples:

```
type     fuse
family   *
current  2A
voltage  32V
speed    fast
```

```
type     ptc
family   *
current  1.5A
voltage  6V
trip     3A
```

### `IND`: Inductors

Discrete single-winding inductors: power inductors for switching regulators and filters, and RF inductors for matching and tuning. Ferrite beads are in `FBD`, and common mode chokes in `CMC`.

Reference prefix: `L`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `type`      | –    | Yes      | `set`      |
| `family`    | –    | Yes      | `pattern`  |
| `value`     | H    | Yes      | `exact`    |
| `tolerance` | %    | Yes      | `max`      |
| `irms`      | A    | Yes      | `min`      |
| `isat`      | A    | Per type | `min`      |
| `dcr`       | Ω    | No       | `max`      |
| `shielding` | –    | No       | `set`      |
| `srf`       | Hz   | No       | `min`      |
| `q`         | –    | No       | `min`      |
| `aec_q200`  | –    | No       | `exact`    |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `type` is the inductor type (members below). It decides which keys are required.
- `family` defines drop-in compatibility. Write `family *` only when `type`, the footprint and the other keys fully define compatibility, such as RF chip inductors in standard sizes. Power inductors with the same rating can still differ in core material and saturation behavior, so fix the family when the regulator design depends on it.
- `value` is the nominal inductance, written with `H` and an SI prefix: `10nH`, `2.2uH`, `100uH`.
- `tolerance` is the inductance tolerance, e.g. `20%`.
- `irms` is the rated current for the specified temperature rise, e.g. `3A`.
- `isat` is the saturation current, e.g. `4A`. It must be above the peak current in the design.
- `dcr` is the maximum DC resistance, written without the Ω symbol: `50m` (50 mΩ).
- `shielding` is one or more shielding types (members below).
- `srf` is the minimum self-resonant frequency, e.g. `1GHz`.
- `q` is the minimum quality factor, written as a plain number (e.g. `30`).
- `aec_q200` is `yes` when automotive qualification (AEC-Q200) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

Required keys per `type`:

| Type    | Required keys |
| ------- | ------------- |
| `power` | `isat`        |
| `rf`    | –             |

`type` members:

| Member  | Description                                                     |
| ------- | --------------------------------------------------------------- |
| `power` | Power inductor for switching regulators and power filters       |
| `rf`    | RF and signal inductor for matching, tuning and signal filters  |

`shielding` members:

| Member          | Description                                              |
| --------------- | -------------------------------------------------------- |
| `shielded`      | Fully shielded, magnetic field contained by the core     |
| `semi_shielded` | Partly shielded, for example with magnetic resin coating |
| `unshielded`    | Open magnetic path, highest stray field                  |

Examples:

```
type       power
family     *
value      2.2uH
tolerance  20%
irms       3A
isat       4A
dcr        50m
shielding  shielded
```

```
type       rf
family     *
value      10nH
tolerance  2%
irms       300mA
q          30
```

### `ITC`: Integrated Circuits

Integrated circuits that no more specific class covers: interface ICs (USB and Type-C port controllers, signal multiplexers, redrivers, level shifters, transceivers), audio ICs, logic ICs and security ICs. Microcontrollers are in `MCU`, power ICs in `PWR`, sensors in `SNS` and memories in `STO`.

Reference prefix: `U`

| Key        | Unit | Required | Comparison |
| ---------- | ---- | -------- | ---------- |
| `function` | –    | Yes      | `set`      |
| `family`   | –    | Yes      | `pattern`  |
| `vdd`      | V    | Yes      | `range`    |
| `aec_q100` | –    | No       | `exact`    |
| `temp_min` | °C   | No       | `max`      |
| `temp_max` | °C   | No       | `min`      |

- `function` is the main function of the IC (members below).
- `family` defines drop-in compatibility: pinout, package and function. ICs are rarely interchangeable across manufacturers, so the pattern must be narrow and `family *` is never used.
- `vdd` is the supply voltage of the design, e.g. `3.3V`. ICs with several supplies list each rail, separated by commas (e.g. `3.3V,5V`). A part matches when each rated supply range includes its rail.
- `aec_q100` is `yes` when automotive qualification (AEC-Q100) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.
- ICs that contain firmware follow the [firmware-bearing parts](bom-standard.md#firmware-bearing-parts) rule.

`function` members:

| Member             | Description                                                       |
| ------------------ | ----------------------------------------------------------------- |
| `usb_c_controller` | USB Type-C port controller (CC logic), with or without a data mux |
| `signal_mux`       | Analog or high-speed signal multiplexer or switch                 |
| `redriver`         | Signal redriver or retimer                                        |
| `level_shifter`    | Logic level translator                                            |
| `transceiver`      | Interface transceiver or PHY (e.g. CAN, RS-485, Ethernet)         |
| `logic`            | Logic gates, buffers and flip-flops                               |
| `security`         | Security IC (e.g. TPM, secure element)                            |
| `audio`            | Audio converter or amplifier (e.g. I2S DAC, codec, class-D amp)   |

Example:

```
function  usb_c_controller
family    HD3SS3220*RNH*
vdd       3.3V,5V
temp_min  -40C
temp_max  85C
```

### `LED`: Light Emitting Diodes

Indicator and illumination LEDs, single color and multi-color (RGB) packages. Infrared emitters are included.

Reference prefix: `D`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `color`     | –    | Yes      | `set`      |
| `family`    | –    | Yes      | `pattern`  |
| `if`        | A    | Yes      | `min`      |
| `vf`        | V    | No       | `max`      |
| `intensity` | cd   | No       | `min`      |
| `angle`     | deg  | No       | `min`      |
| `lens`      | –    | No       | `set`      |
| `aec_q102`  | –    | No       | `exact`    |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `color` is the emitted color (members below).
- `family` defines drop-in compatibility. Write `family *` only when `color`, the footprint and the other keys fully define compatibility, such as single color LEDs in two-terminal packages. Multi-color packages differ in pin order and common anode or cathode, so their pattern must fix the pinout. For a consistent product look, fix the family also when the exact shade and brightness matter.
- `if` is the rated continuous forward current, e.g. `20mA`. It must be at least the current the design drives through the LED.
- `vf` is the maximum forward voltage at the rated current, e.g. `3V`. Use it when the supply leaves little headroom, such as blue or white LEDs on 3.3 V.
- `intensity` is the minimum luminous intensity, e.g. `500mcd`.
- `angle` is the viewing angle, e.g. `120deg`.
- `lens` is the lens type (members below).
- `aec_q102` is `yes` when automotive qualification (AEC-Q102) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`color` members:

| Member          | Description                         |
| --------------- | ----------------------------------- |
| `red`           | Red, about 620–630 nm               |
| `orange`        | Orange, about 600–610 nm            |
| `amber`         | Amber, about 590 nm                 |
| `yellow`        | Yellow, about 585–590 nm            |
| `green`         | Green, about 520–530 nm             |
| `yellow_green`  | Yellow-green, about 565–575 nm      |
| `blue`          | Blue, about 465–475 nm              |
| `white_cool`    | White, above 5000 K                 |
| `white_neutral` | White, 3500–5000 K                  |
| `white_warm`    | White, below 3500 K                 |
| `rgb`           | Red, green and blue in one package  |
| `infrared`      | Infrared, 850 nm or 940 nm          |

`lens` members:

| Member     | Description                                  |
| ---------- | -------------------------------------------- |
| `clear`    | Water-clear lens, narrow and bright spot     |
| `diffused` | Diffused lens, even appearance from all angles |

Examples:

```
color   green
family  *
if      20mA
lens    diffused
```

```
color      white_cool
family     *
if         20mA
vf         3V
intensity  500mcd
```

### `MCU`: Microcontrollers

Microcontrollers.

Reference prefix: `U`

| Key        | Unit | Required | Comparison |
| ---------- | ---- | -------- | ---------- |
| `family`   | –    | Yes      | `pattern`  |
| `flash`    | B    | Yes      | `min`      |
| `ram`      | B    | No       | `min`      |
| `vdd`      | V    | Yes      | `range`    |
| `aec_q100` | –    | No       | `exact`    |
| `temp_min` | °C   | No       | `max`      |
| `temp_max` | °C   | No       | `min`      |

- `family` defines drop-in compatibility: pinout, package, peripherals and firmware compatibility. The pattern must be narrow and `family *` is never used.
- `flash` is the on-chip flash size, written with `KB` or `MB` (e.g. `32KB`).
- `ram` is the on-chip RAM size, e.g. `8KB`.
- `vdd` is the supply voltage of the design, e.g. `3.3V`. A part matches when its rated supply range includes it.
- `aec_q100` is `yes` when automotive qualification (AEC-Q100) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.
- Microcontrollers contain firmware, so the [firmware-bearing parts](bom-standard.md#firmware-bearing-parts) rule applies. A microcontroller programmed before assembly is a `PSP` part, see the [Assembly Part Library Standard](assembly-part-library-standard.md).

Example:

```
family  STM32L0?1C?T?
flash   32KB
vdd     3.3V
```

### `MIC`: Microphones

MEMS and electret microphones.

Reference prefix: `MK`

| Key           | Unit | Required | Comparison |
| ------------- | ---- | -------- | ---------- |
| `type`        | –    | Yes      | `set`      |
| `output`      | –    | Yes      | `set`      |
| `family`      | –    | Yes      | `pattern`  |
| `port`        | –    | Yes      | `set`      |
| `vdd`         | V    | Yes      | `range`    |
| `sensitivity` | dB   | No       | `exact`    |
| `snr`         | dB   | No       | `min`      |
| `temp_min`    | °C   | No       | `max`      |
| `temp_max`    | °C   | No       | `min`      |

- `type` is the microphone type (members below).
- `output` is the output signal (members below).
- `family` defines drop-in compatibility: pinout, acoustic port position and the audio configuration used by Screenly software. The pattern must be narrow and `family *` is never used.
- `port` is the acoustic port position (members below). The board and enclosure openings are designed for it.
- `vdd` is the supply voltage of the design, e.g. `1.8V`. A part matches when its rated supply range includes it.
- `sensitivity` is the nominal sensitivity, written in `dBFS` for digital or `dBV` for analog microphones (e.g. `-26dBFS`, `-38dBV`).
- `snr` is the minimum signal-to-noise ratio, e.g. `65dB`.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`type` members:

| Member     | Description                   |
| ---------- | ----------------------------- |
| `mems`     | MEMS microphone               |
| `electret` | Electret condenser microphone |

`output` members:

| Member   | Description        |
| -------- | ------------------ |
| `analog` | Analog output      |
| `pdm`    | Digital PDM output |
| `i2s`    | Digital I²S output |

`port` members:

| Member   | Description                              |
| -------- | ---------------------------------------- |
| `top`    | Sound enters from the top of the package |
| `bottom` | Sound enters through a hole in the board |

Example:

```
type         mems
output       pdm
family       ICS-41351*
port         bottom
vdd          1.8V
sensitivity  -26dBFS
```

### `MOD`: Modules

Pre-assembled modules that are mounted as a single part, such as compute modules (e.g. Raspberry Pi CM5) and radio modules.

Reference prefix: `U`

| Key        | Unit | Required | Comparison |
| ---------- | ---- | -------- | ---------- |
| `family`   | –    | Yes      | `pattern`  |
| `ram`      | B    | No       | `min`      |
| `storage`  | B    | No       | `min`      |
| `wireless` | –    | No       | `exact`    |
| `temp_min` | °C   | No       | `max`      |
| `temp_max` | °C   | No       | `min`      |

- `family` defines drop-in compatibility. Modules are rarely interchangeable across product lines, so the pattern is usually narrow.
- `ram` and `storage` are on-board memory and storage, written with `KB`, `MB` or `GB` (e.g. `4GB`).
- `wireless` is `yes` or `no`, for modules sold with and without a radio.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.
- Modules usually contain firmware, so the [firmware-bearing parts](bom-standard.md#firmware-bearing-parts) rule applies.
- A module that plugs into board connectors, such as the CM5, has a footprint that holds the pads of those connectors at the exact module spacing. The connectors themselves are separate `CON` symbols, placed as [off-board items](bom-standard.md#off-board-items) so they appear in the BOM.

Example:

```
family    CM5*
ram       4GB
storage   64GB
wireless  yes
temp_min  -20C
temp_max  85C
```

### `OSC`: Oscillators

Active clock oscillators with a built-in driver: crystal (XO, TCXO, VCXO) and MEMS oscillators. Passive crystals are in `XTL`.

Reference prefix: `X`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `family`    | –    | Yes      | `pattern`  |
| `frequency` | Hz   | Yes      | `exact`    |
| `stability` | ppm  | Yes      | `max`      |
| `vdd`       | V    | Yes      | `range`    |
| `output`    | –    | Yes      | `set`      |
| `current`   | A    | No       | `max`      |
| `aec_q200`  | –    | No       | `exact`    |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `family` defines drop-in compatibility. The function of the control pin (output enable, standby or not connected) differs between parts in the same package, so the pattern must fix it.
- `frequency` is the output frequency, e.g. `25MHz`.
- `stability` is the maximum total frequency deviation over the operating temperature range, written with `ppm` (e.g. `50ppm`).
- `vdd` is the supply voltage of the design, e.g. `3.3V`. A part matches when its rated supply range includes it.
- `output` is the output signal type (members below).
- `current` is the maximum supply current, e.g. `10mA`.
- `aec_q200` is `yes` when automotive qualification (AEC-Q200) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`output` members:

| Member         | Description                                   |
| -------------- | --------------------------------------------- |
| `cmos`         | Single-ended CMOS (LVCMOS)                    |
| `clipped_sine` | Clipped sine wave, typical for TCXOs          |
| `lvds`         | Differential LVDS                             |
| `lvpecl`       | Differential LVPECL                           |
| `hcsl`         | Differential HCSL, typical for PCIe reference clocks |

Example:

```
family     SiT1602BC-?3-33E-25.000000*
frequency  25MHz
stability  50ppm
vdd        3.3V
output     cmos
```

### `PWR`: Power ICs

Voltage regulator ICs: linear regulators (including LDOs) and switching regulators. Switching controllers that drive external switches are included. Multi-rail PMICs are not.

Power switch ICs are also in this class: load switches, current-limited power distribution switches and eFuses. They pass the input voltage through to the output and do not regulate it.

Reference prefix: `U`

| Key         | Unit | Required     | Comparison |
| ----------- | ---- | ------------ | ---------- |
| `topology`  | –    | Yes          | `set`      |
| `family`    | –    | Yes          | `pattern`  |
| `vin_min`   | V    | Yes          | `max`      |
| `vin_max`   | V    | Yes          | `min`      |
| `vout`      | V    | Per topology | `exact`    |
| `iout`      | A    | Yes          | `min`      |
| `ilimit`    | A    | No           | `max`      |
| `frequency` | Hz   | No           | `exact`    |
| `dropout`   | V    | No           | `max`      |
| `iq`        | A    | No           | `max`      |
| `aec_q100`  | –    | No           | `exact`    |
| `temp_min`  | °C   | No           | `max`      |
| `temp_max`  | °C   | No           | `min`      |

- `topology` is the regulator or switch type (members below).
- `family` defines drop-in compatibility: pinout, package and function. It must be narrow enough that every match works with the surrounding components.
- `vin_min` and `vin_max` are the required input voltage range. A part matches when its input range covers the required range.
- `vout` is the fixed output voltage (e.g. `3.3V`), or `adj` for adjustable parts set by external resistors. It is required for every topology except `power_switch`, whose output follows the input.
- `iout` is the rated output current, e.g. `2A`. For a power switch, it is the rated continuous load current.
- `ilimit` is the maximum current-limit threshold of a power switch, e.g. `0.8A`, or `adj` for parts set by an external resistor. A part matches when its maximum threshold is at or below the required one, so the protected load or the upstream supply is never exposed to more current.
- `frequency` is the switching frequency, e.g. `2.2MHz`. It only applies to switching topologies. The inductor and capacitors are designed for it, so it must match exactly.
- `dropout` is the maximum dropout voltage at the rated output current, e.g. `300mV`. It only applies to `linear` and `ldo`.
- `iq` is the maximum quiescent current, e.g. `50uA`.
- `aec_q100` is `yes` when automotive qualification (AEC-Q100) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`topology` members:

| Member         | Description                                                     |
| -------------- | --------------------------------------------------------------- |
| -------------  | --------------------------------------------------------        |
| `linear`       | Linear regulator, standard dropout                              |
| `ldo`          | Low-dropout linear regulator                                    |
| `buck`         | Step-down switching regulator                                   |
| `boost`        | Step-up switching regulator                                     |
| `buck_boost`   | Step-up/step-down switching regulator                           |
| `inverting`    | Negative output switching regulator                             |
| `charge_pump`  | Switched-capacitor regulator, no inductor                       |
| `power_switch` | Load switch, current-limited power distribution switch or eFuse |

Examples:

```
topology  ldo
family    AP2112K-3.3*
vin_min   4.5V
vin_max   5.5V
vout      3.3V
iout      0.6A
```

```
topology   buck
family     TPS6213?RGT*
vin_min    4.5V
vin_max    17V
vout       adj
iout       3A
frequency  2.5MHz
```

```
topology  power_switch
family    AP22653W6*
vin_min   3V
vin_max   5.5V
iout      2.1A
ilimit    adj
```

### `RES`: Resistors

Discrete resistors, including zero-ohm jumpers and current sense resistors.

Reference prefix: `R`

| Key          | Unit   | Required | Comparison |
| ------------ | ------ | -------- | ---------- |
| `value`      | Ω      | Yes      | `exact`    |
| `tolerance`  | %      | Yes      | `max`      |
| `power`      | W      | Yes      | `min`      |
| `voltage`    | V      | No       | `min`      |
| `tempco`     | ppm/°C | No       | `max`      |
| `technology` | –      | No       | `set`      |
| `aec_q200`   | –      | No       | `exact`    |
| `temp_min`   | °C     | No       | `max`      |
| `temp_max`   | °C     | No       | `min`      |

- `value` is written without the Ω symbol, with an SI prefix where needed: `100`, `4.7K`, `1M`, `10m` (10 mΩ). Zero-ohm jumpers use `value 0`, and their `tolerance` is not checked.
- `voltage` is the maximum working voltage.
- `tempco` is the temperature coefficient (TCR), written with `ppm` (e.g. `100ppm`).
- `technology` is one or more resistor technologies (members below).
- `aec_q200` is `yes` when automotive qualification (AEC-Q200) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`technology` members:

| Member          | Description                                                   |
| --------------- | ------------------------------------------------------------- |
| `thick_film`    | Thick film chip resistor, general purpose                     |
| `thin_film`     | Thin film chip resistor, precision and low TCR                |
| `metal_film`    | Metal film, usually through-hole or MELF                      |
| `metal_element` | Metal strip or foil element, low-ohm current sense            |
| `wirewound`     | Wire wound, high power or pulse load                          |

Examples:

```
value      10K
tolerance  10%
power      0.1W
```

```
value       10m
tolerance   1%
power       0.5W
tempco      75ppm
technology  metal_element
```

### `SNS`: Sensors

Sensor ICs and modules that measure a physical quantity, such as temperature, humidity, light or motion. Microphones are in `MIC`.

Reference prefix: `U`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `measures`  | –    | Yes      | `all`      |
| `family`    | –    | Yes      | `pattern`  |
| `interface` | –    | Yes      | `set`      |
| `vdd`       | V    | Yes      | `range`    |
| `address`   | –    | Per type | `exact`    |
| `current`   | A    | No       | `max`      |
| `aec_q100`  | –    | No       | `exact`    |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `measures` is one or more measured quantities, separated by `|` (members below). A part matches when it measures every listed quantity.
- `family` defines drop-in compatibility. Sensors with digital interfaces are read by Screenly software, so a substitute must have the same pinout and be supported by the same driver (register map and data format). Accuracy and range also differ between parts, so the pattern must be narrow and `family *` is never used.
- `interface` is the output interface (members below).
- `vdd` is the supply voltage of the design, e.g. `3.3V`. A part matches when its rated supply range includes it.
- `address` is the I²C address, written in hexadecimal (e.g. `0x44`). Parts in one family often differ only in address, and the address must not clash with other devices on the bus.
- `current` is the maximum supply current in operation, e.g. `500uA`.
- `aec_q100` is `yes` when automotive qualification (AEC-Q100) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

Required keys per `interface`:

| Interface | Required keys |
| --------- | ------------- |
| `i2c`     | `address`     |
| others    | –             |

`measures` members:

| Member         | Description                                      |
| -------------- | ------------------------------------------------ |
| `temperature`  | Temperature                                      |
| `humidity`     | Relative humidity                                |
| `pressure`     | Barometric or absolute pressure                  |
| `light`        | Ambient light level                              |
| `color`        | Color (RGB or spectral) light measurement        |
| `proximity`    | Distance or proximity of an object               |
| `presence`     | Presence of people, e.g. PIR or radar            |
| `acceleration` | Linear acceleration                              |
| `rotation`     | Angular rate (gyroscope)                         |
| `magnetic`     | Magnetic field, e.g. Hall effect or magnetometer |
| `current`      | Electrical current                               |
| `gas`          | Gas concentration or air quality                 |

`interface` members:

| Member    | Description                               |
| --------- | ----------------------------------------- |
| `i2c`     | I²C                                       |
| `spi`     | SPI                                       |
| `uart`    | UART                                      |
| `onewire` | 1-Wire                                    |
| `digital` | Digital output, e.g. switch, PWM or pulse |
| `analog`  | Analog voltage or current output          |

Examples:

```
measures   temperature|humidity
family     SHT40-AD1B*
interface  i2c
address    0x44
vdd        3.3V
```

```
measures   light
family     VEML7700*
interface  i2c
address    0x10
vdd        3.3V
```

### `SPK`: Speakers

Loudspeakers for audio output.

Reference prefix: `LS`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `family`    | –    | Yes      | `pattern`  |
| `impedance` | Ω    | Yes      | `exact`    |
| `power`     | W    | Yes      | `min`      |
| `spl`       | dB   | No       | `min`      |
| `resonance` | Hz   | No       | `max`      |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `family` defines drop-in compatibility. The enclosure and its acoustic design are made for one speaker, so the pattern must be narrow and `family *` is never used.
- `impedance` is the nominal impedance, written without the Ω symbol: `4`, `8`.
- `power` is the rated power, e.g. `2W`.
- `spl` is the minimum sensitivity at 1 W and 1 m, e.g. `85dB`.
- `resonance` is the maximum resonant frequency, e.g. `300Hz`. Lower values give more bass.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.
- A speaker connected by wires is an [off-board item](bom-standard.md#off-board-items) with no footprint. The board connector is a separate `CON` symbol. Only speakers soldered to the board have a footprint.

Example:

```
family     AS04008*
impedance  8
power      2W
```

### `STO`: Storage Devices

Data storage devices: memory cards, eMMC, NVMe SSDs, USB drives and serial EEPROMs.

Reference prefix: `U`

| Key        | Unit | Required | Comparison |
| ---------- | ---- | -------- | ---------- |
| `type`     | –    | Yes      | `set`      |
| `family`   | –    | Yes      | `pattern`  |
| `capacity` | B    | Yes      | `min`      |
| `grade`    | –    | Per type | `set`      |
| `speed`    | –    | No       | `all`      |
| `form`     | –    | Per type | `set`      |
| `bus`      | –    | Per type | `set`      |
| `vdd`      | V    | No       | `range`    |
| `temp_min` | °C   | No       | `max`      |
| `temp_max` | °C   | No       | `min`      |

- `type` is the storage type (members below). It decides which keys are required.
- `family` defines drop-in compatibility. Write `family *` only for removable cards and drives where `type` and the other keys fully define compatibility. Soldered eMMC and EEPROMs must have a narrow pattern that fixes the pinout and, for EEPROMs, the addressing scheme (8-bit or 16-bit memory address).
- `capacity` is the storage capacity, written with `KB`, `GB` or `TB` (e.g. `8KB`, `32GB`). EEPROM capacity is in bytes, not bits: a 64-Kbit EEPROM is `8KB`.
- `grade` is one or more allowed endurance grades (members below). Devices in always-on products should be `industrial` or `high_endurance`.
- `speed` is one or more speed classes the card must meet, separated by `|` (members below). It only applies to `microsd` and `sd`.
- `form` is the M.2 form factor (members below). It only applies to `nvme`.
- `bus` is the host interface of an EEPROM (members below). It only applies to `eeprom`.
- `vdd` is the supply voltage of the design, e.g. `3.3V`. A part matches when its rated supply range includes it.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.
- Removable storage, such as memory cards and NVMe SSDs, is an [off-board item](bom-standard.md#off-board-items) with no footprint. The socket is a separate `CON` symbol. Only soldered devices, eMMC and EEPROMs, have a footprint.
- Storage devices except EEPROMs contain controller firmware, so they are tracked with `ContainsFirmware` in the HBOM. A device with a Screenly image written before assembly is a `PSP` part, see the [Assembly Part Library Standard](assembly-part-library-standard.md).

Required keys per `type`:

| Type     | Required keys   |
| -------- | --------------- |
| `nvme`   | `grade`, `form` |
| `eeprom` | `bus`           |
| others   | `grade`         |

`type` members:

| Member      | Description      |
| ----------- | ---------------- |
| `microsd`   | microSD card     |
| `sd`        | SD card          |
| `emmc`      | Soldered eMMC    |
| `nvme`      | NVMe SSD         |
| `usb_drive` | USB flash drive  |
| `eeprom`    | Serial EEPROM IC |

`grade` members:

| Member           | Description                                                 |
| ---------------- | ----------------------------------------------------------- |
| `consumer`       | Consumer grade                                              |
| `high_endurance` | High endurance, for continuous writing                      |
| `industrial`     | Industrial grade, wide temperature range and high endurance |

`bus` members:

| Member | Description         |
| ------ | ------------------- |
| `i2c`  | I2C (two-wire) bus  |
| `spi`  | SPI bus             |

`speed` members:

| Member | Description                                 |
| ------ | ------------------------------------------- |
| `c10`  | Speed Class 10, 10 MB/s minimum write       |
| `u1`   | UHS Speed Class 1, 10 MB/s minimum write    |
| `u3`   | UHS Speed Class 3, 30 MB/s minimum write    |
| `v30`  | Video Speed Class 30, 30 MB/s minimum write |
| `a1`   | Application Performance Class 1             |
| `a2`   | Application Performance Class 2             |

`form` members:

| Member    | Description     |
| --------- | --------------- |
| `m2_2230` | M.2, 22 × 30 mm |
| `m2_2242` | M.2, 22 × 42 mm |
| `m2_2280` | M.2, 22 × 80 mm |

Examples:

```
type      microsd
family    *
capacity  32GB
grade     industrial
speed     a1|u1
```

```
type      nvme
family    *
capacity  256GB
grade     consumer|industrial
form      m2_2230
```

```
type      eeprom
family    M24C64-*MN*
capacity  8KB
bus       i2c
vdd       3.3V
```

### `SWC`: Switches

Board-mounted mechanical switches: tactile, push button, slide, toggle, rocker, rotary and DIP switches.

Reference prefix: `SW`

| Key          | Unit   | Required | Comparison |
| ------------ | ------ | -------- | ---------- |
| `type`       | –      | Yes      | `set`      |
| `family`     | –      | Yes      | `pattern`  |
| `circuit`    | –      | Yes      | `set`      |
| `action`     | –      | No       | `set`      |
| `current`    | A      | No       | `min`      |
| `voltage`    | V      | No       | `min`      |
| `force`      | N      | No       | `exact`    |
| `height`     | mm     | No       | `exact`    |
| `durability` | cycles | No       | `min`      |
| `temp_min`   | °C     | No       | `max`      |
| `temp_max`   | °C     | No       | `min`      |

- `type` is the switch type (members below).
- `family` defines drop-in compatibility. Write `family *` only when `type`, the footprint and the other keys fully define compatibility, such as standard 6 × 6 mm tactile switches. Switches are often operated through the enclosure, so fix the family, or set `height` and `force`, whenever the actuator shape or feel matters.
- `circuit` is the switching configuration of each switch element (members below).
- `action` is `momentary` or `latching` (members below).
- `current` is the rated switching current, e.g. `50mA`.
- `voltage` is the rated switching voltage, e.g. `12V`.
- `force` is the nominal operating force, e.g. `1.6N`. It must match exactly to keep the same feel.
- `height` is the actuator height above the board, e.g. `5mm`. It must match exactly, because the enclosure is designed for it.
- `durability` is the rated number of operations, written as a plain number (e.g. `100000`).
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

`type` members:

| Member       | Description                                      |
| ------------ | ------------------------------------------------ |
| `tactile`    | Tactile switch, small momentary push switch      |
| `pushbutton` | Panel push button, larger actuator               |
| `slide`      | Slide switch                                     |
| `toggle`     | Toggle switch with lever                         |
| `rocker`     | Rocker switch                                    |
| `rotary`     | Rotary switch with several positions             |
| `dip`        | DIP switch, array of small switches              |

`circuit` members:

| Member    | Description                                     |
| --------- | ----------------------------------------------- |
| `spst_no` | Single pole, single throw, normally open        |
| `spst_nc` | Single pole, single throw, normally closed      |
| `spdt`    | Single pole, double throw                       |
| `dpst`    | Double pole, single throw                       |
| `dpdt`    | Double pole, double throw                       |

`action` members:

| Member      | Description                                       |
| ----------- | ------------------------------------------------- |
| `momentary` | Returns to its rest position when released        |
| `latching`  | Stays in position until operated again            |

Examples:

```
type     tactile
family   *
circuit  spst_no
force    1.6N
height   5mm
```

```
type     slide
family   *
circuit  spdt
current  0.3A
voltage  6V
```

### `THR`: Thermal Elements

Passive thermal parts: heat sinks, thermal pads, thermal paste and thermal tape.

Reference prefix: `HS`

| Key            | Unit | Required | Comparison |
| -------------- | ---- | -------- | ---------- |
| `type`         | –    | Yes      | `set`      |
| `family`       | –    | Yes      | `pattern`  |
| `conductivity` | W/mK | Per type | `min`      |
| `thickness`    | mm   | Per type | `exact`    |
| `resistance`   | °C/W | No       | `max`      |
| `drawing`      | –    | No       | `exact`    |
| `temp_min`     | °C   | No       | `max`      |
| `temp_max`     | °C   | No       | `min`      |

- `type` is the thermal element type (members below). It decides which keys are required.
- `family` defines drop-in compatibility. Heat sinks must fit the board and enclosure, so their pattern must be narrow, unless the heat sink is made to a Screenly drawing set in `drawing`. Write `family *` only for pads, paste and tape where the other keys fully define compatibility, or together with `drawing`.
- `conductivity` is the thermal conductivity of a pad, paste or tape, e.g. `3W/mK`.
- `thickness` is the thickness of a pad or tape, e.g. `1mm`. It must match exactly, because the gap is designed for it.
- `resistance` is the maximum thermal resistance of a heat sink, e.g. `10C/W`.
- `drawing` is the Screenly drawing number for a part made or cut to a Screenly drawing.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.
- Thermal elements that are not soldered are [off-board items](bom-standard.md#off-board-items) with no footprint.

Required keys per `type`:

| Type            | Required keys               |
| --------------- | --------------------------- |
| `heatsink`      | –                           |
| `thermal_pad`   | `conductivity`, `thickness` |
| `thermal_paste` | `conductivity`              |
| `thermal_tape`  | `conductivity`, `thickness` |

`type` members:

| Member          | Description                        |
| --------------- | ---------------------------------- |
| `heatsink`      | Heat sink                          |
| `thermal_pad`   | Thermal gap pad                    |
| `thermal_paste` | Thermal paste or grease            |
| `thermal_tape`  | Thermally conductive adhesive tape |

Examples:

```
type        heatsink
family      *
drawing     THR-0001
resistance  8C/W
```

```
type          thermal_pad
family        *
conductivity  3W/mK
thickness     1mm
```

### `XTL`: Crystals

Passive quartz crystals, driven by an oscillator circuit in another IC. Active oscillators are in `OSC`.

Reference prefix: `Y`

| Key         | Unit | Required | Comparison |
| ----------- | ---- | -------- | ---------- |
| `family`    | –    | Yes      | `pattern`  |
| `frequency` | Hz   | Yes      | `exact`    |
| `tolerance` | ppm  | Yes      | `max`      |
| `stability` | ppm  | Yes      | `max`      |
| `load`      | F    | Yes      | `exact`    |
| `esr`       | Ω    | No       | `max`      |
| `drive`     | W    | No       | `min`      |
| `aec_q200`  | –    | No       | `exact`    |
| `temp_min`  | °C   | No       | `max`      |
| `temp_max`  | °C   | No       | `min`      |

- `family` defines drop-in compatibility. Write `family *` only when the footprint and the other keys fully define compatibility, such as standard 2-pad or 4-pad SMD crystals with the usual pin assignment.
- `frequency` is the nominal frequency, e.g. `24MHz`, `32.768kHz`.
- `tolerance` is the maximum frequency deviation at 25 °C, written with `ppm` (e.g. `20ppm`).
- `stability` is the maximum frequency deviation over the operating temperature range, written with `ppm` (e.g. `30ppm`).
- `load` is the load capacitance, e.g. `12pF`. The external load capacitors are designed for it, so it must match exactly.
- `esr` is the maximum equivalent series resistance, written without the Ω symbol: `60`, `70K`. The oscillator circuit needs enough margin to start the crystal.
- `drive` is the rated maximum drive level, e.g. `100uW`. It must be at least the drive level of the oscillator circuit.
- `aec_q200` is `yes` when automotive qualification (AEC-Q200) is required. `yes` is its only value; leave it out otherwise.
- `temp_min` and `temp_max` are the required operating temperature range, written with `C` (e.g. `-20C`, `70C`). A part matches when its range covers the required range.

Examples:

```
family     *
frequency  24MHz
tolerance  20ppm
stability  30ppm
load       12pF
esr        60
```

```
family     *
frequency  32.768kHz
tolerance  20ppm
stability  100ppm
load       12.5pF
esr        70K
```

## Open Items

- New IC classes are created and defined when a design first needs one.
- Whether the `value` key is stored in KiCad's built-in `Value` field or in a separate field.
