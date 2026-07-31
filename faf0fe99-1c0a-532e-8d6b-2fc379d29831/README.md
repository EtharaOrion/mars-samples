# fix-makefile-stale-dep

Terminal Task, sub_type build-ci-cd, archetype AR9 temporal/staleness. A C project's Makefile omits header prerequisites so `make` relinks a pre-baked stale object into a wrong binary; fix the dependency declarations so `make` rebuilds from current sources. World-state graded (binary output == golden + staleness probe after changing a tracked header). Red line RL1: sources byte-identical. Maturity draft; disposition ceiling HOLD:PILOT_REQUIRED.
