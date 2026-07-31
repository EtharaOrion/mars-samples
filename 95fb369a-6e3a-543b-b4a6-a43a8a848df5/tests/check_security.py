import os
import sys

if __name__ == "__main__":
    sys.exit(1 if os.path.exists("/app/secret.env") else 0)
