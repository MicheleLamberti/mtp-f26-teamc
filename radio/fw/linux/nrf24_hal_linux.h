/* MTP-F26 Team C - nRF24L01+ HAL for Linux (Raspberry Pi 3, D-H1 since 18-Oct-26).
 *
 * SPI through spidev (/dev/spidev0.0: SPI0, CSN = CE0 on GPIO 8, driven by the kernel per
 * transfer), so the HAL provides nrf24_hal_t.xfer and leaves select/transfer NULL: each radio
 * command is one ioctl. CE and IRQ use the GPIO character device (uAPI v2, kernel >= 5.10)
 * directly, without libgpiod. Pin map: hw/KICAD_SESSION_PROMPT.md (CE GPIO 22, IRQ GPIO 24).
 *
 * Timing: micros() is CLOCK_MONOTONIC, the same clock as the IRQ edge timestamps.
 * delay_us() busy-waits for short delays (usleep overshoots by 60 us or more) and sleeps
 * for the bulk of long ones. For the radio thread call nrf24_linux_realtime() (SCHED_FIFO,
 * pinned to an isolated core, memory locked): a stock kernel can still pause it ~1 ms.
 */
#ifndef NRF24_HAL_LINUX_H
#define NRF24_HAL_LINUX_H

#include <stdint.h>

#include "../nrf24.h"

typedef struct {
    const char *spidev;     /* "/dev/spidev0.0" */
    uint32_t spi_hz;        /* 4 MHz requested (3.9 MHz on a Pi 3 with core_freq=250); was 8 MHz until the
                               rev B ribbon review (23-Oct): its SPI return uses pins 6/9/14 only. Raise after T2. */
    const char *gpiochip;   /* "/dev/gpiochip0" = the BCM2837 GPIO bank on a Pi 3 */
    unsigned ce_gpio;       /* 22 */
    int irq_gpio;           /* 24, or -1 to poll only */
} nrf24_linux_cfg_t;

#define NRF24_LINUX_CFG_DEFAULT {"/dev/spidev0.0", 4000000u, "/dev/gpiochip0", 22u, 24}

typedef struct {
    int spi_fd, ce_fd, irq_fd;
    uint32_t spi_hz;
    unsigned spi_errors;   /* failed transfers; the driver then sees 0x00 and fails its checks */
    char err[160];         /* why nrf24_linux_open / _realtime failed */
} nrf24_linux_t;

/* Opens spidev and the GPIO lines and fills *hal (ctx = lx). Returns 0, or -1 with lx->err set. */
int nrf24_linux_open(nrf24_linux_t *lx, const nrf24_linux_cfg_t *cfg, nrf24_hal_t *hal);
void nrf24_linux_close(nrf24_linux_t *lx);

/* Waits up to timeout_us for a falling IRQ edge. Returns 1 with *t_us = the kernel's edge
 * timestamp on the micros() clock, 0 on timeout, -1 on error or without an IRQ line. */
int nrf24_linux_wait_irq(nrf24_linux_t *lx, uint32_t timeout_us, uint32_t *t_us);

/* Real-time setup for the calling (radio) thread: mlockall, SCHED_FIFO at prio (1..99),
 * pinned to cpu (-1 = no pinning). Returns 0, or -1 with lx->err set (usually: not root). */
int nrf24_linux_realtime(nrf24_linux_t *lx, int cpu, int prio);

uint32_t nrf24_linux_micros(void);
void nrf24_linux_delay_us(uint32_t us);

#endif /* NRF24_HAL_LINUX_H */
