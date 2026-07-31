#include "compute.h"
#include "params.h"

long compute(long n) {
    return (long)COEFF * n * n + (long)OFFSET * n;
}
