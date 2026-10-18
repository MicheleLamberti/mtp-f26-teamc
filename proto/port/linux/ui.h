/* MTP-F26 Team C - buttons, switches, LEDs and the battery gauge of the Linux node.
 *
 * GPIO (BCM numbers, hw/KICAD_SESSION_PROMPT.md): Tx/Rx button 17, role switch 27 (closed = TX), mode switch
 * on 23 + 16 (a 3-position on-off-on switch: 23 low = NM, 16 low = MRM, neither = SRI), activity LED 5,
 * status LED 6. Inputs have pull-ups and are active low. The rules: a button turns Tx/Rx on and off, and a
 * pilot light blinks while in Tx/Rx. No input says where the box is in the network.
 *
 * The simulated UI (tests, no GPIO) takes role and mode from the command line; a press comes from SIGUSR1
 * or from a time given on the command line.
 */
#ifndef UI_H
#define UI_H

#include <stdint.h>

typedef enum { MODE_SRI = 0, MODE_MRM = 1, MODE_NM = 2 } node_mode_t;

typedef struct {
    int sim;
    int in_fd, out_fd;
    /* simulated inputs */
    int sim_role_tx;
    node_mode_t sim_mode;
    uint64_t sim_press_at[4];   /* timed presses (us, CLOCK_MONOTONIC), 0 = unused */
    /* debounce */
    int btn_down;
    uint64_t btn_since;
    int leds_act, leds_status;
    /* battery */
    int i2c_fd;
} ui_t;

int ui_open_gpio(ui_t *u, const char *chip, char *err, unsigned errlen);
void ui_open_sim(ui_t *u, int role_tx, node_mode_t mode);
/* A simulated press at t (CLOCK_MONOTONIC us). */
void ui_sim_press_at(ui_t *u, uint64_t t_us);
/* 1 once per press of the Tx/Rx button (debounced), or per SIGUSR1 / timed press in the simulation. */
int ui_pressed(ui_t *u, uint64_t now_us);
int ui_role_tx(ui_t *u);
node_mode_t ui_mode(ui_t *u);
void ui_leds(ui_t *u, int act, int status);
void ui_close(ui_t *u);
/* SIGUSR1 handler body (async-signal-safe). */
void ui_signal_press(void);

/* MAX17048 fuel gauge on I2C (address 0x36). mV of the cell, or -1 without a gauge. */
int ui_battery_open(ui_t *u, const char *i2c_dev);
int ui_battery_mv(ui_t *u);

#endif /* UI_H */
