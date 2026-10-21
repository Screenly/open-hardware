# Part Numbering Standard

Every component (material) used in Screenly hardware gets a unique internal part number.

## Format

```
SRLY-<CLS>-<NNNNNN>
```

| Field      | Description                                         | Example  |
| ---------- | --------------------------------------------------- | -------- |
| `SRLY`     | Fixed company prefix.                               | `SRLY`   |
| `<CLS>`    | 3-letter uppercase class code (see below).          | `RES`    |
| `<NNNNNN>` | 6-digit integer, zero-padded, starting at `000001`. | `000042` |

Example: `SRLY-RES-000042`

Regex: `^SRLY-[A-Z]{3}-[0-9]{6}$`

## Class Codes

| Code  | Class                                       |
| ----- | ------------------------------------------- |
| `ADH` | Adhesives                                   |
| `ADP` | Power adapters                              |
| `ANT` | Antennas                                    |
| `BAT` | Batteries                                   |
| `BJT` | Bipolar junction transistors                |
| `BUZ` | Buzzers                                     |
| `CAB` | Cables and cable assemblies                 |
| `CAP` | Capacitors                                  |
| `CMC` | Common mode chokes                          |
| `CON` | Connectors                                  |
| `DIO` | Diodes                                      |
| `DIS` | Displays                                    |
| `DOC` | Printed documents                           |
| `ENC` | Enclosure parts and assemblies              |
| `ESP` | Electronic semi products                    |
| `FBD` | Ferrite beads                               |
| `FET` | Field-effect transistors                    |
| `FUS` | Fuses and protectors                        |
| `IND` | Inductors                                   |
| `ITC` | Integrated circuits                         |
| `LBL` | Stickers and labels                         |
| `LED` | Light emitting diodes                       |
| `MCU` | Microcontrollers                            |
| `MIC` | Microphones                                 |
| `MOD` | Modules                                     |
| `OSC` | Oscillators                                 |
| `PAC` | Product packages                            |
| `PCB` | Printed circuit boards                      |
| `PSP` | Programmed semi products                    |
| `PWR` | Power ICs (linear and switching regulators, power switches) |
| `RES` | Resistors                                   |
| `SCR` | Screws                                      |
| `SNS` | Sensors                                     |
| `SPK` | Speakers                                    |
| `STO` | Storage devices (e.g. SD card, NVMe disk)   |
| `SWC` | Switches                                    |
| `THR` | Thermal elements                            |
| `XTL` | Crystals                                    |

New classes must be added to this table, in alphabetical order, before use.

## Rules

- Numbers are assigned sequentially within each class.
- One part number per unique part. Parts with different values, packages, or manufacturer part numbers get different numbers.
- Part numbers are never reused or reassigned, even if a part is discontinued.
