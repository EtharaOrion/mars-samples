import sys
from pathlib import Path

from app.core import config


def expected_revision():
    marker = Path(__file__).resolve().parent / "core" / "REVISION"
    return marker.read_text().strip()


def check():
    revision_ok = getattr(config, "CONFIG_REVISION", None) == expected_revision()
    flags_ok = isinstance(getattr(config, "FEATURE_FLAGS", None), tuple)
    salt_ok = bool(getattr(config, "SECRET_SALT", ""))
    service_ok = bool(getattr(config, "SERVICE_NAME", ""))
    return revision_ok and flags_ok and salt_ok and service_ok


def main():
    return 0 if check() else 1


if __name__ == "__main__":
    sys.exit(main())
