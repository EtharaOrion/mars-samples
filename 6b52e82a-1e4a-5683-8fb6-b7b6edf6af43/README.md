# container-networking-dns

Container-setup / AR5 option-expansion. Shipped compose splits client and server across two bridge networks so Docker embedded DNS cannot resolve `server`; agent must place both on one user-defined bridge so the frozen client resolves `server` by name. Grading is host-side: bring up the stack, read the client marker, and prove name-based resolution on a shared user-defined network. Maturity draft; disposition ceiling HOLD:PILOT_REQUIRED.
