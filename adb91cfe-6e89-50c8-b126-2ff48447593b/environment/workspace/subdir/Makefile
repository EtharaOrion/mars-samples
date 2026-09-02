# Subdir build system for the mars-configure-makefile-phony-implicit-rule-conflict-v2
# task. Provides `test`, `build`, `clean`, and a private `helper` target
# it depends on. The `test` recipe runs the compiled helper binary and
# captures its stdout into a run log named literally `test`; the `build`
# recipe compiles helper.c into an executable literally named `build`.
# Both recipes produce a file whose name collides with its target name,
# so GNU Make will treat these targets as up-to-date on any invocation
# after the first unless the targets are declared .PHONY. This subdir
# Makefile is invoked through $(MAKE) -C subdir from the root Makefile,
# so a fix that only touches the root Makefile leaves this gap intact
# and the second recursive invocation silently skips the recipe.

CC := gcc
CFLAGS := -O0 -Wall -Wno-unused

test: helper
	@echo "SUBDIR_TEST_MARKER: subdir test suite executed"
	@./helper > test

build: helper
	@echo "SUBDIR_BUILD_MARKER: subdir build stage executed"
	@cp helper build

helper: helper.c
	@$(CC) $(CFLAGS) -o helper helper.c

clean:
	@rm -f helper build test
