/* MTP-F26 Team C - radio backend for the Linux node (Raspberry Pi 3, D-H1).
 *
 * Two backends behind one small vtable:
 *   - phy_nrf24: the E01-ML01SP4 through radio/fw/nrf24.c and the Linux HAL (spidev + GPIO uAPI);
 *   - phy_udp:   an emulated radio over UDP on 127.0.0.1, so whole nodes run against each other on a PC
 *                (port/linux/e2e.sh): airtime, half-duplex deafness, channels, random loss and busy CCAs.
 * Times are CLOCK_MONOTONIC microseconds (64-bit), the clock the radio layer hops on.
 */
#ifndef PHY_H
#define PHY_H

#include <stdint.h>

#include "nrf24.h"

typedef struct {
    void *ctx;
    const nrf24_profile_t *profile;
    int (*set_channel)(void *ctx, uint8_t ch);   /* 0 = ok */
    void (*start_rx)(void *ctx);
    int (*cca)(void *ctx);                       /* lbt profiles: 1 = clear; leaves the radio in RX */
    /* Blocking send of one frame (PLL settling + airtime). 0 = sent, 1 = refused by LBT (needs a CCA),
     * -1 = failed. Leaves the radio in standby: call start_rx to listen again. */
    int (*send)(void *ctx, const uint8_t *f, uint8_t len);
    /* Wait until deadline_us for one received frame. 1 = frame: body, length, the time its last bit
     * arrived (t_end_us) and the RPD bit; 0 = deadline reached. */
    int (*recv)(void *ctx, uint64_t deadline_us, uint8_t *f, uint8_t *len, uint64_t *t_end_us, uint8_t *rpd);
    void (*close)(void *ctx);
} phy_t;

uint64_t phy_now_us(void);
/* Sleep until t_us: nanosleep for the bulk, busy-wait the last 200 us. */
void phy_sleep_until(uint64_t t_us);

/* Backend options parsed from the node's command line. */
typedef struct {
    const char *spidev, *gpiochip;
    uint32_t spi_hz;
    unsigned ce_gpio;
    int irq_gpio;
} phy_nrf24_opts_t;

/* "udp:<my port>:<peer port>[,<peer port>...]", loss = share of frames lost per link,
 * busy = share of CCAs that find the channel busy, seed for both. */
typedef struct {
    const char *spec;
    double loss, busy;
    uint32_t seed;
} phy_udp_opts_t;

int phy_nrf24_open(phy_t *phy, const phy_nrf24_opts_t *o, const nrf24_profile_t *profile, char *err, unsigned errlen);
int phy_udp_open(phy_t *phy, const phy_udp_opts_t *o, const nrf24_profile_t *profile, char *err, unsigned errlen);

#endif /* PHY_H */
