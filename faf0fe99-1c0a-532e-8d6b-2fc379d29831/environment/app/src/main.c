#include <stdio.h>
#include "version.h"
#include "compute.h"

int main(void) {
    long n = 12;
    printf("app coeff-model v%s compute(%ld)=%ld\n", VERSION, n, compute(n));
    return 0;
}
