/* Small C program compiled by subdir/Makefile's `build` recipe and
 * exercised by subdir/Makefile's `test` recipe. The runtime output
 * line SUBDIR_BINARY_STDOUT is what the verifier looks for through
 * the recursive $(MAKE) -C subdir invocation as evidence that the
 * subdir recipe actually ran.
 */
#include <stdio.h>

int main(void) {
    printf("SUBDIR_BINARY_STDOUT: hello from subdir helper\n");
    return 0;
}
