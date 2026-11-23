# open-hardware
Repository for Screenly's open hardware projects.

## Screenly CM5 Player

A digital signage player built on the Raspberry Pi Compute Module 5, with the CM4 as a fallback.

- **Display:** 2× HDMI Type A with CEC
- **Network:** Gigabit Ethernet; Wi-Fi and Bluetooth through an external antenna
- **USB:** 2× USB-A 3.0, 1× USB-C 2.0, and an internal USB-C for eMMC flashing
- **Storage:** CM5 eMMC, M.2 M-key NVMe, microSD slot (not fitted in the base variant)
- **Security:** TPM 2.0 (Infineon OPTIGA SLB 9672)
- **Audio:** stereo line output on a 3.5 mm jack (PCM5102A I2S DAC)
- **Power:** 9–16 V DC barrel jack
- **PCB:** 4 layers, 120 × 120 mm

| Item | Location |
| ---- | -------- |
| Specification | [screenly-cm5-player/docs/screenly-cm5-player-specifications.md](screenly-cm5-player/docs/screenly-cm5-player-specifications.md) |
| KiCad project | [screenly-cm5-player/electronics](screenly-cm5-player/electronics) |
| Bare PCB / assembly (`eMMC` variant) | `SRLY-PCB-000001` / `SRLY-ESP-000001` |

## Generating Manufacturing Files

`create-manufacturing-files.sh` creates every file needed to make a board from its KiCad project, with `kicad-cli`:

```
PARTSDB_DIR=<part database> ./create-manufacturing-files.sh <project folder> <variant>
```

`PARTSDB_DIR` is needed only in this early stage, while the part database is a local folder.[^partsdb]

For example: `./create-manufacturing-files.sh screenly-cm5-player/pcb eMMC`.

The script runs ERC and DRC first and stops on errors. It writes into `<project folder>/outputs`:

| Output | Content |
| ------ | ------- |
| `manufacturing/pcb/<PCB_PN>.zip` | Gerbers, drill files, Gerber job file and fabrication notes, ready to upload to a PCB fab |
| `manufacturing/assembly/<ESP_PN>.zip` | BOM, HBOM (CycloneDX), pick-and-place files (CSV and KiCad `.pos`), assembly drawing (PDF) and assembly notes |
| `3d/<project>-<revision>.step.zip` | STEP model of the board |

Requirements:

- **Tools:** KiCad 10 (`kicad-cli`), Python 3 and `zip`. On the first run, the script installs `cyclonedx-python-lib` into a git-ignored `.venv/` for the HBOM.
- **Part database:** access through `tools/partsdb.py`, which reads part attributes for the HBOM. The database is private; see [How to Add Parts into the Library](docs/how-to-add-parts-into-the-library.md).
- **Project text variables** (KiCad: File → Project Setup → Text Variables):
  - `PCB_PN`: part number of the bare PCB;
  - `ESP_PN_<variant>`: part number of the assembly of each variant;
  - optional `FAB_*` and `ASM_*` variables for fabrication and assembly facts KiCad can't store, such as material, quality class and inspection. See `tools/manufacturing.py` for the list.
- **Board title block:** the revision, used in file names and notes.

Everything is generated from the source files, so fix the design or project settings rather than editing the outputs.

[^partsdb]: The part database will become a remote web service. Only `tools/partsdb.py` will change then, and `PARTSDB_DIR` will be replaced by the service's own settings; the script itself stays the same.

## License

Copyright Screenly, Inc.

This source describes Open Hardware and is licensed under the CERN-OHL-P v2 (SPDX: `CERN-OHL-P-2.0`). See [LICENSE](LICENSE) for the full text.

You may redistribute and modify this source and make products using it under the terms of the CERN-OHL-P v2 (https://cern.ch/cern-ohl).

This source is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A PARTICULAR PURPOSE. Please see the CERN-OHL-P v2 for applicable conditions.

Source location: https://github.com/Screenly/open-hardware

Third-party 3D models in `library/3d-models` come from component manufacturers and the KiCad libraries, and remain under their owners' terms.
