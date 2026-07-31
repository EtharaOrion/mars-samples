# Merge layered configuration fragments

The directory `/app/config` holds several JSON fragment files
(`00-base.json`, `10-env.json`, `20-override.json`, ...). They must be combined,
in ascending filename order, into a single effective configuration written to
`/app/merged.json`.

Combine the fragments with these exact rules, applied fragment by fragment in
order. When both the accumulated result and the incoming fragment hold an object
at the same key, merge those objects recursively. When the incoming value is
anything other than an object - a string, number, boolean, or array - it
replaces the accumulated value entirely (arrays are not concatenated). When the
incoming value is JSON `null`, the key is deleted from the result rather than set
to null. The final `/app/merged.json` must contain the fully merged object and
nothing else. Do not modify any file under `/app/config`.
