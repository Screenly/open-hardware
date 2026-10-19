# Screenly CM5 Player Specifications

Hardware specifications of the Screenly CM5 Player, a digital signage player based on the Raspberry Pi Compute Module 5 (CM5).

## Compute Module

| Item            | Specification                                                                   |
| --------------- | ------------------------------------------------------------------------------- |
| Module          | Raspberry Pi Compute Module 5, wireless variant                                 |
| RAM             | 4 GB                                                                            |
| eMMC            | 64 GB on the module                                                             |
| Wireless antenna | External antenna with an SMA connector on the enclosure, connected to the CM5's U.FL (MHF) antenna connector |
| RTC             | The CM5's built-in RTC. No external RTC chip (such as the NXP PCF85063A) is used. |

## Display Outputs

- Two standard-size HDMI Type A outputs (not micro HDMI).
- Both HDMI outputs support HDMI-CEC and DDC/CI.

## Audio Jack

- One 3.5 mm jack with stereo audio output (left and right), like the Raspberry Pi 4B jack without its composite video.
- The audio comes from the CM5's PWM audio outputs (`AUDIO_OUT_L`, `AUDIO_OUT_R`).

## Networking

- One Gigabit Ethernet port (1 Gbps).
- The Ethernet connector is a low-profile, shielded 8P8C (RJ45) connector, to keep the overall thickness low. If no low-profile connector with integrated magnetics is available, a separate magnetics component can be used. The connector must be as low as in the reference 3D model, but it can be longer in depth.
- Wi-Fi and Bluetooth through the CM5 wireless module and the external antenna.

## USB

| Port                   | Location | Specification          | Power output        |
| ---------------------- | -------- | ---------------------- | ------------------- |
| USB-C                  | Side     | USB 3.1 Gen 1 (5 Gbps) | 10 W (2 A at 5 V)   |
| USB-C                  | Back     | USB 3.1 Gen 1 (5 Gbps) | 2.5 W (500 mA at 5 V) |
| USB-A                  | Back     | USB 2.0                | 2.5 W (500 mA at 5 V) |
| Internal eMMC flashing | Internal | USB connector for flashing the eMMC, see below | – |

- **Overcurrent protection:** the power output of every external USB port is protected by a discrete current protection circuit, with enough margin over the port's power rating. PTC fuses are not used.
- **eMMC flashing port:** placed close to the edge of the PCB, but not accessible from outside. Authorized personnel reach it after removing the top cover.

## Storage

- **eMMC:** 64 GB on the CM5, used as the boot device.
- **NVMe:** one M.2 M-key connector for a full-size NVMe drive.
- **microSD card slot:** the connector and its components are on the PCB but not populated (DNP) in the first assembly. The slot is reachable only from inside the enclosure. Its purposes:
  1. Firmware recovery: updating a device directly from an SD card is easier and safer.
  2. Data transfer, such as logs.
  3. A possible cheaper variant later, with a CM5 Lite (no eMMC) booting from the SD card. This only needs a new assembly variant of the same PCB.

  The microSD slot and the eMMC share the CM5's SDIO interface, so they are mutually exclusive: the SD card works only with a CM5 Lite.

## Power

- **Input:** DC barrel jack, 12 V nominal, accepting 9–16 V. The product ships with a 12 V adapter.
- **Barrel jack:** 5.5 × 2.1 mm, the most common plug of 12 V and 24 V adapters:
  - outer diameter 5.5 mm, center pin 2.1 mm
  - center positive
  - current rating sized for the power budget at the minimum input voltage (9 V)
- **Power budget:** calculated at full CPU load, with every USB port at its full power rating: 10 W for the side USB-C port and 2.5 W each for the back USB-C and USB-A ports (15 W in total).
- **Safety margin:** the power stage is designed with at least 25% margin over the calculated power budget.
- **Power button:** connected to the CM5's power button pin (`PWR_BUT`), the one close to the bottom left corner.

## RTC Backup

- The RTC keeps the date and time for at least 5 years without external power.
- A CR2032 coin cell is used, as it is widely available. A supercapacitor is not used.

## Security

- TPM 2.0: Infineon OPTIGA TPM SLB 9672, connected over SPI at 33 MHz.

## Indicators and Controls

- **LEDs:** a red and a green LED, exactly as used on the Raspberry Pi 5B, visible from outside the enclosure.
- **Power button:** see [Power](#power).
- **Reset button:** connected to a CM5 GPIO. It is pressed with a needle through a small circular hole in the case. The same button type as the power button is used, placed with a margin so that it sits fully inside the enclosure, as shown in the 3D model.

## Debug

- A serial debug connector, the same as on the Raspberry Pi 5B, reachable only from inside the enclosure.

## Thermal and Environmental

- **Cooling:** passive heatsink with enough dissipation area.
- **Component temperature range:** electronic components are selected for −25 °C to +85 °C. The CM5 itself is rated −20 °C to +85 °C, so it limits the low end of the product's range.
- **Ambient temperature rating:** to be defined. The target is stable performance at maximum load up to 60 °C ambient, to be verified by thermal testing. The CM5 throttles its CPU to stay below 85 °C, so a higher ambient temperature reduces performance.

## Enclosure and Mounting

- **Air circulation:** the case has enough air circulation to dissipate the heat without deforming.
- **Orientation:** the device works both horizontally and vertically, as customers use it both ways.
- **Design:** the enclosure is designed together with Screenly's industrial designer.
- **Mounting:** one mounting accessory provides all options:
  - VESA mount, also used for wall mounting
  - DIN rail mount
  - Rubber pads for desk use

## Compliance

The design must be fully compliant with the following standards:

- IEC 62368-1
- CISPR 32
- CISPR 35
- IEC 61000-4-2, IEC 61000-4-4, IEC 61000-4-5, IEC 61000-4-6, IEC 61000-4-8, IEC 61000-4-11
- EN 62311

## Not Included

- **Digital inputs and outputs:** no digital I/O on the board, and no components for it.
- **External RTC chip:** the CM5's built-in RTC is used.
- **MIPI DSI and CSI:** the CM5's two MIPI ports are not used.
- **Composite video:** the CM5 has no composite video output (the CM4's `VDAC_COMP` pin is `VBUS_EN` on the CM5), so the audio jack carries audio only.

## Optional: Power over Ethernet

PoE is explored as an optional extension board. Some customers ask for it, but it is not a common request. The implementation and unit cost are to be defined.

## Block Diagram

```
                         ┌──────────────────────┐
DC barrel jack 9–28 V ──►│ DC-DC ──► 5 V        │
PoE board (optional) ───►│                      │
                         │                      │◄──► 2× USB-C, USB 3.1 Gen 1
Gigabit Ethernet ◄──────►│                      │◄──► 1× USB-A, USB 2.0
Red / green LEDs ◄───────│                      │◄──► Internal USB (eMMC flashing)
2× HDMI Type A ◄─────────│   Raspberry Pi CM5   │◄──► M.2 M-key NVMe
microSD slot (DNP) ◄────►│   wireless, 4 GB,    │◄──► SMA ◄── U.FL antenna
TPM 2.0 (SPI) ◄─────────►│   64 GB eMMC         │───► 3.5 mm jack: stereo audio (PWM)
Serial debug ◄──────────►│   built-in RTC       │◄─── RTC coin cell
Power / reset buttons ──►│                      │
                         └──────────────────────┘
```

## Open Items

- **Ambient temperature rating** of the product, such as 60 °C.
- **PoE extension board:** implementation and unit cost.
