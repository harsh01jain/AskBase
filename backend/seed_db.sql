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

TRUNCATE TABLE order_items, orders, products, customers RESTART IDENTITY CASCADE;

INSERT INTO customers (name, email, segment, signup_date) VALUES
('Alice Smith', 'alice@example.com', 'Enterprise', '2023-01-15'),
('Bob Johnson', 'bob@example.com', 'SMB', '2023-03-22'),
('Charlie Brown', 'charlie@example.com', 'Startup', '2023-06-10');

INSERT INTO products (name, category, price) VALUES
('Pro Subscription', 'Software', 99.99),
('Basic Subscription', 'Software', 29.99),
('Consulting Hour', 'Service', 150.00);

INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
(1, '2023-02-01', 99.99, 'Completed'),
(1, '2023-03-01', 99.99, 'Completed'),
(2, '2023-04-15', 29.99, 'Completed'),
(3, '2023-06-15', 150.00, 'Pending');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 99.99),
(2, 1, 1, 99.99),
(3, 2, 1, 29.99),
(4, 3, 1, 150.00);
