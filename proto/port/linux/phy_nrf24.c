/* MTP-F26 Team C - radio backend on the real nRF24 (E01-ML01SP4) through the Linux HAL. See phy.h. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "nrf24_hal_linux.h"
#include "phy.h"

typedef struct {
    nrf24_linux_t lx;
    nrf24_hal_t hal;
    nrf24_t dev;
    uint64_t edge_us;   /* last RX IRQ edge not yet matched to a frame (0 = none) */
} nrf_t;

/* 64-bit time of a 32-bit micros() stamp taken shortly before now. */
static uint64_t widen(uint32_t t32)
{
    uint64_t now = phy_now_us();
    return now - (uint32_t)((uint32_t)now - t32);
}

/* TX_DS raises IRQ too: drop those edges so RX timestamps stay those of received frames. */
static void drain_edges(nrf_t *n)
{
    uint32_t t;
    while (n->lx.irq_fd >= 0 && nrf24_linux_wait_irq(&n->lx, 0, &t) == 1)
        ;
    n->edge_us = 0;
}

static int n_set_channel(void *ctx, uint8_t ch)
{
    nrf_t *n = ctx;
    return nrf24_set_channel(&n->dev, ch) == NRF24_OK ? 0 : -1;
}

static void n_start_rx(void *ctx)
{
    nrf_t *n = ctx;
    if (!n->dev.rx_on)
        nrf24_start_rx(&n->dev);
}

static int n_cca(void *ctx)
{
    nrf_t *n = ctx;
    return nrf24_cca(&n->dev);
}

static int n_send(void *ctx, const uint8_t *f, uint8_t len)
{
    nrf_t *n = ctx;
    nrf24_status_t st = nrf24_send(&n->dev, f, len);
    drain_edges(n);
    return st == NRF24_OK ? 0 : st == NRF24_ERR_LBT ? 1 : -1;
}

static int n_recv(void *ctx, uint64_t deadline, uint8_t *f, uint8_t *len, uint64_t *t_end, uint8_t *rpd)
{
    nrf_t *n = ctx;
    for (;;) {
        if (nrf24_poll_rx(&n->dev, f, len) == NRF24_OK) {
            /* The IRQ edge is the end of the frame (RX_DR after the CRC check); without one (polling, or a
             * second frame already in the FIFO) the best estimate is now. */
            *t_end = n->edge_us ? n->edge_us : phy_now_us();
            n->edge_us = 0;
            *rpd = n->dev.last_rpd;
            return 1;
        }
        uint64_t now = phy_now_us();
        if (now >= deadline)
            return 0;
        uint64_t left = deadline - now;
        if (n->lx.irq_fd >= 0 && left > 300u) {
            uint32_t t;
            /* poll() has 1 ms resolution: wake 300 us early and spin the rest. */
            uint32_t wait = (uint32_t)(left - 300u);
            if (nrf24_linux_wait_irq(&n->lx, wait < 1000u ? 0u : wait - wait % 1000u, &t) == 1)
                n->edge_us = widen(t);
        } else {
            nrf24_linux_delay_us(left < 100u ? (uint32_t)left : 100u);
        }
    }
}

static void n_close(void *ctx)
{
    nrf_t *n = ctx;
    nrf24_linux_close(&n->lx);
    free(n);
}

int phy_nrf24_open(phy_t *phy, const phy_nrf24_opts_t *o, const nrf24_profile_t *profile, char *err, unsigned errlen)
{
    nrf_t *n = calloc(1, sizeof *n);
    if (!n)
        return -1;
    nrf24_linux_cfg_t cfg = {o->spidev, o->spi_hz, o->gpiochip, o->ce_gpio, o->irq_gpio};
    if (nrf24_linux_open(&n->lx, &cfg, &n->hal)) {
        snprintf(err, errlen, "%s", n->lx.err);
        free(n);
        return -1;
    }
    nrf24_status_t st = nrf24_init(&n->dev, &n->hal, profile);
    if (st != NRF24_OK) {
        snprintf(err, errlen, "nrf24_init(%s) failed: status %d (1 = no SPI answer, 2 = not an nRF24L01+)",
                 profile->name, (int)st);
        nrf24_linux_close(&n->lx);
        free(n);
        return -1;
    }
    memset(phy, 0, sizeof *phy);
    phy->ctx = n;
    phy->profile = profile;
    phy->set_channel = n_set_channel;
    phy->start_rx = n_start_rx;
    phy->cca = n_cca;
    phy->send = n_send;
    phy->recv = n_recv;
    phy->close = n_close;
    return 0;
}
