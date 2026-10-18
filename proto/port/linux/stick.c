/* MTP-F26 Team C - the USB stick as a raw block device behind usbm_disk_t. See stick.h. */
#define _GNU_SOURCE
#include "stick.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

#define BOUNCE_SECTORS 128u   /* 64 KB per transfer */

int stick_present(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 && (S_ISBLK(st.st_mode) || (S_ISREG(st.st_mode) && st.st_size >= 512));
}

static int s_ready(void *ctx)
{
    stick_t *s = ctx;
    return s->fd >= 0 && stick_present(s->path);   /* pulled out: the device node goes away */
}

static int s_wp(void *ctx) { return ((stick_t *)ctx)->ro; }

static int s_read(void *ctx, uint8_t *buf, uint32_t lba, uint32_t count)
{
    stick_t *s = ctx;
    if ((uint64_t)lba + count > s->sectors)
        return -1;
    while (count) {
        uint32_t n = count < BOUNCE_SECTORS ? count : BOUNCE_SECTORS;
        size_t bytes = (size_t)n * 512u;
        if (pread(s->fd, s->bounce, bytes, (off_t)lba * 512) != (ssize_t)bytes)
            return -1;
        memcpy(buf, s->bounce, bytes);
        buf += bytes;
        lba += n;
        count -= n;
    }
    return 0;
}

static int s_write(void *ctx, const uint8_t *buf, uint32_t lba, uint32_t count)
{
    stick_t *s = ctx;
    if (s->ro || (uint64_t)lba + count > s->sectors)
        return -1;
    while (count) {
        uint32_t n = count < BOUNCE_SECTORS ? count : BOUNCE_SECTORS;
        size_t bytes = (size_t)n * 512u;
        memcpy(s->bounce, buf, bytes);
        if (pwrite(s->fd, s->bounce, bytes, (off_t)lba * 512) != (ssize_t)bytes)
            return -1;
        buf += bytes;
        lba += n;
        count -= n;
    }
    return 0;
}

static int s_sync(void *ctx)
{
    stick_t *s = ctx;
    if (s->ro)
        return 0;
    if (fdatasync(s->fd))   /* on a block device this also flushes the stick's own cache */
        return -1;
    if (!s->direct)
        posix_fadvise(s->fd, 0, 0, POSIX_FADV_DONTNEED);   /* the read-back must come from the stick */
    return 0;
}

static uint32_t s_count(void *ctx)
{
    stick_t *s = ctx;
    return s->sectors > 0xFFFFFFFFu ? 0xFFFFFFFFu : (uint32_t)s->sectors;
}

static int open_mode(const char *path, int flags, int *direct)
{
    int fd = open(path, flags | O_DIRECT | O_CLOEXEC);
    *direct = fd >= 0;
    if (fd < 0)
        fd = open(path, flags | O_CLOEXEC);   /* tmpfs and some file systems refuse O_DIRECT */
    return fd;
}

int stick_open(stick_t *s, const char *path, usbm_disk_t *d)
{
    memset(s, 0, sizeof *s);
    s->fd = -1;
    snprintf(s->path, sizeof s->path, "%s", path);
    s->fd = open_mode(path, O_RDWR, &s->direct);
    if (s->fd < 0 && (errno == EROFS || errno == EACCES || errno == EPERM)) {
        s->fd = open_mode(path, O_RDONLY, &s->direct);
        s->ro = 1;
    }
    if (s->fd < 0)
        return -1;
    struct stat st;
    if (fstat(s->fd, &st)) {
        stick_close(s);
        return -1;
    }
    if (S_ISBLK(st.st_mode)) {
        uint64_t bytes = 0;
        int ro = 0;
        if (ioctl(s->fd, BLKGETSIZE64, &bytes) == 0)
            s->sectors = bytes / 512u;
        if (ioctl(s->fd, BLKROGET, &ro) == 0 && ro)
            s->ro = 1;   /* the lock switch, as the kernel sees it */
    } else {
        s->sectors = (uint64_t)st.st_size / 512u;
    }
    if (!s->sectors || posix_memalign((void **)&s->bounce, 4096, BOUNCE_SECTORS * 512u)) {
        stick_close(s);
        return -1;
    }
    memset(d, 0, sizeof *d);
    d->ctx = s;
    d->ready = s_ready;
    d->read = s_read;
    d->write = s_write;
    d->sync = s_sync;
    d->sector_count = s_count;
    d->write_protected = s_wp;
    return 0;
}

void stick_close(stick_t *s)
{
    if (s->fd >= 0)
        close(s->fd);
    s->fd = -1;
    free(s->bounce);
    s->bounce = NULL;
}
