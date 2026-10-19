CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2 -g -Wall -Wextra -Werror
CPPFLAGS += -D_FILE_OFFSET_BITS=64
PYTHON ?= python3

.PHONY: all test clean
all: build/encoding_stream

build/encoding_stream: encoding_stream.cpp encoding_stream.hpp main.cpp
	mkdir -p build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) encoding_stream.cpp main.cpp -o $@

build/test_receiver: encoding_stream.cpp encoding_stream.hpp tests/test_receiver.cpp
	mkdir -p build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) encoding_stream.cpp tests/test_receiver.cpp -o $@

test: build/encoding_stream build/test_receiver
	./build/test_receiver
	$(PYTHON) tests/test_encoding_stream.py --cpp build/encoding_stream -v

clean:
	rm -f build/encoding_stream build/test_receiver
