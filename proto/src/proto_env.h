/* MTP-F26 Team C - platform interface for the protocol modules.
 *
 * The protocol code (link.c, nm_gossip.c) is pure logic: it never touches a radio,
 * a clock or an RTOS directly. Each platform fills one proto_env_t:
 *   - the PC simulator (proto/sim) with a channel model and simulated time;
 *   - the Pico firmware with nrf24_send(), time_us_64() and a hardware alarm.
 * The platform then calls the module's on_frame / on_timer / on_tx_idle handlers.
 *
 * Contract (16-Oct review): on_tx_idle MUST be called each time the transmit queue has drained (the last
 * queued frame is on air and done). The link arms its ACK timer and accepts ACKs only from then on, so a
 * platform that never calls it stalls the link. send() must never drop a frame silently: if the queue is
 * full, block until it drains (the PC simulator counts q_overflow and the tests require it to stay 0).
 */
#ifndef PROTO_ENV_H
#define PROTO_ENV_H

#include <stdint.h>

#define PROTO_NO_TIMER UINT64_MAX

typedef struct proto_env {
    void *ctx;
    /* Queue one frame (<= 32 B body) for transmission; frames go out in order. */
    void (*send)(void *ctx, const uint8_t *frame, uint8_t len);
    uint64_t (*now_us)(void *ctx);
    /* One timer per protocol instance; a new call replaces the previous one.
     * PROTO_NO_TIMER cancels it. */
    void (*set_timer)(void *ctx, uint64_t at_us);
    uint32_t (*rand32)(void *ctx);
} proto_env_t;

#endif /* PROTO_ENV_H */
