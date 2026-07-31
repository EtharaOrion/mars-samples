CC = cc
CFLAGS = -O2 -Iinclude
OBJS = build/main.o build/compute.o

app: $(OBJS)
	$(CC) $(CFLAGS) -o app $(OBJS)

build/compute.o: src/compute.c
	@mkdir -p build
	$(CC) $(CFLAGS) -c src/compute.c -o build/compute.o

build/main.o: src/main.c
	@mkdir -p build
	$(CC) $(CFLAGS) -c src/main.c -o build/main.o

clean:
	rm -f build/main.o build/compute.o app

.PHONY: clean
