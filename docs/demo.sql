-- Synthetic, non-sensitive demo data. Import into a new SQLite database.
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    price REAL,
    quantity INTEGER
);
INSERT OR IGNORE INTO products VALUES
    (1, 'Notebook', 'stationery', 4.5, 12),
    (2, 'Pen', 'stationery', 1.2, 40),
    (3, 'Mug', 'kitchen', 8.9, 8),
    (4, 'Plate', 'kitchen', 6.0, 15),
    (5, 'Lamp', 'lighting', 29.0, 3);

SELECT category, COUNT(*) AS products,
       ROUND(SUM(price * quantity), 2) AS stock_value
FROM products
GROUP BY category
ORDER BY category;
