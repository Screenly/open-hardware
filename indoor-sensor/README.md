# Indoor Air Quality Sensor

This is an open hardware indoor air quality sensor. It meassures the following:

* Temperature
* Humidity
* eCO2
* VOC

The goal was to create a cheap WiFi based sensor that leverages the [ESPHome](https://esphome.io/) platform. This sensor can either be used stand-alone, or integrated with home automation systems like [Home Assistant](https://www.home-assistant.io/).

In addition to being 'plug and play' with Home Assistant, the configuration below also exposes a Prometheus endpoint on `/metrics`, which allows you to "scrape" the metrics using any Prometheus compatible tool.

## ESP Home config file

In the commands below, we assume that you have written the file below as `bedroom.yaml`.

```yaml
---
esp32:
  board: esp32doit-devkit-v1
  framework:
    type: arduino

esphome:
  name: bedroom-sensor

wifi:
  ssid: "[redacted]"
  password: "[redacted]"

  # Enable fallback hotspot (captive portal) in case wifi connection fails
  ap:
    ssid: "Bedroom Sensor Fallback"
    password: "[redacted]"

captive_portal:

# Enable logging
logger:

i2c:
  sda: 21
  scl: 22

sensor:
  - platform: dht
    pin: 25
    model: DHT22
    temperature:
      name: "Bedoom Temperature"
    humidity:
      name: "Bedroom Humidity"
    update_interval: 60s
  - platform: ccs811
    baseline: 0x8489
    eco2:
      name: "Bedroom eCO2 Value"
    tvoc:
      name: "Bedroom Total Volatile Organic Compound"
    address: 0x5A
    update_interval: 60s
# Enable Home Assistant API
api:
web_server:
prometheus:
ota:
  - platform: esphome
    password: ""
```

## Intial flash

This assumes the ESP32 is connected to your local computer on `/dev/ttyUSB0`. Adjust accordingly.

```bash
docker run --rm --privileged \
    -v "${PWD}":/config \
    --device=/dev/ttyUSB0 \
    -it ghcr.io/esphome/esphome \
    run bedroom.yaml
```

For more information, see the ESPHome [Getting Started Guide](https://esphome.io/guides/getting_started_command_line.html).

## Deploying OTA

One of the neat things with the ESPHome platform is that you can update subsequant update Over The Air (OTA). To do this, you just run:

```bash
docker run \
    --rm -v "${PWD}":/config \
    --add-host="bedroom.local:a.b.c.d" \
    -it ghcr.io/esphome/esphome run bedroom.yaml
```

