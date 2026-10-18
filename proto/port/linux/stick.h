/* MTP-F26 Team C - the USB stick as a raw block device behind usbm_disk_t (Linux node).
 *
 * The Pi's USB host port shows a stick as /dev/sda; Pi OS Lite does not automount it, and our FatFs code
 * (src/usb_msc.c) reads the partition table and the FAT/exFAT volume itself, so the tested code runs as it
 * is. The same backend opens a disk image file, which the e2e tests use. Reads and writes go through an
 * aligned bounce buffer with O_DIRECT when the device allows it, so the read-back CRC after a save reads
 * the stick, not the page cache; otherwise the cache is dropped at every sync. A stick whose lock switch is
 * on opens read-only and reports write_protected (usb_msc answers USBM_READ_ONLY).
 */
#ifndef STICK_H
#define STICK_H

#include <stdint.h>

#include "usb_msc.h"

typedef struct {
    char path[200];
    int fd, direct, ro;
    uint64_t sectors;
    uint8_t *bounce;
} stick_t;

/* 1 if something is at path (the device node exists, or the image file). */
int stick_present(const char *path);
/* Opens path and fills *d. Returns 0, or -1 (nothing there / cannot open). */
int stick_open(stick_t *s, const char *path, usbm_disk_t *d);
void stick_close(stick_t *s);

#endif /* STICK_H */
