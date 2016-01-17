all: ep15
	perf stat -e cycles:u -e instructions:u -e branch-misses:u -e L1-dcache-load-misses -e L1-dcache-loads ep15 cross.input

ep15: ep15.c
	gcc -O3 -Wall -o ep15 ep15.c

dist:
	mkdir ep15
	ln ep15.c Makefile cross.input ep15
	tar cvfz ep15.tar.gz ep15
	rm -rf ep15
