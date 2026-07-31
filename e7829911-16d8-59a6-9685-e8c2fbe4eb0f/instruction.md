# Normalize a mixed-encoding text corpus

The directory `/app/corpus` holds several plain-text files that were collected
from different systems. They are inconsistent in two ways: their byte encoding
varies (some are UTF-8, some carry a leading UTF-8 byte-order mark, and some are
Latin-1 / ISO-8859-1 containing bytes above 127 such as accented letters or a
pound sign), and their line endings are a mix of CRLF, lone CR, and LF.

Produce a directory `/app/normalized` that contains, for every file in
`/app/corpus`, a normalized copy under the same relative filename. Build each
normalized file with this exact deterministic rule: take the source bytes, and
if they begin with a single leading UTF-8 byte-order mark remove that mark; if
the resulting bytes are valid UTF-8, decode them as UTF-8, otherwise decode the
original bytes as Latin-1 (ISO-8859-1). Then convert every line ending to a
single LF (`\n`) - both CRLF pairs and any remaining lone CR become LF - and
write the text back out as UTF-8 with no byte-order mark. Each
`/app/normalized/<name>` must be byte-for-byte the correct normalization of the
matching `/app/corpus/<name>`. Leave every file under `/app/corpus` unchanged.
