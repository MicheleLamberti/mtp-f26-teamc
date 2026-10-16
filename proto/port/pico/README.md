# Pico 2 port (work in progress)

Board glue for the Raspberry Pi Pico 2 (RP2350). **Not compiled here**: the radio team's machine has no
pico-sdk or ARM toolchain. Everything portable is host-tested in `proto/` (`make test`).

| File | What | Status |
|---|---|---|
| `usb_msc_pico.c` | `usbm_disk_t` over TinyUSB host MSC on the box's USB-A port (Pico-PIO-USB on GP12/GP13), 5 V switch on GP11, FAULT on GP10 | skeleton, untested |
| (to do) `radio_hal_pico.c` | `nrf24_hal_t`: SPI0 GP16/18/19, CSN GP17, CE GP20, IRQ GP21 | waits for the ET pin map |
| (to do) `proto_env_pico.c` | `proto_env_t`: `nrf24_send`, `time_us_64`, a hardware alarm | |
| (to do) `store_flash.c` | raw flash region for the file sent / received + progress record (4 KB sectors) | |

## How the USB stick flow uses `usb_msc` (`src/usb_msc.h`)

```c
usbm_pico_init();                                  // boot, after set_sys_clock_khz(120000, true)
// Setup (sender): copy the competition file into flash
if (usbm_pico_wait_stick(5000) && usbm_mount(&u) == USBM_OK &&
    usbm_find_input(&u, "NM_LOG.TXT", name, sizeof name, &size, &count) == USBM_OK)
    st = usbm_load(&u, name, FLASH_FILE_MAX, flash_sink, &store, &len, &crc);
usbm_unmount(&u); usbm_pico_power(false);
// After STOP (every box): received file + NM relay log back to a stick
st = usbm_save(&u, out_name, rx_len, flash_source, &store, &crc);   // writes .part, verifies, renames
st = usbm_save_buf(&u, "NM_LOG.TXT", (uint8_t *)log, log_len);     // nm_log_format()
```

`usbm_save` writes `<name>.part`, reads it back, compares CRC-32s and only then renames it, so the final
name never holds a truncated file even if the stick is pulled half-way. Output name and encoding wait on
Atenea Q9.

## Bench checklist (stage 1)

1. PIO-USB enumerates 3-4 different sticks (FAT32 and exFAT, 8-64 GB) at 120 MHz system clock.
2. Load the 1 MB file into flash: time it (target < 10 s) and compare the CRC-32 with the PC's.
3. Save 1 MB back, pull the stick, open it on a laptop: identical file, no `.part` left.
4. Pull the stick during a save: `usbm_save` returns an error within ~2 s, no final-name file appears.
5. Short the stick's VBUS through a resistor: FAULT goes low, firmware turns the 5 V off.
