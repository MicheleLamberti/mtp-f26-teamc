/* MTP-F26 Team C - nRF24L01+ HAL for Linux (Raspberry Pi 3). See nrf24_hal_linux.h. */
#define _GNU_SOURCE
#include "nrf24_hal_linux.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/gpio.h>
#include <linux/spi/spidev.h>
#include <poll.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define SLEEP_MARGIN_US 1000u   /* sleep until 1 ms before the deadline, then spin */

static uint64_t now_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000u + (uint64_t)ts.tv_nsec;
}

uint32_t nrf24_linux_micros(void)
{
    return (uint32_t)(now_ns() / 1000u);   /* wraps every 71 min; the driver only uses differences */
}

void nrf24_linux_delay_us(uint32_t us)
{
    uint64_t deadline = now_ns() + (uint64_t)us * 1000u;
    if (us > 2u * SLEEP_MARGIN_US) {
        uint64_t wake = deadline - (uint64_t)SLEEP_MARGIN_US * 1000u;
        struct timespec ts = {(time_t)(wake / 1000000000u), (long)(wake % 1000000000u)};
        while (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, NULL) == EINTR)
            ;
    }
    while (now_ns() < deadline)
        ;
}

static void fail(nrf24_linux_t *lx, const char *what, const char *name)
{
    snprintf(lx->err, sizeof lx->err, "%s %s: %s", what, name, strerror(errno));
}

static void h_xfer(void *ctx, const uint8_t *out, uint8_t *in, uint8_t n)
{
    nrf24_linux_t *lx = ctx;
    struct spi_ioc_transfer t;
    memset(&t, 0, sizeof t);
    t.tx_buf = (uint64_t)(uintptr_t)out;
    t.rx_buf = (uint64_t)(uintptr_t)in;
    t.len = n;
    t.speed_hz = lx->spi_hz;
    t.bits_per_word = 8;
    if (ioctl(lx->spi_fd, SPI_IOC_MESSAGE(1), &t) < 0) {
        lx->spi_errors++;
        memset(in, 0, n);
    }
}

static void h_ce(void *ctx, int high)
{
    nrf24_linux_t *lx = ctx;
    struct gpio_v2_line_values v;
    memset(&v, 0, sizeof v);
    v.mask = 1u;
    v.bits = high ? 1u : 0u;
    ioctl(lx->ce_fd, GPIO_V2_LINE_SET_VALUES_IOCTL, &v);
}

static void h_delay_us(void *ctx, uint32_t us)
{
    (void)ctx;
    nrf24_linux_delay_us(us);
}

static uint32_t h_micros(void *ctx)
{
    (void)ctx;
    return nrf24_linux_micros();
}

static int request_line(nrf24_linux_t *lx, int chip_fd, unsigned gpio, int output, const char *consumer)
{
    struct gpio_v2_line_request req;
    memset(&req, 0, sizeof req);
    req.offsets[0] = gpio;
    req.num_lines = 1;
    snprintf(req.consumer, sizeof req.consumer, "%s", consumer);
    if (output) {
        req.config.flags = GPIO_V2_LINE_FLAG_OUTPUT;
        req.config.num_attrs = 1;   /* start low: CE low = standby */
        req.config.attrs[0].attr.id = GPIO_V2_LINE_ATTR_ID_OUTPUT_VALUES;
        req.config.attrs[0].attr.values = 0;
        req.config.attrs[0].mask = 1u;
    } else {
        /* IRQ is active low and open drain on the nRF24: pull-up, falling edges, monotonic timestamps. */
        req.config.flags = GPIO_V2_LINE_FLAG_INPUT | GPIO_V2_LINE_FLAG_EDGE_FALLING | GPIO_V2_LINE_FLAG_BIAS_PULL_UP;
    }
    if (ioctl(chip_fd, GPIO_V2_GET_LINE_IOCTL, &req) < 0) {
        char name[16];
        snprintf(name, sizeof name, "GPIO %u", gpio);
        fail(lx, "cannot request", name);
        return -1;
    }
    return req.fd;
}

