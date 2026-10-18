# MTP-F26 Team C radio firmware - host build and tests.
#   make test     regenerate nrf24_config.h from ../phy_config.py, build, run tests
#                 (on Linux it also builds the Pi 3 bench tool, as a compile check)
#   make linux    build/nrf24_probe: the Linux HAL + bench tool (run it on the Raspberry Pi 3)
CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Werror -Wconversion -O1 -g
SRC = nrf24.c crc16.c
TEST_SRC = test/test_main.c test/mock_nrf24.c
LINUX_SRC = linux/nrf24_hal_linux.c linux/nrf24_probe.c

.PHONY: test config clean linux

ifeq ($(shell uname -s),Linux)
test: build/test_radio build/nrf24_probe
else
test: build/test_radio
endif
	./build/test_radio

linux: build/nrf24_probe

build/nrf24_probe: config $(SRC) $(LINUX_SRC) nrf24.h linux/nrf24_hal_linux.h
	mkdir -p build
	$(CC) $(CFLAGS) -o $@ $(SRC) $(LINUX_SRC) -lpthread

config:
	cd .. && python3 phy_config.py > /dev/null

build/test_radio: config $(SRC) $(TEST_SRC) nrf24.h crc16.h test/mock_nrf24.h
	mkdir -p build
	$(CC) $(CFLAGS) -o $@ $(SRC) $(TEST_SRC)

clean:
	rm -rf build
