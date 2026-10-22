# Connecting to the team's Raspberry Pis

How to reach Team C's two Raspberry Pi 3 A+ boxes while developing: on the network they know, on a different
WiFi, and when they cannot reach any network. Setup of a fresh card: [`proto/port/linux/README.md`](proto/port/linux/README.md)
"Pi setup". Last updated 22-Oct-26.

| Box | Hostname | User | State |
|---|---|---|---|
| C1 | `mtp-team-c1` | `mtp-team-c1` | Pi setup step 1 + team hotspot + serial console, 22-Oct |
| C2 | `mtp-team-c2` | `mtp-team-c2` | Pi setup step 1 + team hotspot + serial console, 22-Oct |

Both run Pi OS 13 (trixie, 64-bit; desktop image that boots to the console). Step 1 = SPI, I2C, Bluetooth off,
`core_freq=250`, `isolcpus=3`, no desktop at boot; plus `enable_uart=1` (serial console). Backups of the original
`config.txt` / `cmdline.txt` in `/boot/firmware/*.bak-teamc`.
**Passwords are never in the repository: ask Santiago.** Keep your own copy in a `.env` at the repo root
(`cp .env.example .env`; the repository ignores it).

**WiFi known to both Pis (22-Oct): Santiago's home network and the team hotspot `teamc-pi`** (WPA2; password: ask
Santiago). Anywhere else, start a phone hotspot named `teamc-pi` ([team hotspot](#team-hotspot-teamc-pi)) or read
[Another WiFi](#another-wifi) first.

## 1. Power it

- Use a 5.1 V ≥ 2.5 A supply into the micro-USB (the official Pi supply). A laptop USB port and a phone charger
  both boot it, but both Pis reported under-voltage on them (`throttled=0x50005` / `0x50000` on 22-Oct): fine for
  SSH, not for radio or timing tests. Check with `vcgencmd get_throttled`; it must print `throttled=0x0`.
- On a weak laptop port C2 once booted (red on, green blinking) but **never joined the WiFi**; it came up at once
  on a phone charger. If a Pi does not show up after 2 minutes, try a stronger supply first.
- The A+ micro-USB carries **power only, no data**: plugging it into a laptop gives no USB network or serial link.
  You reach the Pi over WiFi (or the options in [No network at all](#no-network-at-all)).
- Boot to SSH takes about 1 minute (3–5 minutes the first time after flashing a card).

## 2. Find it

| From | Command |
|---|---|
| Windows PowerShell, macOS, Linux | `ping mtp-team-c1.local` (mDNS name) |
| WSL2 | `.local` names do **not** resolve inside WSL. Use the IP, or Windows' own ssh from WSL: `ssh.exe mtp-team-c1@mtp-team-c1.local` |
| Phone hotspot | The hotspot's "connected devices" list shows the hostname and IP |
| Home router | Its web page lists DHCP clients by hostname |

The IP comes from DHCP and can change between boots. Do not look for the Pi by MAC address: trixie's
NetworkManager does not show the usual Raspberry Pi prefix (`b8:27:eb`), as seen on 22-Oct. Last resort on
Windows, a ping sweep, then try SSH on each new address (replace `192.168.1` with your network):

```powershell
$t = 1..254 | % { (New-Object Net.NetworkInformation.Ping).SendPingAsync("192.168.1.$_", 800) }
[void][Threading.Tasks.Task]::WaitAll($t); $t | ? { $_.Result.Status -eq "Success" } | % { $_.Result.Address }
```

## 3. Log in

```sh
ssh mtp-team-c1@mtp-team-c1.local        # or ssh mtp-team-c1@<IP>
```

- **Use a key** (once per laptop): `ssh-keygen -t ed25519` if you have none, then `ssh-copy-id
  mtp-team-c1@<IP>`. On Windows without `ssh-copy-id`: `type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh
  mtp-team-c1@<IP> "cat >> ~/.ssh/authorized_keys"`. Santiago's laptop key is on both Pis.
- **One-line `sudo` needs `-t`** (it must ask for the password): `ssh -t mtp-team-c1@<IP> sudo poweroff`.
- **`sudo` asks for the user's password**, but Pi OS sets `timestamp_type=global`: after one successful `sudo`,
  no session of that user is asked again for 15 minutes, including a new SSH login. That is normal, not a
  password-less account.
- **Raspberry Pi Connect** (browser shell at connect.raspberrypi.com) is signed in to Santiago's Raspberry Pi ID:
  only that account sees the Pis there. It works on any network with internet access, including networks
  that block device-to-device traffic. Everyone else uses SSH.

## 4. Shut it down

`sudo poweroff` (or `ssh -t <user>@<IP> sudo poweroff`), then unplug once the green ACT LED has stopped
flashing (about 10 s; the red LED stays on). Pulling the power while Linux runs can corrupt the SD card.

## Another WiFi

A Pi joins only networks it already knows. NetworkManager keeps all of them and picks whichever is in range,
so add a network **before** taking the box there, while you can still log in at home.

### Add a network the Pi knows nothing about yet

The network does not need to be in range. Easiest, with no password left in the shell history:

```sh
sudo nmtui        # Edit a connection -> Add -> Wi-Fi: profile name, SSID, WPA & WPA2 Personal, password
```

or in one line (the password stays in `~/.bash_history`; delete the line afterwards with `history -d`):

```sh
sudo nmcli connection add type wifi ifname wlan0 con-name "<name>" ssid "<SSID>" \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<password>" connection.autoconnect yes
```

Check and tidy: `nmcli connection show` (all known networks), `nmcli -f NAME,DEVICE connection show --active`
(the one in use), `sudo nmcli connection delete "<name>"`. To prefer one when several are in range:
`sudo nmcli connection modify "<name>" connection.autoconnect-priority 10` (higher wins).

If the network is in range right now, `sudo nmcli --ask dev wifi connect "<SSID>"` adds it and switches to it,
asking for the password. Over SSH that drops your session; log in again on the new network.

### Team hotspot `teamc-pi`

Both Pis know the network `teamc-pi` (WPA2 Personal, added with `nmtui` on 22-Oct; the password is shared
outside the repository: ask Santiago). So **any** teammate's phone hotspot with that name and password works
anywhere, campus included. Tested 22-Oct with Santiago's phone on both Pis: each joined within seconds, got an
address from the phone (10.72.203.x), name lookups worked (pings to 1.1.1.1 were dropped, as phone hotspots often
do), and went back to the home network afterwards.

- Phone: set the hotspot name `teamc-pi` and the password; on an iPhone turn on "Maximize Compatibility" (2.4 GHz).
- If both the home network and `teamc-pi` are in range, the Pi stays on whichever it joined first. To move it
  by hand: `sudo nmcli connection up teamc-pi` (your SSH session drops; log in again on the hotspot).
- Connect your laptop to the same hotspot, read the Pi's IP in the phone's device list, `ssh` as usual.
- Mobile data is only used for internet traffic (apt, git, Pi Connect); SSH between laptop and Pi stays local.
- During radio bench tests, keep the hotspot (and the Pi's own WiFi) in mind: they are 2.4 GHz traffic next to
  the nRF24. Note the channel, or use 5 GHz on the phone when it can (the Pi 3 A+ supports 5 GHz too).

### eduroam (campus)

Not tested. Two problems: eduroam is WPA2-Enterprise (it needs a personal university login stored on a shared
box), and campus WiFi usually blocks device-to-device traffic, so your laptop on eduroam may not reach the Pi by
SSH even when both are connected. Pi Connect would still work. Prefer the team hotspot. If you do need it, take the
EAP method, phase-2 method and CA certificate from UPC's eduroam instructions; the shape is:

```sh
sudo nmcli connection add type wifi ifname wlan0 con-name eduroam ssid eduroam \
    wifi-sec.key-mgmt wpa-eap 802-1x.eap peap 802-1x.phase2-auth mschapv2 \
    802-1x.identity "<you>@<domain>" 802-1x.password "<password>" 802-1x.ca-cert "<path to CA cert>"
```

### No network at all

The Pi is somewhere it knows no network and you cannot log in. Options, quickest first:

1. **Make a network it knows.** Start a phone hotspot named `teamc-pi` with the team password.
2. **Keyboard + HDMI monitor** (full-size HDMI on the A+, keyboard in its USB-A port): log in on the console and run
   `sudo nmtui`.
3. **USB-Ethernet adapter** in the USB-A port, cable to the router: the Pi gets an address by DHCP; find it as in
   step 2, SSH in, add the WiFi.
4. **Serial console:** a 3.3 V USB-serial adapter on header pins 8 (Pi TX), 10 (Pi RX), 6 (GND), 115200 baud
   (with the carrier HAT on: its 3-pin UART header J13). Ready on both Pis since 22-Oct: `enable_uart=1`,
   `/dev/serial0 → ttyAMA0` with a login prompt. Cross the wires: adapter RX to pin 8, adapter TX to pin 10.
5. **Re-flash the card** with Raspberry Pi Imager (hostname, user, password, WiFi, Pi Connect token as before).
   This erases the Pi: redo Pi setup step 1 afterwards. C1 needed this once on 22-Oct: the first WiFi entry in
   Imager never joined.

On trixie the WiFi settings live in the root (ext4) partition, so they cannot be edited from Windows by putting
the card in a laptop; only the boot (FAT) partition is visible there.

## Competition days

WiFi, Bluetooth and Pi Connect are for development only: the rules (p.6) ban an active WiFi/BT chip (Atenea Q22).
Before QM or any test day: `sudo systemctl disable --now rpi-connect`, then `dtoverlay=disable-wifi` (already
`disable-bt`) in `/boot/firmware/config.txt`, reboot. From then on only options 2–4 of
[No network at all](#no-network-at-all) reach the Pi: bring a 3.3 V USB-serial adapter (the serial console is
already on) or a keyboard and monitor.