int nrf24_linux_open(nrf24_linux_t *lx, const nrf24_linux_cfg_t *cfg, nrf24_hal_t *hal)
{
    memset(lx, 0, sizeof *lx);
    lx->spi_fd = lx->ce_fd = lx->irq_fd = -1;
    lx->spi_hz = cfg->spi_hz;

    lx->spi_fd = open(cfg->spidev, O_RDWR | O_CLOEXEC);
    if (lx->spi_fd < 0) {
        fail(lx, "cannot open", cfg->spidev);   /* SPI off? dtparam=spi=on in config.txt */
        return -1;
    }
    uint8_t mode = SPI_MODE_0, bits = 8;
    uint32_t hz = cfg->spi_hz;
    if (ioctl(lx->spi_fd, SPI_IOC_WR_MODE, &mode) < 0 || ioctl(lx->spi_fd, SPI_IOC_WR_BITS_PER_WORD, &bits) < 0 ||
        ioctl(lx->spi_fd, SPI_IOC_WR_MAX_SPEED_HZ, &hz) < 0) {
        fail(lx, "cannot configure", cfg->spidev);
        nrf24_linux_close(lx);
        return -1;
    }

    int chip = open(cfg->gpiochip, O_RDWR | O_CLOEXEC);
    if (chip < 0) {
        fail(lx, "cannot open", cfg->gpiochip);
        nrf24_linux_close(lx);
        return -1;
    }
    lx->ce_fd = request_line(lx, chip, cfg->ce_gpio, 1, "nrf24-ce");
    if (lx->ce_fd >= 0 && cfg->irq_gpio >= 0)
        lx->irq_fd = request_line(lx, chip, (unsigned)cfg->irq_gpio, 0, "nrf24-irq");
    close(chip);
    if (lx->ce_fd < 0 || (cfg->irq_gpio >= 0 && lx->irq_fd < 0)) {
        nrf24_linux_close(lx);
        return -1;
    }

    memset(hal, 0, sizeof *hal);
    hal->ctx = lx;
    hal->select = NULL;     /* the kernel drives CSN (CE0) for each transfer */
    hal->transfer = NULL;
    hal->xfer = h_xfer;
    hal->ce = h_ce;
    hal->delay_us = h_delay_us;
    hal->micros = h_micros;
    return 0;
}

void nrf24_linux_close(nrf24_linux_t *lx)
{
    if (lx->ce_fd >= 0)
        close(lx->ce_fd);   /* releasing the line leaves CE where the kernel puts it (input) */
    if (lx->irq_fd >= 0)
        close(lx->irq_fd);
    if (lx->spi_fd >= 0)
        close(lx->spi_fd);
    lx->spi_fd = lx->ce_fd = lx->irq_fd = -1;
}

int nrf24_linux_wait_irq(nrf24_linux_t *lx, uint32_t timeout_us, uint32_t *t_us)
{
    if (lx->irq_fd < 0)
        return -1;
    struct pollfd p = {lx->irq_fd, POLLIN, 0};
    int ms = (int)((timeout_us + 999u) / 1000u);
    int r = poll(&p, 1, ms);
    if (r <= 0)
        return r < 0 ? -1 : 0;
    struct gpio_v2_line_event ev;
    if (read(lx->irq_fd, &ev, sizeof ev) != (ssize_t)sizeof ev)
        return -1;
    if (t_us)
        *t_us = (uint32_t)(ev.timestamp_ns / 1000u);   /* CLOCK_MONOTONIC, as micros() */
    return 1;
}

int nrf24_linux_realtime(nrf24_linux_t *lx, int cpu, int prio)
{
    if (mlockall(MCL_CURRENT | MCL_FUTURE) < 0) {
        fail(lx, "mlockall", "");
        return -1;
    }
    if (cpu >= 0) {
        cpu_set_t set;
        CPU_ZERO(&set);
        CPU_SET((size_t)cpu, &set);
        int e = pthread_setaffinity_np(pthread_self(), sizeof set, &set);
        if (e) {
            errno = e;
            fail(lx, "cannot pin to CPU", "");
            return -1;
        }
    }
    struct sched_param sp;
    memset(&sp, 0, sizeof sp);
    sp.sched_priority = prio;
    int e = pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);
    if (e) {
        errno = e;
        fail(lx, "SCHED_FIFO", "(run as root or give CAP_SYS_NICE)");
        return -1;
    }
    return 0;
}
