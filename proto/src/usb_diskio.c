/* MTP-F26 Team C - FatFs disk I/O layer: routes FatFs's drive 0 to the registered usbm_disk_t. */
#include <stddef.h>

#include "ff.h"
#include "diskio.h"
#include "usb_msc.h"

static const usbm_disk_t *disk;

void usbm_set_disk(const usbm_disk_t *d) { disk = d; }

DSTATUS disk_status(BYTE pdrv)
{
    if (pdrv != 0 || !disk || !disk->ready(disk->ctx))
        return STA_NOINIT | STA_NODISK;
    return 0;
}

DSTATUS disk_initialize(BYTE pdrv) { return disk_status(pdrv); }

DRESULT disk_read(BYTE pdrv, BYTE *buff, LBA_t sector, UINT count)
{
    if (disk_status(pdrv))
        return RES_NOTRDY;
    return disk->read(disk->ctx, buff, (uint32_t)sector, (uint32_t)count) ? RES_ERROR : RES_OK;
}

DRESULT disk_write(BYTE pdrv, const BYTE *buff, LBA_t sector, UINT count)
{
    if (disk_status(pdrv))
        return RES_NOTRDY;
    return disk->write(disk->ctx, buff, (uint32_t)sector, (uint32_t)count) ? RES_ERROR : RES_OK;
}

DRESULT disk_ioctl(BYTE pdrv, BYTE cmd, void *buff)
{
    if (disk_status(pdrv))
        return RES_NOTRDY;
    switch (cmd) {
    case CTRL_SYNC:
        return disk->sync(disk->ctx) ? RES_ERROR : RES_OK;
    case GET_SECTOR_COUNT:
        *(LBA_t *)buff = (LBA_t)disk->sector_count(disk->ctx);
        return RES_OK;
    case GET_SECTOR_SIZE:
        *(WORD *)buff = 512;
        return RES_OK;
    case GET_BLOCK_SIZE:
        *(DWORD *)buff = 1;   /* erase block unknown: let f_mkfs (tests only) use its default alignment */
        return RES_OK;
    default:
        return RES_PARERR;
    }
}
