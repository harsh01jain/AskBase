import psycopg2
import random
from datetime import datetime, timedelta
import string

DB_USER = "root"
DB_PASS = "rootpassword"
DB_HOST = "127.0.0.1"
DB_PORT = "5433"
DB_NAME = "yourdatabase"

schema_sql = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    segment VARCHAR(50),
    signup_date DATE
);

CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date DATE,
    total_amount DECIMAL(10, 2),
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    product_id INT REFERENCES products(product_id),
    quantity INT,
    unit_price DECIMAL(10, 2)
);

-- Truncate existing data
TRUNCATE TABLE order_items, orders, products, customers RESTART IDENTITY CASCADE;
"""

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters, k=length))

def generate_random_date(start_date, end_date):
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

def seed_db():
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        with conn.cursor() as cur:
            print("Executing schema script...")
            cur.execute(schema_sql)
            
            # Generate Products
            print("Generating Products...")
            categories = ['Software', 'Hardware', 'Services', 'Consulting']
            products = []
            for i in range(50):
                p_name = f"Product {generate_random_string(5)}"
                cat = random.choice(categories)
                price = round(random.uniform(10.0, 500.0), 2)
                products.append((p_name, cat, price))
            
            psql_insert = "INSERT INTO products (name, category, price) VALUES (%s, %s, %s) RETURNING product_id, price"
            cur.executemany("INSERT INTO products (name, category, price) VALUES (%s, %s, %s)", products)
            cur.execute("SELECT product_id, price FROM products")
            product_data = cur.fetchall()
            
            # Generate Customers
            print("Generating Customers...")
            segments = ['Enterprise', 'SMB', 'Startup', 'Mid-Market']
            start_date = datetime(2021, 1, 1)
            end_date = datetime(2024, 1, 1)
            
            customers = []
            for i in range(1000):
                c_name = f"Company {generate_random_string(6)}"
                email = f"contact@{c_name.lower().replace(' ', '')}.com"
                seg = random.choice(segments)
                s_date = generate_random_date(start_date, end_date)
                customers.append((c_name, email, seg, s_date.date()))
                
            cur.executemany("INSERT INTO customers (name, email, segment, signup_date) VALUES (%s, %s, %s, %s)", customers)
            
            # Generate Orders and Order Items
            print("Generating Orders and Items...")
            orders = []
            order_items = []
            
            statuses = ['Completed', 'Pending', 'Cancelled', 'Refunded']
            
            for o_id in range(1, 5001):
                c_id = random.randint(1, 1000)
                o_date = generate_random_date(start_date, end_date)
                status = random.choices(statuses, weights=[70, 20, 5, 5])[0]
                
                # generate 1 to 5 items for this order
                num_items = random.randint(1, 5)
                order_total = 0
                items_for_this_order = []
                for _ in range(num_items):
                    p_id, price = random.choice(product_data)
                    qty = random.randint(1, 10)
                    items_for_this_order.append((o_id, p_id, qty, price))
                    order_total += float(price) * qty
                    
                orders.append((c_id, o_date.date(), order_total, status))
                order_items.extend(items_for_this_order)
                
            cur.executemany("INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES (%s, %s, %s, %s)", orders)
            cur.executemany("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)", order_items)
            
        conn.commit()
        print(f"Database seeded successfully with {len(customers)} customers, {len(products)} products, {len(orders)} orders, and {len(order_items)} items!")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    seed_db()
