/* MTP-F26 Team C - usb_msc backend for the Raspberry Pi Pico 2: the box's USB-A port as a USB host.
 *
 * STATUS: SKELETON, NOT COMPILED OR TESTED. Written against pico-sdk 2.x with its bundled TinyUSB
 * (host MSC class) and Pico-PIO-USB; nothing of that is installed on the radio team's machine. Check
 * every call against the SDK version you build with, then test on the bench with 3-4 different
 * sticks (stage 1 of the hardware plan). The portable part (src/usb_msc.c + FatFs) is host-tested.
 *
 * Hardware (hw/KICAD_SESSION_PROMPT.md): USB-A D+ = GP12, D- = GP13 (PIO-USB needs D- = D+ + 1),
 * 5 V boost + current-limited switch enable = GP11, switch FAULT = GP10 (active low).
 *
 * Build notes:
 *  - tusb_config.h: CFG_TUH_ENABLED 1, CFG_TUH_RPI_PIO_USB 1, CFG_TUH_MSC 1, CFG_TUH_DEVICE_MAX 1,
 *    BOARD_TUH_RHPORT 1 (the PIO port; the native port stays free for programming and logs).
 *  - PIO-USB needs the system clock to be a multiple of 12 MHz: the RP2350 boots at 150 MHz, so call
 *    set_sys_clock_khz(120000, true) (or 240000) before usbm_pico_init(). Check that the radio's SPI
 *    divider and the UART baud still come out right at that clock.
 *  - Run tuh_task() from core 0's main loop only (the proposal puts USB, flash and codec on core 0).
 *  - Flash writes stall both cores: the radio loop on core 1 must run from RAM (__not_in_flash_func).
 *  - Flash ERASES (45-400 ms per 4 KB) also stall PIO-USB's 1 ms SOF interrupt, and a stick suspends after
 *    3 ms without SOF: erase the whole file region BEFORE mounting the stick, then only program pages
 *    (the usbm_load sink) while it is attached.
 *  - PIO_USB_DEFAULT_CONFIG uses DMA channel 0 and PIO0/PIO1: call usbm_pico_init() before anything that
 *    claims DMA channels (or set cfg.tx_ch to a free one), and keep the radio's SPI off PIO.
 *  - Stack: pico-sdk's default is 2 KB per core; FatFs with exFAT + LFN, vsnprintf and the log need more:
 *    set PICO_STACK_SIZE (and PICO_CORE1_STACK_SIZE) to 8 KB, keep usbm_t and big buffers static.
 */
#include <stdbool.h>
#include <stdint.h>

#include "hardware/gpio.h"
#include "pico/stdlib.h"
#include "pio_usb.h"
#include "tusb.h"

#include "usb_msc.h"

#define PIN_USB_DP 12u
#define PIN_USB_5V_EN 11u
#define PIN_USB_5V_FAULT 10u
#define MSC_TIMEOUT_US 2000000u   /* one READ10/WRITE10 must finish within 2 s */

static volatile uint8_t msc_addr;      /* 0 = no stick mounted */
static volatile bool xfer_busy, xfer_ok;

/* --- TinyUSB host MSC callbacks --------------------------------------------------------------- */

void tuh_msc_mount_cb(uint8_t dev_addr) { msc_addr = dev_addr; }

void tuh_msc_umount_cb(uint8_t dev_addr)
{
    if (msc_addr == dev_addr)
        msc_addr = 0;
}

static bool xfer_done(uint8_t dev_addr, tuh_msc_complete_data_t const *cb)
{
    (void)dev_addr;
    xfer_ok = cb->csw->status == MSC_CSW_STATUS_PASSED;
    xfer_busy = false;
    return true;
}

/* A timed-out READ10/WRITE10 is still in flight with FatFs's buffer: a late completion would write into a
 * buffer FatFs has already reused, and the MSC driver stays busy. So power-cycle the port: drop the device,
 * cut the 5 V, and let the stick enumerate again; the caller remounts (usbm_mount) and retries. */
