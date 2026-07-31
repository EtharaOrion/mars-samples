# recover-lost-git-commit

A container-native terminal task. The environment ships a small Python
repository whose git history has been damaged by a bad reset, leaving the
correct version of one source file recoverable only from dangling objects among
several misleading drafts. The agent must recover the correct version and leave
the repository in a clean, consistent state.

- `instruction.md` — the end-state the agent must reach.
- `environment/` — Docker build context for the task container.
- `solution/solve.sh` — reference recovery (withheld from the agent).
- `tests/` — world-state checks (withheld from the agent).
