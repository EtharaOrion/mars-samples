FROM gcc:13
WORKDIR /app
COPY app/ /app/
RUN set -eux; \
    mkdir -p build; \
    cp include/params.h /tmp/params.current.h; \
    printf '#ifndef PARAMS_H\n#define PARAMS_H\n#define COEFF 4\n#define OFFSET 5\n#endif\n' > include/params.h; \
    cc -O2 -Iinclude -c src/compute.c -o build/compute.o; \
    cp /tmp/params.current.h include/params.h; \
    rm -f /tmp/params.current.h; \
    touch -d '2021-01-01T00:00:00' Makefile src/main.c src/compute.c include/compute.h include/version.h; \
    touch -d '2021-01-01T00:10:00' build/compute.o; \
    touch -d '2021-01-01T00:20:00' include/params.h
CMD ["sleep","infinity"]
