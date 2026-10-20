# MTP-F26 Team C - protocol code + PC simulator.
#   make test        generate sample files, build, run the simulator suite and the usb_msc tests
#   make sim         build only;  ./build/sim sri --loss 0.1 ...  /  ./build/sim nm --nodes 12 ...
#   make usb-xcheck  usb_msc against a FAT image made and checked by pyfatfs (needs: pip install pyfatfs)
#   make linux       the Raspberry Pi 3 node (build/teamc-node) and the stick-image tool (build/mkstick)
#   make e2e         whole nodes against each other over the emulated UDP radio (port/linux/e2e.sh, ~1-2 min)
CC ?= cc
CXX ?= c++
CXXFLAGS ?= -std=c++17 -O2 -g -Wall -Wextra -Werror
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
LNX = port/linux
LINUX_SRC = $(LNX)/node.c $(LNX)/radio.c $(LNX)/phy_udp.c $(LNX)/phy_nrf24.c $(LNX)/store.c $(LNX)/stick.c \
	$(LNX)/ui.c $(RADIO)/linux/nrf24_hal_linux.c
LINUX_FLAGS = -I$(LNX) -I$(RADIO)/linux
TEXT = test_encoding_text
TEXT_OBJ = build/text/encoding_stream.o build/text/encoding_stream_c.o
LINUX_FLAGS += -I$(TEXT)

.PHONY: test sim usb sample usb-xcheck clean linux e2e encoding-e2e

ifeq ($(shell uname -s),Linux)
test: sim usb sample linux
else
test: sim usb sample
endif
	./build/sim test
	./build/test_usb

linux: build/teamc-node build/mkstick

build/teamc-node: $(PROTO) $(RADIO_SRC) $(USB) $(LINUX_SRC) $(FATFS_OBJ) $(TEXT_OBJ) $(wildcard src/*.h $(LNX)/*.h) $(TEXT)/encoding_stream_c.h $(RADIO)/nrf24_config.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(LINUX_FLAGS) $(CFLAGS) -o $@ $(PROTO) $(RADIO_SRC) $(USB) $(LINUX_SRC) $(FATFS_OBJ) $(TEXT_OBJ) -lz -lpthread -lstdc++

build/text/%.o: $(TEXT)/%.cpp $(TEXT)/encoding_stream.hpp $(TEXT)/encoding_stream_c.h
	mkdir -p build/text
	$(CXX) -D_FILE_OFFSET_BITS=64 $(CXXFLAGS) -c -o $@ $<

build/mkstick: $(LNX)/mkstick.c $(LNX)/stick.c $(USB) $(FATFS_OBJ) $(LNX)/stick.h src/usb_msc.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(LINUX_FLAGS) -DFF_USE_MKFS=1 $(CFLAGS) -o $@ $(LNX)/mkstick.c $(LNX)/stick.c $(USB) $(FATFS_OBJ)

e2e: linux sample
	sh $(LNX)/e2e.sh

build/test_text_bridge: tests/test_text_bridge.c src/codec.c src/codec.h $(TEXT_OBJ) $(TEXT)/encoding_stream_c.h
	mkdir -p build
	$(CC) $(CPPFLAGS) -I$(TEXT) $(CFLAGS) -o $@ tests/test_text_bridge.c src/codec.c $(TEXT_OBJ) -lz -lstdc++

encoding-e2e: linux build/test_text_bridge
	./build/test_text_bridge
	$(PYTHON) $(LNX)/test_text_integration.py

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
