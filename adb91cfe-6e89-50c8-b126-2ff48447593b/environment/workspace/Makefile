# Root build system for the mars-configure-makefile-phony-implicit-rule-conflict-v2
# task. Provides `all`, `test`, `build`, `clean`, and `help` targets and
# recursively delegates the `test` and `build` targets into subdir/ via
# $(MAKE) --no-print-directory -C subdir. The root recipes also produce
# artifacts whose file names collide with the target names: the `test`
# recipe writes a run log to a file literally named `test`, and the
# `build` recipe compiles main.c into an executable literally named
# `build`. This is a common recursive-Make pattern in older C projects
# and it is what surfaces the .PHONY gap: once a target-named file
# exists on disk, GNU Make will treat the corresponding target as
# up-to-date and silently skip its recipe unless the target is declared
# .PHONY.

.PHONY: all clean help

CC := gcc
CFLAGS := -O0 -Wall -Wno-unused

all: test build

help:
	@echo "targets: all test build clean help"
	@echo "  make test  runs the root+subdir test suites"
	@echo "  make build compiles the root+subdir binaries"
	@echo "  make clean removes generated artifacts"

test:
	@echo "ROOT_TEST_MARKER: root test suite executed"
	@$(MAKE) --no-print-directory -C subdir test
	@echo "root_test_ok" > test

build:
	@echo "ROOT_BUILD_MARKER: root build stage executed"
	@$(CC) $(CFLAGS) -DFROM_ROOT -o build main.c
	@$(MAKE) --no-print-directory -C subdir build
	@./build

clean:
	@rm -f build test
	@$(MAKE) --no-print-directory -C subdir clean
