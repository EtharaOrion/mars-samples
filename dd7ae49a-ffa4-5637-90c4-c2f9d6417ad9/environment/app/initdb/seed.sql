CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    status TEXT NOT NULL
);

INSERT INTO orders (id, customer, amount_cents, status) VALUES
    (7, 'Grace Hopper', 42000, 'pending'),
    (42, 'Ada Lovelace', 189900, 'shipped'),
    (99, 'Alan Turing', 512500, 'delivered')
ON CONFLICT (id) DO NOTHING;