static void reset_port(void)
{
    msc_addr = 0;
    xfer_busy = false;
    gpio_put(PIN_USB_5V_EN, 0);
    uint64_t t0 = time_us_64();
    while (time_us_64() - t0 < 200000u)   /* let VBUS fall and TinyUSB see the disconnect */
        tuh_task();
    gpio_put(PIN_USB_5V_EN, 1);
}

/* Run TinyUSB until the transfer completes, the stick goes away or the timeout expires. */
static int wait_xfer(void)
{
    uint64_t t0 = time_us_64();
    while (xfer_busy) {
        tuh_task();
        if (!msc_addr)
            return -1;
        if (time_us_64() - t0 > MSC_TIMEOUT_US) {
            reset_port();
            return -1;
        }
    }
    return xfer_ok ? 0 : -1;
}

/* --- usbm_disk_t over TinyUSB MSC (LUN 0, 512-byte blocks) -------------------------------------- */

static int pico_ready(void *ctx)
{
    (void)ctx;
    tuh_task();
    return msc_addr && tuh_msc_mounted(msc_addr) && tuh_msc_get_block_size(msc_addr, 0) == 512;
}

static int pico_read(void *ctx, uint8_t *buf, uint32_t lba, uint32_t count)
{
    (void)ctx;
    xfer_busy = true;
    if (!tuh_msc_read10(msc_addr, 0, buf, lba, (uint16_t)count, xfer_done, 0)) {
        xfer_busy = false;
        return -1;
    }
    return wait_xfer();
}

static int pico_write(void *ctx, const uint8_t *buf, uint32_t lba, uint32_t count)
{
    (void)ctx;
    xfer_busy = true;
    if (!tuh_msc_write10(msc_addr, 0, buf, lba, (uint16_t)count, xfer_done, 0)) {
        xfer_busy = false;
        return -1;
    }
    return wait_xfer();
}

static int pico_sync(void *ctx)
{
    (void)ctx;
    return 0;   /* WRITE10 completes only after the stick accepted the data */
}

static uint32_t pico_count(void *ctx)
{
    (void)ctx;
    return msc_addr ? tuh_msc_get_block_count(msc_addr, 0) : 0;
}

static const usbm_disk_t pico_disk = {NULL, pico_ready, pico_read, pico_write, pico_sync, pico_count};

/* --- public ------------------------------------------------------------------------------------ */

/* Once at boot (after set_sys_clock_khz). The 5 V stays off until usbm_pico_power(true). */
void usbm_pico_init(void)
{
    gpio_init(PIN_USB_5V_EN);
    gpio_set_dir(PIN_USB_5V_EN, GPIO_OUT);
    gpio_put(PIN_USB_5V_EN, 0);
    gpio_init(PIN_USB_5V_FAULT);
    gpio_set_dir(PIN_USB_5V_FAULT, GPIO_IN);
    gpio_pull_up(PIN_USB_5V_FAULT);

    pio_usb_configuration_t cfg = PIO_USB_DEFAULT_CONFIG;
    cfg.pin_dp = PIN_USB_DP;
    tuh_configure(BOARD_TUH_RHPORT, TUH_CFGID_RPI_PIO_USB_CONFIGURATION, &cfg);
    tuh_init(BOARD_TUH_RHPORT);
    usbm_set_disk(&pico_disk);
}

/* 5 V to the stick only while loading or saving (saves energy, protects against a shorted stick). */
void usbm_pico_power(bool on) { gpio_put(PIN_USB_5V_EN, on); }

/* true while the current-limited switch reports an over-current. */
bool usbm_pico_fault(void) { return !gpio_get(PIN_USB_5V_FAULT); }

/* Power the port and wait up to timeout_ms for a stick to enumerate. */
bool usbm_pico_wait_stick(uint32_t timeout_ms)
{
    usbm_pico_power(true);
    uint64_t t0 = time_us_64();
    while (!pico_ready(NULL)) {
        if (usbm_pico_fault() || time_us_64() - t0 > (uint64_t)timeout_ms * 1000u)
            return false;
    }
    return true;
}
