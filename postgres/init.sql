
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert base product data
INSERT INTO products (id, name, price, stock, category, description) VALUES
(1, 'Laptop Pro', 1499.0, 10, 'laptop', '15" performance laptop'),
(2, 'Mouse', 29.0, 200, 'accessories', 'Wireless ergonomic mouse'),
(3, 'Keyboard', 79.0, 120, 'accessories', 'Mechanical keyboard'),
(4, 'Monitor 27"', 329.0, 45, 'monitor', '27" QHD IPS monitor'),
(5, 'Headset', 119.0, 80, 'audio', 'Wireless noise-cancelling headset'),
(6, 'Webcam 4K', 149.0, 60, 'accessories', '4K streaming webcam'),
(7, 'Docking Station', 199.0, 35, 'accessories', 'USB-C docking station'),
(8, 'SSD 1TB', 129.0, 150, 'storage', 'NVMe 1TB SSD'),
(9, 'GPU External', 799.0, 8, 'gpu', 'External GPU enclosure'),
(10, 'Laptop Air', 999.0, 25, 'laptop', '13" ultrabook'),
(11, 'Smartphone Plus', 899.0, 55, 'phone', '6.7" OLED smartphone'),
(12, 'Tablet Max', 649.0, 40, 'tablet', '12" tablet with pen'),
(13, 'Charger 100W', 59.0, 300, 'accessories', 'GaN fast charger'),
(14, 'Router WiFi 6', 179.0, 70, 'network', 'WiFi 6 tri-band router'),
(15, 'NAS 4-bay', 549.0, 15, 'storage', '4-bay NAS with RAID'),
(16, 'Printer Laser', 229.0, 50, 'printer', 'Duplex laser printer'),
(17, 'Smartwatch', 249.0, 90, 'wearable', 'Fitness smartwatch'),
(18, 'Earbuds Pro', 159.0, 180, 'audio', 'ANC true wireless earbuds'),
(19, 'Projector 1080p', 399.0, 22, 'display', 'Portable 1080p projector'),
(20, 'Action Cam', 299.0, 65, 'camera', '4K action camera')
ON CONFLICT (id) DO NOTHING;

SELECT setval('products_id_seq', (SELECT MAX(id) FROM products));

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
