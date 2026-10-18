#!/bin/sh
# MTP-F26 Team C - whole Linux nodes (build/teamc-node) against each other over the emulated UDP radio.
#
#   sh port/linux/e2e.sh [scenario ...]      (from proto/; default: all)   or   make -C proto e2e
#
# Each node gets its own data directory (the SD card) and FAT stick images made by build/mkstick. The
# simulated UI presses GO and STOP at given times. A scenario passes when the stick the receiver saved to
# holds a byte-identical copy of the original file (NM: every node's NM_FILE.TXT).
#   sri         TEAM_250K, fixed channel, 5 % loss
#   mrm         TEAM_FHSS: hopping + LBT, 10 % of CCAs busy, 5 % loss (hop acquisition from parking)
#   sri_reboot  the receiver is killed (kill -9) mid-transfer and restarted: resumes without GO
#   mrm_reboot  the same while hopping: the restarted receiver parks and re-acquires the hop timing
#   tx_reboot   the sender is killed and restarted while hopping
#   nm          NM gossip, 3 nodes in a line (origin - relay - end): every node saves the NM-file
set -u
cd "$(dirname "$0")/../.." || exit 2
NODE=build/teamc-node
MK=build/mkstick
W=build/e2e
LINES=${E2E_LINES:-1500}
STOP=${E2E_STOP:-30}
rm -rf "$W"
mkdir -p "$W"
head -n "$LINES" build/sample.txt > "$W/sample.txt"
head -n 5 build/sample.txt > "$W/nm.txt"
FAILS=0
PORT=47100

pass() { echo "PASS $1: $2"; }
fail() { echo "FAIL $1: $2"; FAILS=$((FAILS + 1)); }

done_time() { grep -o 'DONE after [0-9.]* s' "$1" | head -n 1 | awk '{print $3}'; }

# link NAME MODE LOSS BUSY [REBOOT_WHO REBOOT_AT]
link() {
    name=$1 mode=$2 loss=$3 busy=$4 who=${5:-} at=${6:-0}
    D="$W/$name"
    mkdir -p "$D"
    p0=$PORT p1=$((PORT + 1))
    PORT=$((PORT + 10))
    $MK make "$D/tx.img" 16 fat16 "$W/sample.txt" > /dev/null
    $MK make "$D/rx.img" 16 fat16 "$W/sample.txt" > /dev/null
    $MK make "$D/out.img" 16 fat16 > /dev/null
    common="--loss $loss --busy $busy --exit-after-save"
    $NODE --radio "udp:$p1:$p0" --data "$D/rx" --stick "$D/rx.img" --stick-out "$D/out.img" --box C2 \
        --sim-ui rx "$mode" --go-after 0.5 --stop-after "$STOP" --seed 2 $common > "$D/rx.log" 2>&1 &
    rx=$!
    $NODE --radio "udp:$p0:$p1" --data "$D/tx" --stick "$D/tx.img" --box C1 \
        --sim-ui tx "$mode" --go-after 0.5 --stop-after "$STOP" --seed 1 $common > "$D/tx.log" 2>&1 &
    tx=$!
    if [ -n "$who" ]; then
        sleep "$at"
        rest=$(awk "BEGIN{print $STOP - $at - 0.5}")
        if [ "$who" = rx ]; then
            kill -9 $rx 2> /dev/null
            wait $rx 2> /dev/null
            sleep 0.5
            $NODE --radio "udp:$p1:$p0" --data "$D/rx" --stick "$D/rx.img" --stick-out "$D/out.img" --box C2 \
                --sim-ui rx "$mode" --stop-after "$rest" --seed 3 $common > "$D/rx2.log" 2>&1 &
            rx=$!
        else
            kill -9 $tx 2> /dev/null
            wait $tx 2> /dev/null
            sleep 0.5
            $NODE --radio "udp:$p0:$p1" --data "$D/tx" --stick "$D/tx.img" --box C1 \
                --sim-ui tx "$mode" --stop-after "$rest" --seed 4 $common > "$D/tx2.log" 2>&1 &
            tx=$!
        fi
    fi
    wait $tx
    wait $rx
    $MK get "$D/out.img" RX_sample.txt "$D/got.txt" 2> "$D/get.err"
    t=$(done_time "$D/rx.log")
    [ -f "$D/rx2.log" ] && t="$(done_time "$D/rx2.log") (after the restart)"
    if cmp -s "$W/sample.txt" "$D/got.txt"; then
        pass "$name" "$LINES lines identical, receiver done after ${t:-?} s"
    else
        fail "$name" "received file differs or missing (see $D/*.log)"
    fi
}

nm() {
    D="$W/nm"
    mkdir -p "$D"
    a=$PORT b=$((PORT + 1)) c=$((PORT + 2))
    PORT=$((PORT + 10))
    $MK make "$D/n0.img" 16 fat16 "$W/nm.txt" > /dev/null
    $MK make "$D/n1.img" 16 fat16 > /dev/null
    $MK make "$D/n2.img" 16 fat16 > /dev/null
    common="--loss 0.1 --exit-after-save --go-after 0.5 --stop-after 25"
    $NODE --radio "udp:$a:$b" --data "$D/d0" --stick "$D/n0.img" --box C1 --sim-ui tx nm --seed 1 $common > "$D/n0.log" 2>&1 &
    p0=$!
    $NODE --radio "udp:$b:$a,$c" --data "$D/d1" --stick "$D/n1.img" --box C2 --sim-ui rx nm --seed 2 $common > "$D/n1.log" 2>&1 &
    p1=$!
    $NODE --radio "udp:$c:$b" --data "$D/d2" --stick "$D/n2.img" --box X1 --sim-ui rx nm --seed 3 $common > "$D/n2.log" 2>&1 &
    p2=$!
    wait $p0 $p1 $p2
    ok=1
    for k in 0 1 2; do
        $MK get "$D/n$k.img" NM_FILE.TXT "$D/got$k.txt" 2> /dev/null
        $MK get "$D/n$k.img" NM_LOG.TXT "$D/log$k.txt" 2> /dev/null
        cmp -s "$W/nm.txt" "$D/got$k.txt" && [ -s "$D/log$k.txt" ] || ok=0
    done
    if [ $ok = 1 ]; then
        pass nm "3 nodes hold an identical NM_FILE.TXT + NM_LOG.TXT; end node done after $(done_time "$D/n2.log") s"
    else
        fail nm "a node is missing the NM-file or its log (see $D/*.log)"
    fi
}

SC=${*:-"sri mrm sri_reboot mrm_reboot tx_reboot nm"}
for s in $SC; do
    case $s in
    sri) link sri sri 0.05 0 ;;
    mrm) link mrm mrm 0.05 0.1 ;;
    sri_reboot) link sri_reboot sri 0.05 0 rx 3 ;;
    mrm_reboot) link mrm_reboot mrm 0.05 0.1 rx 5 ;;
    tx_reboot) link tx_reboot mrm 0.05 0.1 tx 5 ;;
    nm) nm ;;
    *) fail "$s" "unknown scenario" ;;
    esac
done
[ $FAILS = 0 ] && echo "e2e: ALL PASSED" || echo "e2e: $FAILS FAILED"
[ $FAILS = 0 ]
