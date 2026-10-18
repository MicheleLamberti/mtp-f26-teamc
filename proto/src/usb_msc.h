/* MTP-F26 Team C - USB stick file I/O (the usb_msc module of the protocol proposal).
 *
 * The rules: each device must be "capable of reading/writing a file from/to memory device (USB)". At
 * setup the sender copies the .txt from the stick into flash; after STOP every box writes what it
 * received (and the NM relay log) back to a stick, within 3 minutes. The stick plugs into the box's
 * USB-A port: on the Raspberry Pi 3 a native host port, the stick read as a raw block device
 * (port/linux/stick.c, no automount). (The Pico 2 plan used TinyUSB + Pico-PIO-USB: in git history.)
 *
 * Sticks from any computer: FAT12/16/32 and exFAT, MBR (Windows, most factory sticks) or GPT (macOS Disk
 * Utility) partition tables, UTF-8 file names. NTFS, APFS and HFS+ are not readable: bring FAT32/exFAT sticks.
 *
 * This file is the portable half: FAT/exFAT through ChaN's FatFs (third_party/fatfs, R0.15a), the
 * input-file choice, chunked transfers to/from a sink/source (the flash store on the Pico, a buffer in
 * the tests) and a read-back CRC check after every write. The block device is a small vtable
 * (usbm_disk_t), so the same code runs against a RAM disk on the PC.
 *
 * Not thread-safe: run it on one core (core 0 in the proposal), never while the radio loop writes flash.
 */
#ifndef USB_MSC_H
#define USB_MSC_H

#include <stddef.h>
#include <stdint.h>

#include "ff.h"

#define USBM_CHUNK 4096u   /* transfer unit = one RP2350 flash sector */

/* Block device behind FatFs. 512-byte sectors (FF_MAX_SS); 0 = success for the int functions. */
typedef struct {
    void *ctx;
    int (*ready)(void *ctx);          /* 1 = a stick is attached and answers */
    int (*read)(void *ctx, uint8_t *buf, uint32_t lba, uint32_t count);
    int (*write)(void *ctx, const uint8_t *buf, uint32_t lba, uint32_t count);
    int (*sync)(void *ctx);
    uint32_t (*sector_count)(void *ctx);
    int (*write_protected)(void *ctx);   /* optional (may be NULL): 1 = the stick's lock switch is on */
} usbm_disk_t;

/* Register the device (once, before usbm_mount). */
void usbm_set_disk(const usbm_disk_t *disk);

typedef enum {
    USBM_OK = 0,
    USBM_NO_MEDIA,   /* nothing plugged in, or it does not answer */
    USBM_NO_FS,      /* no FAT/exFAT volume on it */
    USBM_NO_FILE,    /* no .txt in the root directory */
    USBM_TOO_BIG,    /* the file is larger than the caller's limit */
    USBM_FULL,       /* the stick is full */
    USBM_IO,         /* read/write error, or the sink/source failed */
    USBM_VERIFY,     /* read-back CRC differs from what we wrote */
    USBM_READ_ONLY,  /* the stick is write-protected */
} usbm_status_t;

const char *usbm_strerror(usbm_status_t st);

/* Stream callbacks: off is the byte offset in the file, n <= USBM_CHUNK. Return 0 on success. */
typedef int (*usbm_sink_fn)(void *ctx, uint32_t off, const uint8_t *p, uint32_t n);
typedef int (*usbm_source_fn)(void *ctx, uint32_t off, uint8_t *p, uint32_t n);

typedef struct {
    FATFS fs;
    FIL fil;
    int mounted;
    uint8_t buf[USBM_CHUNK];
    char tmp[FF_MAX_LFN + 1];   /* "<name>.part" during usbm_save (kept off the 2 KB Pico stack) */
} usbm_t;

usbm_status_t usbm_mount(usbm_t *u);
void usbm_unmount(usbm_t *u);

/* The input file: the largest *.txt in the root, skipping directories, hidden/system files, macOS
 * "._" shadow files and the name in `skip` (our own log; may be NULL). `count` = .txt files seen. */
usbm_status_t usbm_find_input(usbm_t *u, const char *skip, char *name, size_t cap, uint32_t *size,
                              uint32_t *count);

/* Read `name` into the sink in USBM_CHUNK pieces. Fails with USBM_TOO_BIG above max_len. */
usbm_status_t usbm_load(usbm_t *u, const char *name, uint32_t max_len, usbm_sink_fn sink, void *ctx,
                        uint32_t *len, uint32_t *crc32);

/* Write `len` bytes from the source as `name` (replacing it), close it, then read it back and compare
 * CRC-32s. *crc32 = CRC of the data written. */
usbm_status_t usbm_save(usbm_t *u, const char *name, uint32_t len, usbm_source_fn source, void *ctx,
                        uint32_t *crc32);
usbm_status_t usbm_save_buf(usbm_t *u, const char *name, const uint8_t *data, uint32_t len);

/* CRC-32 (IEEE, as zlib/miniz): crc = usbm_crc32(0, p, n), then feed the result back in for more data. */
uint32_t usbm_crc32(uint32_t crc, const uint8_t *p, uint32_t n);

#endif /* USB_MSC_H */
