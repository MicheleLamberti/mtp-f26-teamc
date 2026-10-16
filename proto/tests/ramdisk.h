/* MTP-F26 Team C - RAM disk behind usbm_disk_t, for the host tests of usb_msc. */
#ifndef RAMDISK_H
#define RAMDISK_H

#include <stdint.h>

#include "usb_msc.h"

typedef struct {
    uint8_t *img;
    uint32_t sectors;
    int present;            /* 0 = "stick unplugged" */
    int32_t fail_after;     /* < 0: never; else writes fail once this many more sectors were written */
    uint32_t writes, reads;
} ramdisk_t;

int ramdisk_init(ramdisk_t *r, uint32_t sectors);
void ramdisk_free(ramdisk_t *r);
void ramdisk_bind(ramdisk_t *r, usbm_disk_t *d);
int ramdisk_load(ramdisk_t *r, const char *path);   /* whole image from a file (size sets sectors) */
int ramdisk_save(const ramdisk_t *r, const char *path);

#endif /* RAMDISK_H */
