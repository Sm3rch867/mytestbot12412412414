import sqlite3

def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    # Таблица товаров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price INTEGER NOT NULL,
            sizes TEXT NOT NULL,
            image_path TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # Проверяем, заполнена ли база, если нет — добавляем тестовые товары
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ("Худи Stussy", "Худи", 1999, "S, M, L, XL", "images/hudi.png", "Стильное и удобное оверсайз худи Stussy."),
            ("Джинсы Grey Wash", "Джинсы", 1000, "S, M, L, XL", "images/jeans.png", "Классические широкие джинсы серого цвета."),
            ("Кроссовки Asics GEL", "Кроссовки", 5000, "40, 41, 42, 43, 44, 45", "images/sneakers.png", "Удобные кроссовки для ежедневной носки и спорта.")
        ]
        cursor.executemany('''
            INSERT INTO products (name, category, price, sizes, image_path, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)
        
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM products')
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def get_products_by_category(category):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price FROM products WHERE category = ?', (category,))
    products = cursor.fetchall()
    conn.close()
    return products

def get_product(product_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, category, price, sizes, image_path, description FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product
