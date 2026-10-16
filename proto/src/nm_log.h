/* MTP-F26 Team C - Network Mode relay log.
 *
 * The rules make a team an NM winner by "delivering a copy of the NM-file from at least one of their
 * node devices". The copy itself is the proof; this log is supporting evidence written next to it on
 * the USB stick: which file we hold (file_id, CRC-32), when its chunks first reached us, and that the
 * node rebroadcast it (frames and broadcast times). Plain ASCII with CRLF line ends, so it opens in
 * Notepad. Built from nm_t (nm_gossip.h); no heap, no clock of its own.
 */
#ifndef NM_LOG_H
#define NM_LOG_H

#include <stddef.h>
#include <stdint.h>

#include "nm_gossip.h"

#define NM_LOG_MAX 3072u  /* worst case with 64 chunks fits comfortably */

typedef struct {
    const char *team;       /* "Team C" */
    const char *box;        /* label on the box, e.g. "C1" (or the flash unique ID) */
    const char *firmware;   /* build string */
    const char *file_name;  /* name of the NM-file copy written next to the log ("" if none) */
} nm_log_info_t;

/* CRC-32 (IEEE 802.3, as zlib/miniz crc32), so the log can be checked against the original file. */
uint32_t nm_log_crc32(const uint8_t *p, uint32_t len);

/* Writes the log text into buf (NUL-terminated). Returns its length, or 0 if cap is too small. */
size_t nm_log_format(const nm_t *n, const nm_log_info_t *info, char *buf, size_t cap);

#endif /* NM_LOG_H */
