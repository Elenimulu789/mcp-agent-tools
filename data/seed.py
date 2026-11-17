"""Build the bundled database from synthetic fixtures in an empty destination."""
from pathlib import Path
import sqlite3

PATH = Path(__file__).with_name("enterprise_ops.db")


def seed(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, account_name TEXT NOT NULL);
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES customers,
                city TEXT NOT NULL,
                sku TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                total_cents INTEGER NOT NULL CHECK (total_cents >= 0)
            );
            CREATE TABLE inventory (
                city TEXT NOT NULL, sku TEXT NOT NULL,
                on_hand INTEGER NOT NULL CHECK (on_hand >= 0),
                PRIMARY KEY (city, sku)
            );
        """)
        cities = ["Seattle", "Portland", "Spokane", "Tacoma"]
        db.executemany("INSERT INTO customers VALUES (?, ?)", [
            (i, f"Fictional account {i:02}") for i in range(1, 9)
        ])
        db.executemany("INSERT INTO inventory VALUES (?, ?, ?)", [
            (city, f"SKU-{90210 + sku}", 80 + city_idx * 7 + sku * 5)
            for city_idx, city in enumerate(cities) for sku in range(4)
        ])
        db.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", [
            (4492 + i, i % 8 + 1, cities[i % 4], f"SKU-{90210 + i % 4}", 24 + i, 248_500 + i * 5_250)
            for i in range(12)
        ])


if __name__ == "__main__":
    if PATH.exists():
        raise SystemExit(f"{PATH.name} already exists. Move it before rebuilding.")
    seed(PATH)
