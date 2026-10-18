/* MTP-F26 Team C - buttons, switches, LEDs and battery gauge of the Linux node. See ui.h. */
#define _GNU_SOURCE
#include "ui.h"

#include <fcntl.h>
#include <linux/gpio.h>
#include <linux/i2c-dev.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define GPIO_BTN 17u
#define GPIO_ROLE 27u
#define GPIO_NM 23u
#define GPIO_MRM 16u
#define GPIO_LED_ACT 5u
#define GPIO_LED_STATUS 6u
#define DEBOUNCE_US 30000u

static volatile sig_atomic_t sig_presses;

void ui_signal_press(void) { sig_presses++; }

static int request(int chip, const unsigned *gpios, unsigned n, int output, const char *consumer)
{
    struct gpio_v2_line_request req;
    memset(&req, 0, sizeof req);
    for (unsigned i = 0; i < n; i++)
        req.offsets[i] = gpios[i];
    req.num_lines = n;
    snprintf(req.consumer, sizeof req.consumer, "%s", consumer);
    req.config.flags = output ? GPIO_V2_LINE_FLAG_OUTPUT : GPIO_V2_LINE_FLAG_INPUT | GPIO_V2_LINE_FLAG_BIAS_PULL_UP;
    if (ioctl(chip, GPIO_V2_GET_LINE_IOCTL, &req) < 0)
        return -1;
    return req.fd;
}

int ui_open_gpio(ui_t *u, const char *chip_path, char *err, unsigned errlen)
{
    memset(u, 0, sizeof *u);
    u->in_fd = u->out_fd = u->i2c_fd = -1;
    int chip = open(chip_path, O_RDWR | O_CLOEXEC);
    if (chip < 0) {
        snprintf(err, errlen, "cannot open %s", chip_path);
        return -1;
    }
    static const unsigned in[] = {GPIO_BTN, GPIO_ROLE, GPIO_NM, GPIO_MRM};
    static const unsigned out[] = {GPIO_LED_ACT, GPIO_LED_STATUS};
    u->in_fd = request(chip, in, 4, 0, "teamc-ui");
    u->out_fd = request(chip, out, 2, 1, "teamc-led");
    close(chip);
    if (u->in_fd < 0 || u->out_fd < 0) {
        snprintf(err, errlen, "cannot request the button/switch/LED GPIOs on %s", chip_path);
        ui_close(u);
        return -1;
    }
    return 0;
}

void ui_open_sim(ui_t *u, int role_tx, node_mode_t mode)
{
    memset(u, 0, sizeof *u);
    u->sim = 1;
    u->in_fd = u->out_fd = u->i2c_fd = -1;
    u->sim_role_tx = role_tx;
    u->sim_mode = mode;
}

void ui_sim_press_at(ui_t *u, uint64_t t)
{
    for (unsigned i = 0; i < 4; i++)
        if (!u->sim_press_at[i]) {
            u->sim_press_at[i] = t;
            return;
        }
}

/* Input bits, 1 = active (pulled low): bit 0 button, 1 role TX, 2 NM, 3 MRM. */
static unsigned inputs(ui_t *u)
{
    struct gpio_v2_line_values v;
    memset(&v, 0, sizeof v);
    v.mask = 0xFu;
    if (u->in_fd < 0 || ioctl(u->in_fd, GPIO_V2_LINE_GET_VALUES_IOCTL, &v) < 0)
        return 0;
    return (unsigned)(~v.bits) & 0xFu;
}

int ui_pressed(ui_t *u, uint64_t now)
{
    static sig_atomic_t seen;
    if (sig_presses != seen) {
        seen++;
        return 1;
    }
    if (u->sim) {
        for (unsigned i = 0; i < 4; i++)
            if (u->sim_press_at[i] && now >= u->sim_press_at[i]) {
                u->sim_press_at[i] = 0;
                return 1;
            }
        return 0;
    }
    int down = (int)(inputs(u) & 1u);
    if (down != u->btn_down) {
        if (!u->btn_since)
            u->btn_since = now;
        if (now - u->btn_since >= DEBOUNCE_US) {   /* stable for 30 ms */
            u->btn_down = down;
            u->btn_since = 0;
            return down;   /* the press, not the release */
        }
    } else {
        u->btn_since = 0;
    }
    return 0;
}

int ui_role_tx(ui_t *u) { return u->sim ? u->sim_role_tx : (int)((inputs(u) >> 1) & 1u); }

node_mode_t ui_mode(ui_t *u)
{
    if (u->sim)
        return u->sim_mode;
    unsigned b = inputs(u);
    return (b & 4u) ? MODE_NM : (b & 8u) ? MODE_MRM : MODE_SRI;
}

void ui_leds(ui_t *u, int act, int status)
{
    if (act == u->leds_act && status == u->leds_status)
        return;
    u->leds_act = act;
    u->leds_status = status;
    if (u->out_fd < 0)
        return;
    struct gpio_v2_line_values v;
    memset(&v, 0, sizeof v);
    v.mask = 3u;
    v.bits = (act ? 1u : 0u) | (status ? 2u : 0u);
    ioctl(u->out_fd, GPIO_V2_LINE_SET_VALUES_IOCTL, &v);
}

void ui_close(ui_t *u)
{
    if (u->out_fd >= 0) {
        ui_leds(u, 0, 0);
        close(u->out_fd);
    }
    if (u->in_fd >= 0)
        close(u->in_fd);
    if (u->i2c_fd >= 0)
        close(u->i2c_fd);
    u->in_fd = u->out_fd = u->i2c_fd = -1;
}

int ui_battery_open(ui_t *u, const char *dev)
{
    u->i2c_fd = open(dev, O_RDWR | O_CLOEXEC);
    if (u->i2c_fd < 0)
        return -1;
    if (ioctl(u->i2c_fd, I2C_SLAVE, 0x36) < 0 || ui_battery_mv(u) < 0) {
        close(u->i2c_fd);
        u->i2c_fd = -1;
        return -1;
    }
    return 0;
}

int ui_battery_mv(ui_t *u)
{
    if (u->i2c_fd < 0)
        return -1;
    uint8_t reg = 0x02, b[2];   /* VCELL: 78.125 uV per LSB */
    if (write(u->i2c_fd, &reg, 1) != 1 || read(u->i2c_fd, b, 2) != 2)
        return -1;
    unsigned raw = (unsigned)b[0] << 8 | b[1];
    return (int)((uint64_t)raw * 78125u / 1000000u);
}
