# MTP-F26 Team C - protocol code + PC simulator.
#   make test        generate sample files, build, run the simulator suite and the usb_msc tests
#   make sim         build only;  ./build/sim sri --loss 0.1 ...  /  ./build/sim nm --nodes 12 ...
#   make usb-xcheck  usb_msc against a FAT image made and checked by pyfatfs (needs: pip install pyfatfs)
CC ?= cc
RADIO = ../radio/fw
FATFS = third_party/fatfs
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Werror
CPPFLAGS += -Isrc -Isim -I$(RADIO) -I$(FATFS)
PROTO = src/link.c src/nm_gossip.c src/nm_log.c src/codec.c
RADIO_SRC = $(RADIO)/nrf24.c $(RADIO)/crc16.c
SIM = sim/sim.c sim/main.c
USB = src/usb_msc.c src/usb_diskio.c
USB_TEST = tests/test_usb.c tests/ramdisk.c
# FatFs is third-party code: its own (lenient) warning level; mkfs only for the tests.
FATFS_OBJ = build/fatfs/ff.o build/fatfs/ffunicode.o
FATFS_FLAGS = -std=c11 -O2 -g -w -DFF_USE_MKFS=1
PYTHON ?= python3

.PHONY: test sim usb sample usb-xcheck clean

test: sim usb sample
	./build/sim test
	./build/test_usb

sim: build/sim

usb: build/test_usb

build/sim: $(PROTO) $(RADIO_SRC) $(SIM) $(wildcard src/*.h sim/*.h) $(RADIO)/nrf24_config.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $(PROTO) $(RADIO_SRC) $(SIM) -lz

build/fatfs/%.o: $(FATFS)/%.c $(FATFS)/ffconf.h $(FATFS)/ff.h
	mkdir -p build/fatfs
	$(CC) -I$(FATFS) $(FATFS_FLAGS) -c -o $@ $<

build/test_usb: $(USB) $(USB_TEST) $(FATFS_OBJ) src/usb_msc.h tests/ramdisk.h
	mkdir -p build
	$(CC) $(CPPFLAGS) -Itests -DFF_USE_MKFS=1 $(CFLAGS) -o $@ $(USB) $(USB_TEST) $(FATFS_OBJ)

usb-xcheck: build/test_usb
	$(PYTHON) tools/fat_xcheck.py build/test_usb build

sample: build/sample.txt build/sample_utf16.txt

build/sample.txt: tools/make_sample.py
	python3 tools/make_sample.py $@

build/sample_utf16.txt: tools/make_sample.py
	python3 tools/make_sample.py $@ --utf16

clean:
	rm -rf build
