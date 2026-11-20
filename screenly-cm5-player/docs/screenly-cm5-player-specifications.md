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
- The audio comes from an I2S audio DAC (TI PCM5102A) connected to the CM5's I2S pins.

## Networking

- One Gigabit Ethernet port (1 Gbps).
- The Ethernet connector is a low-profile, shielded 8P8C (RJ45) connector, to keep the overall thickness low. If no low-profile connector with integrated magnetics is available, a separate magnetics component can be used. The connector must be as low as in the reference 3D model, but it can be longer in depth.
- Wi-Fi and Bluetooth through the CM5 wireless module and the external antenna.

## USB

| Port                   | Location | Specification          | Power output        |
| ---------------------- | -------- | ---------------------- | ------------------- |
| USB-A                  | Side     | USB 3.0 (5 Gbps)       | 10 W (2 A at 5 V)   |
| USB-A                  | Back     | USB 3.0 (5 Gbps)       | 4.5 W (900 mA at 5 V) |
| USB-C                  | Back     | USB 2.0                | 2.5 W (500 mA at 5 V) |
| Internal eMMC flashing | Internal | USB connector for flashing the eMMC, see below | – |

- **Side USB-A power profile:** the 10 W rating covers short bursts only, about 100 ms at roughly 1% duty cycle. The expected average load is 100–300 mA, so a connector with a 1.8 A continuous contact rating is acceptable for this port.
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
- **Power budget:** calculated at full CPU load, with every USB port at its full power rating: 10 W for the side USB-A port, 4.5 W for the back USB-A port and 2.5 W for the back USB-C port (17 W in total).
- **Safety margin:** the power stage is designed with at least 15% margin over the calculated power budget.
- **Overcurrent protection of the input:** the board has no input fuse. The power adapter must be a limited power source (LPS) under IEC 62368-1, and the board relies on the adapter's own overcurrent protection.
- **Power button:** connected to the CM5's power button pin (`PWR_BUT`), the one close to the bottom left corner.

## RTC Backup

- The RTC keeps the date and time for at least 4 years without external power.
- A CR2032 coin cell is used, as it is widely available. A supercapacitor is not used.

## Security

- TPM 2.0: Infineon OPTIGA TPM SLB 9672, connected over SPI at 33 MHz.

## Indicators and Controls

- **LEDs:** a red and a green LED, exactly as used on the Raspberry Pi 5B, visible from outside the enclosure.
- **Power button:** see [Power](#power).
- **Reset button:** connected to a CM5 GPIO. It is pressed with a needle through a small circular hole in the case. The same button type as the power button is used, placed with a margin so that it sits fully inside the enclosure, as shown in the 3D model.

## Debug

- A serial debug connector, the same 3-pin connector type as on the Raspberry Pi 5B, reachable only from inside the enclosure.
- The connector is wired to the CM5's UART0 (GPIO14/GPIO15), not to the CM5's dedicated debug UART, which is available only on module test points. Firmware and bootloader messages therefore don't appear on it; see [Software Configuration](#software-configuration) for the Linux console.

## Software Configuration

Settings the board needs in the CM5 firmware and operating system configuration:

| Setting | Where | Why |
| ------- | ----- | --- |
| `PSU_MAX_CURRENT=5000` | Bootloader EEPROM configuration | The CM5's USB-C power negotiation pins (`CC1`, `CC2`) are not connected, because the board is powered from the DC jack. Without this setting the CM5 assumes a weaker supply, warns about it and limits the USB current. |
| `dtparam=uart0_console` | `config.txt` | Moves the Linux console to UART0 (GPIO14/GPIO15), where the serial debug connector is wired. |
| `dtoverlay=dwc2,dr_mode=host` | `config.txt` | Enables the CM5's USB 2.0 port, used by the back USB-C port. The CM5 datasheet requires this overlay for USB 2.0. |
| `POWER_OFF_ON_HALT=1` | Bootloader EEPROM configuration | After a shutdown (`sudo shutdown`/`halt` or the power button) the CM5's PMIC goes to standby with all its outputs off, including the CM5's 3.3 V output. The board then uses about 0.01 W instead of about 1–1.4 W, and the HDMI 5 V outputs, which are enabled from the CM5's 3.3 V output, switch off so a connected display can't feed its hot-plug signal back into the powered-down CM5. The power button still wakes the board. |
| `WAKE_ON_GPIO=0` | Bootloader EEPROM configuration | Required for `POWER_OFF_ON_HALT=1` to take effect. |

## Thermal and Environmental

- **Cooling:** passive heatsink with enough dissipation area.
- **Component temperature range:** electronic components are selected for −20 °C to +80 °C.
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

## CM4 Fallback

The board also works with a Raspberry Pi Compute Module 4 (CM4), as a fallback if the CM5 is not available. These features are accepted as lost with a CM4:

- **Both USB-A ports:** their USB 3.0 and USB 2.0 lines use CM5-only pins (the CM4's CAM0 and DSI0 pins), and their power is switched by the CM5's `VBUS_EN` pin (`VDAC_COMP` on the CM4).
- **RTC:** the CM4 has no RTC, so the coin cell has no function. The coin cell must not be fitted when a CM4 is used: the cell connects to pin 76, which the CM4 datasheet marks "Reserved – do not connect anything to this pin".
- **Power button:** the CM5's `PWR_BUT` pin is `RUN_PG` on the CM4, so pressing the button resets the CM4 immediately instead of starting a clean shutdown.
- **NVMe:** the M.2 power supply is enabled by the CM5's `PCIE_PWR_EN` pin, which is reserved on the CM4, so the M.2 slot gets no power.

The back USB-C port still works as a USB 2.0 port.

There is no separate CM4 assembly variant; the same assembly is used with either module. One more reserved CM4 pin stays connected: pin 104 (the CM5's `PCIE_DET_nWAKE`) goes to the M.2 connector's `PEWAKE#` pin. The CM4 datasheet marks pin 104 "Reserved – do not connect anything to this pin". The risk is low, because the M.2 slot has no power with a CM4 and the board has no pull-up on this line.

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
DC barrel jack 9–16 V ──►│ DC-DC ──► 5 V        │
PoE board (optional) ───►│                      │
                         │                      │◄──► 2× USB-A, USB 3.0
Gigabit Ethernet ◄──────►│                      │◄──► 1× USB-C, USB 2.0
Red / green LEDs ◄───────│                      │◄──► Internal USB (eMMC flashing)
2× HDMI Type A ◄─────────│   Raspberry Pi CM5   │◄──► M.2 M-key NVMe
microSD slot (DNP) ◄────►│   wireless, 4 GB,    │◄──► SMA ◄── U.FL antenna
TPM 2.0 (SPI) ◄─────────►│   64 GB eMMC         │───► 3.5 mm jack: stereo audio (I2S DAC)
Serial debug ◄──────────►│   built-in RTC       │◄─── RTC coin cell
Power / reset buttons ──►│                      │
                         └──────────────────────┘
```

## Open Items

- **Ambient temperature rating** of the product, such as 60 °C.
- **PoE extension board:** implementation and unit cost.
