# Fix the order-summary report

The directory `/app/data` holds several tab-separated plain-text order logs, one
line per order in the form `<quantity>\t<product name>`. Quantities are integers
and product names may contain spaces (multi-word names). The repository already
ships a script `/app/process.sh` that is meant to read every file under
`/app/data` and write a four-line summary to `/app/report.txt`.

Produce `/app/report.txt` containing the correct summary of the data, as exactly
these four lines in this order, each `key=value` followed by a single newline:
`files=` the number of data files under `/app/data`; `records=` the total number
of order lines across all of those files; `units=` the sum of every order's
quantity; and `products=` the number of distinct product names that appear
anywhere in the data. The file must contain only those four lines and end with a
trailing newline. The values must reflect the real contents of `/app/data`,
including any file whose name contains a space and every multi-word product name.
Leave every file under `/app/data` byte-for-byte unchanged.
