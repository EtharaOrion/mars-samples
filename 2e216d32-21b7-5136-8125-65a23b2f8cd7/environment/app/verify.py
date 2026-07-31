import sys
import alpha
import beta
import common

value = alpha.a() + beta.b()
expected = 314
if value != expected:
    sys.stderr.write(
        "verify failed: got %r expected %r (common=%s alpha=%s beta=%s)\n"
        % (value, expected, common.__version__, alpha.__version__, beta.__version__)
    )
    sys.exit(1)
print("verify ok:", value)
sys.exit(0)
