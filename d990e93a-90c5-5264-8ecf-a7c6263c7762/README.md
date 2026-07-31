# local-registry

Container-setup / AR3 tool-chaining brittleness. The shipped push.sh never stands up the localhost:5050 registry (and tags the wrong host:port), so the build->tag->push->pull round-trip breaks. Grading (host-side) runs the wiring, checks the registry catalog/tags, then rmi + pull + run to golden stdout, and asserts localhost-only + frozen app source. Maturity draft; disposition ceiling HOLD:PILOT_REQUIRED.
