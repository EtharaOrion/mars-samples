/* Small C program compiled by the root Makefile's `build` recipe.
 * The recipe passes -DFROM_ROOT so this branch is selected at compile
 * time and the runtime output line ROOT_BINARY_STDOUT is what the
 * verifier looks for as evidence that the compiled artifact ran.
 */
#include <stdio.h>

int main(void) {
#ifdef FROM_ROOT
    printf("ROOT_BINARY_STDOUT: hello from root main (FROM_ROOT set)\n");
#else
    printf("ROOT_BINARY_STDOUT: hello from root main (FROM_ROOT unset)\n");
#endif
    return 0;
}
