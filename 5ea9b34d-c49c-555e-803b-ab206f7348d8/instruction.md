# Provision a shared engineering directory with exact access control

The directory `/app/shared` already exists but is otherwise unconfigured. Create a
group named `engineers` and three login users: `alice` and `bob`, both of whom are
members of `engineers`, and `carol`, who must NOT be a member of `engineers`. Then
create the directory `/app/shared/proj`. That directory must be owned by user `root`
and group `engineers` and carry mode `2770` (the setgid bit set, group `rwx`, no
access for others), so that any new file created inside it automatically inherits the
group `engineers`. Grant user `carol` a POSIX access ACL of `r-x` on `/app/shared/proj`
(read and traverse, but no write) without adding her to the group; the ACL mask must
leave that `r-x` effective.

Inside `/app/shared/proj` create a file `secret.txt` owned by user `alice` and group
`engineers` with mode `0640`, so members of `engineers` may read it but it is not
readable or writable by others. The final world-state must satisfy this access matrix
exactly: `alice` and `bob` can read `secret.txt`; a new file that `alice` creates under
`/app/shared/proj` comes out with group `engineers`; `carol` can list and enter
`/app/shared/proj` but cannot create files there and cannot read `secret.txt`. Leave
`/app/shared` itself traversable (mode `0755`, owner `root:root`) so the users can
reach `proj`.
