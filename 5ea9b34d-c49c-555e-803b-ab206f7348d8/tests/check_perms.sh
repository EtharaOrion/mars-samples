#!/bin/sh
# Static world-state checks: ownership, mode bits, ACL entries, group membership.
fail() { echo "FAIL: $1"; exit 1; }

PROJ=/app/shared/proj
SECRET=/app/shared/proj/secret.txt

# --- group + membership (id) ---
getent group engineers >/dev/null 2>&1 || fail "group engineers missing"
id alice >/dev/null 2>&1 || fail "user alice missing"
id bob   >/dev/null 2>&1 || fail "user bob missing"
id carol >/dev/null 2>&1 || fail "user carol missing"
id -nG alice | tr ' ' '\n' | grep -qx engineers || fail "alice not in engineers"
id -nG bob   | tr ' ' '\n' | grep -qx engineers || fail "bob not in engineers"
if id -nG carol | tr ' ' '\n' | grep -qx engineers; then fail "carol must NOT be in engineers"; fi

# --- /app/shared traversable ---
[ -d /app/shared ] || fail "/app/shared missing"
[ "$(stat -c '%U:%G' /app/shared)" = "root:root" ] || fail "/app/shared not root:root"
[ "$(stat -c '%a' /app/shared)" = "755" ] || fail "/app/shared not mode 755"

# --- proj dir: root:engineers, mode 2770 ---
[ -d "$PROJ" ] || fail "proj dir missing"
[ "$(stat -c '%U' "$PROJ")" = "root" ] || fail "proj owner not root"
[ "$(stat -c '%G' "$PROJ")" = "engineers" ] || fail "proj group not engineers"
[ "$(stat -c '%a' "$PROJ")" = "2770" ] || fail "proj mode not 2770 (got $(stat -c '%a' "$PROJ"))"

# --- carol ACL r-x present and effective on proj ---
getfacl -p "$PROJ" 2>/dev/null | grep -q '^user:carol:r-x' || fail "carol ACL r-x missing on proj"
# mask must permit at least r-x (mask r-x or rwx)
MASK=$(getfacl -p "$PROJ" 2>/dev/null | sed -n 's/^mask::\(.*\)/\1/p')
case "$MASK" in
  r-x|rwx) : ;;
  *) fail "ACL mask does not leave carol r-x effective (mask=$MASK)" ;;
esac

# --- secret.txt: alice:engineers, mode 0640 ---
[ -f "$SECRET" ] || fail "secret.txt missing"
[ "$(stat -c '%U' "$SECRET")" = "alice" ] || fail "secret.txt owner not alice"
[ "$(stat -c '%G' "$SECRET")" = "engineers" ] || fail "secret.txt group not engineers"
[ "$(stat -c '%a' "$SECRET")" = "640" ] || fail "secret.txt mode not 640 (got $(stat -c '%a' "$SECRET"))"

echo "check_perms: OK"
exit 0
