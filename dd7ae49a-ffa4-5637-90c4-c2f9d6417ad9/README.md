# compose-multiservice-debug

Container-setup / AR7 ambiguous intermediate state. A three-service compose stack (Go api, Postgres db, Redis) comes up half-wired (wrong api DB env, missing db healthcheck/ordering, wrong redis port) so /order returns empty while the stack still looks "up"; the agent fixes only the compose/Dockerfile wiring. Graded host-side by running the stack, curling the mapped port, and exec-ing redis-cli. Red line RL1: api Go source and seed SQL byte-immutable. Maturity draft; disposition ceiling HOLD:PILOT_REQUIRED.
