# compose-healthcheck-restart

Container-setup / AR6 silent-execution. A compose stack looks "up" but a dependent checker races a slow app; agent must add a HEALTHCHECK plus depends_on condition:service_healthy so the checker succeeds on its first attempt. Draft; HOLD:PILOT_REQUIRED.
