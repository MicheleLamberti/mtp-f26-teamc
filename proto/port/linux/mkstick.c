/* MTP-F26 Team C - USB stick images for the Linux node's tests, through the node's own stick backend.
 *
 *   mkstick make IMG MB fat16|fat32|exfat [FILE...]   new image with FILEs in the root
 *   mkstick get IMG NAME OUT                          copy NAME out of the image
 *   mkstick ls IMG                                    list the root (name and size)
 *
 * On a Pi the same commands work on a real stick (IMG = /dev/sda) without mounting it.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "stick.h"
#include "usb_msc.h"

static int mem_sink(void *ctx, uint32_t off, const uint8_t *p, uint32_t n)
{
    memcpy((uint8_t *)ctx + off, p, n);
    return 0;
}

static uint8_t *slurp(const char *path, uint32_t *n)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *p = malloc(sz > 0 ? (size_t)sz : 1u);
    *n = p && fread(p, 1, (size_t)sz, f) == (size_t)sz ? (uint32_t)sz : 0u;
    fclose(f);
    return p;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: mkstick make IMG MB fat16|fat32|exfat [FILE...] | get IMG NAME OUT | ls IMG\n");
        return 2;
    }
    const char *cmd = argv[1], *img = argv[2];
    if (!strcmp(cmd, "make")) {
        if (argc < 5)
            return 2;
        unsigned mb = (unsigned)atoi(argv[3]);
        int fd = open(img, O_RDWR | O_CREAT | O_TRUNC, 0644);
        if (fd < 0 || ftruncate(fd, (off_t)mb << 20)) {
            perror(img);
            return 1;
        }
        close(fd);
    }
    stick_t s;
    usbm_disk_t d;
    if (stick_open(&s, img, &d)) {
        perror(img);
        return 1;
    }
    usbm_set_disk(&d);
    usbm_t *u = calloc(1, sizeof *u);
    int rc = 0;
    if (!strcmp(cmd, "make")) {
        static uint8_t work[4096];
        BYTE fmt = !strcmp(argv[4], "exfat") ? FM_EXFAT : !strcmp(argv[4], "fat32") ? FM_FAT32 : FM_FAT;
        MKFS_PARM opt = {fmt, 1, 0, 0, 0};
        if (f_mkfs("", &opt, work, sizeof work) != FR_OK || usbm_mount(u) != USBM_OK) {
            fprintf(stderr, "mkfs failed\n");
            return 1;
        }
        for (int i = 5; i < argc; i++) {
            uint32_t n = 0;
            uint8_t *p = slurp(argv[i], &n);
            const char *base = strrchr(argv[i], '/') ? strrchr(argv[i], '/') + 1 : argv[i];
            usbm_status_t r = p ? usbm_save_buf(u, base, p, n) : USBM_IO;
            printf("%s: %u B %s\n", base, n, usbm_strerror(r));
            rc |= r != USBM_OK;
            free(p);
        }
    } else if (!strcmp(cmd, "get") && argc == 5) {
        uint8_t *buf = malloc(64u << 20);
        uint32_t len = 0, crc = 0;
        usbm_status_t r = usbm_mount(u);
        if (r == USBM_OK)
            r = usbm_load(u, argv[3], 64u << 20, mem_sink, buf, &len, &crc);
        if (r != USBM_OK) {
            fprintf(stderr, "%s: %s\n", argv[3], usbm_strerror(r));
            rc = 1;
        } else {
            FILE *f = fopen(argv[4], "wb");
            rc = !f || fwrite(buf, 1, len, f) != len;
            if (f)
                fclose(f);
        }
        free(buf);
    } else if (!strcmp(cmd, "ls")) {
        if (usbm_mount(u) != USBM_OK)
            return 1;
        DIR dir;
        FILINFO fi;
        if (f_opendir(&dir, "/") == FR_OK) {
            while (f_readdir(&dir, &fi) == FR_OK && fi.fname[0])
                printf("%10llu  %s\n", (unsigned long long)fi.fsize, fi.fname);
            f_closedir(&dir);
        }
    } else {
        rc = 2;
    }
    if (u->mounted)
        usbm_unmount(u);
    stick_close(&s);
    free(u);
    return rc;
}
