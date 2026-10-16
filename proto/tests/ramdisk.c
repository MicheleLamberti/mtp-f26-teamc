/* MTP-F26 Team C - RAM disk for the usb_msc host tests. See ramdisk.h. */
#include "ramdisk.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int ramdisk_init(ramdisk_t *r, uint32_t sectors)
{
    memset(r, 0, sizeof *r);
    r->img = calloc(sectors, 512u);
    r->sectors = sectors;
    r->present = 1;
    r->fail_after = -1;
    return r->img ? 0 : -1;
}

void ramdisk_free(ramdisk_t *r)
{
    free(r->img);
    r->img = NULL;
}

static int rd_ready(void *ctx) { return ((ramdisk_t *)ctx)->present; }

static int rd_read(void *ctx, uint8_t *buf, uint32_t lba, uint32_t count)
{
    ramdisk_t *r = ctx;
    lba += r->offset;
    if (lba + count > r->sectors)
        return -1;
    memcpy(buf, r->img + (size_t)lba * 512u, (size_t)count * 512u);
    r->reads += count;
    return 0;
}

static int rd_write(void *ctx, const uint8_t *buf, uint32_t lba, uint32_t count)
{
    ramdisk_t *r = ctx;
    lba += r->offset;
    if (lba + count > r->sectors)
        return -1;
    if (r->fail_after >= 0) {
        if ((int32_t)count > r->fail_after)
            return -1;
        r->fail_after -= (int32_t)count;
    }
    memcpy(r->img + (size_t)lba * 512u, buf, (size_t)count * 512u);
    r->writes += count;
    return 0;
}

static int rd_sync(void *ctx)
{
    (void)ctx;
    return 0;
}

static uint32_t rd_count(void *ctx) { return ((ramdisk_t *)ctx)->sectors - ((ramdisk_t *)ctx)->offset; }

void ramdisk_bind(ramdisk_t *r, usbm_disk_t *d)
{
    d->ctx = r;
    d->ready = rd_ready;
    d->read = rd_read;
    d->write = rd_write;
    d->sync = rd_sync;
    d->sector_count = rd_count;
}

int ramdisk_load(ramdisk_t *r, const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return -1;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n <= 0 || n % 512 || ramdisk_init(r, (uint32_t)(n / 512))) {
        fclose(f);
        return -1;
    }
    size_t got = fread(r->img, 1, (size_t)n, f);
    fclose(f);
    return got == (size_t)n ? 0 : -1;
}

int ramdisk_save(const ramdisk_t *r, const char *path)
{
    FILE *f = fopen(path, "wb");
    if (!f)
        return -1;
    size_t n = (size_t)r->sectors * 512u, put = fwrite(r->img, 1, n, f);
    return fclose(f) == 0 && put == n ? 0 : -1;
}
