# Normalise a batch of awkward filenames

The directory `/app/inbox` contains a fixed set of files whose names include
awkward characters: embedded spaces, a leading dash, a trailing space before the
extension, mixed case, and non-ASCII letters. Every file must be renamed into a
canonical "slug" form and the renamed copies must be written into `/app/out`
(create it if needed). The original bytes of every file's contents must be
carried across unchanged.

Compute each output name from the original name with this exact, deterministic
rule. First split off the final filename extension (the last `.` and everything
after it) and set it aside. Lowercase the remaining stem. In that lowercased
stem, replace every maximal run of characters that are not ASCII letters
(`a`-`z`), ASCII digits (`0`-`9`), or a dot (`.`) with a single `-`, then strip
any leading or trailing `-`. Re-attach the original extension, lowercased. If two
or more originals produce the same output name, sort those colliding originals by
their original filename in ascending order: the first keeps the plain name and
each later one gets `-1`, `-2`, ... inserted just before the extension. The final
`/app/out` directory must contain exactly one output file per input file, each
holding the exact contents of the input it came from.
