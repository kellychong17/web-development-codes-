from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'employee-secret-key-12345'

class Product:
    def __init__(self, id=None, name='', brand='', price=0.0, stock=0, image='',
                 description='', nutritional='', ingredients='', allergens='',
                 dimensions='', vegan=0, halal=0, beef=0, gluten_free=0):
        self.id = id
        self.name = name
        self.brand = brand
        self.price = price
        self.stock = stock
        self.image = image
        self.description = description
        self.nutritional = nutritional
        self.ingredients = ingredients
        self.allergens = allergens
        self.dimensions = dimensions
        self.vegan = vegan
        self.halal = halal
        self.beef = beef
        self.gluten_free = gluten_free
    
    def save(self):
        """Create or Update product in database"""
        conn = get_db_connection()
        if self.id:
            # UPDATE existing product
            conn.execute('''
                UPDATE products SET name=?, brand=?, price=?, stock=?, image=?,
                description=?, nutritional=?, ingredients=?, allergens=?,
                dimensions=?, vegan=?, halal=?, beef=?, gluten_free=?
                WHERE id=?
            ''', (self.name, self.brand, self.price, self.stock, self.image,
                  self.description, self.nutritional, self.ingredients, self.allergens,
                  self.dimensions, self.vegan, self.halal, self.beef, self.gluten_free, self.id))
        else:
            # CREATE new product
            conn.execute('''
                INSERT INTO products (name, brand, price, stock, image, description,
                nutritional, ingredients, allergens, dimensions, vegan, halal, beef, gluten_free)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.name, self.brand, self.price, self.stock, self.image,
                  self.description, self.nutritional, self.ingredients, self.allergens,
                  self.dimensions, self.vegan, self.halal, self.beef, self.gluten_free))
        conn.commit()
        conn.close()
    
    def delete(self):
        """Delete product from database"""
        if self.id:
            conn = get_db_connection()
            conn.execute('DELETE FROM products WHERE id=?', (self.id,))
            conn.commit()
            conn.close()
    
    @staticmethod
    def get_all():
        """Retrieve all products"""
        conn = get_db_connection()
        products_raw = conn.execute('SELECT * FROM products ORDER BY id').fetchall()
        conn.close()
        
        products = []
        for p in products_raw:
            product = Product(
                id=p['id'], name=p['name'], brand=p['brand'],
                price=p['price'], stock=p['stock'], image=p['image'],
                description=p['description'], nutritional=p['nutritional'],
                ingredients=p['ingredients'], allergens=p['allergens'],
                dimensions=p['dimensions'], vegan=p['vegan'],
                halal=p['halal'], beef=p['beef'], gluten_free=p['gluten_free']
            )
            products.append(product)
        return products
    
    @staticmethod
    def get_by_id(product_id):
        """Retrieve single product by ID"""
        conn = get_db_connection()
        p = conn.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
        conn.close()
        
        if p:
            return Product(
                id=p['id'], name=p['name'], brand=p['brand'],
                price=p['price'], stock=p['stock'], image=p['image'],
                description=p['description'], nutritional=p['nutritional'],
                ingredients=p['ingredients'], allergens=p['allergens'],
                dimensions=p['dimensions'], vegan=p['vegan'],
                halal=p['halal'], beef=p['beef'], gluten_free=p['gluten_free']
            )
        return None

def get_db_connection():
    conn = sqlite3.connect('store.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with sample products if empty"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            image TEXT,
            description TEXT,
            nutritional TEXT,
            ingredients TEXT,
            allergens TEXT,
            dimensions TEXT,
            vegan INTEGER DEFAULT 0,
            halal INTEGER DEFAULT 0,
            beef INTEGER DEFAULT 0,
            gluten_free INTEGER DEFAULT 0
        )
    ''')
    
    count = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    if count == 0:
        sample_products = [
            ("Blueberry Granola", "Nature's Best", 29.99, 156, 'blueberry_granola.png',
             'A delicious and nutritious granola made with real blueberries.', 
             'Energy: 420 kcal per 100g | Protein: 9g', 'Whole grain oats, blueberries',
             'Contains: Tree nuts', 'Weight: 500g', 0, 1, 0, 0),
            ("Strawberry Jam", "Orchard Fresh", 59.99, 89, 'strawberry_jam.png',
             'Premium strawberry jam.', 'Energy: 250 kcal per 100g',
             'Strawberries, sugar', 'None', 'Weight: 340g', 1, 1, 0, 1),
        ]
        conn.executemany('''
            INSERT INTO products (name, brand, price, stock, image, description,
            nutritional, ingredients, allergens, dimensions, vegan, halal, beef, gluten_free)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_products)
        conn.commit()
    conn.close()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('employee_dashboard.html')

@app.route('/products')
def product_management():
    """Product management page - READ all products"""
    products = Product.get_all()
    return render_template('product_management.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    """Add new product - CREATE"""
    if request.method == 'POST':
        # Get form data
        product = Product(
            name=request.form['name'],
            brand=request.form['brand'],
            price=float(request.form['price']),
            stock=int(request.form['stock']),
            image=request.form.get('image', ''),
            description=request.form.get('description', ''),
            nutritional=request.form.get('nutritional', ''),
            ingredients=request.form.get('ingredients', ''),
            allergens=request.form.get('allergens', ''),
            dimensions=request.form.get('dimensions', ''),
            vegan=1 if request.form.get('vegan') else 0,
            halal=1 if request.form.get('halal') else 0,
            beef=1 if request.form.get('beef') else 0,
            gluten_free=1 if request.form.get('gluten_free') else 0
        )
        

        if not product.name or not product.brand:
            flash('Product name and brand are required!', 'error')
            return render_template('product_form.html', product=product, action='Add')
        
        if product.price <= 0:
            flash('Price must be greater than 0!', 'error')
            return render_template('product_form.html', product=product, action='Add')
        

        product.save()
        flash('Product added successfully!', 'success')
        return redirect(url_for('product_management'))
    
    return render_template('product_form.html', product=Product(), action='Add')

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    """Edit existing product - UPDATE"""
    product = Product.get_by_id(product_id)
    
    if not product:
        flash('Product not found!', 'error')
        return redirect(url_for('product_management'))
    
    if request.method == 'POST':

        product.name = request.form['name']
        product.brand = request.form['brand']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        product.image = request.form.get('image', '')
        product.description = request.form.get('description', '')
        product.nutritional = request.form.get('nutritional', '')
        product.ingredients = request.form.get('ingredients', '')
        product.allergens = request.form.get('allergens', '')
        product.dimensions = request.form.get('dimensions', '')
        product.vegan = 1 if request.form.get('vegan') else 0
        product.halal = 1 if request.form.get('halal') else 0
        product.beef = 1 if request.form.get('beef') else 0
        product.gluten_free = 1 if request.form.get('gluten_free') else 0
        
        if not product.name or not product.brand:
            flash('Product name and brand are required!', 'error')
            return render_template('product_form.html', product=product, action='Edit')
        
        if product.price <= 0:
            flash('Price must be greater than 0!', 'error')
            return render_template('product_form.html', product=product, action='Edit')
        
        # Save to database
        product.save()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('product_management'))
    
    return render_template('product_form.html', product=product, action='Edit')

@app.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """Delete product - DELETE"""
    product = Product.get_by_id(product_id)
    
    if product:
        product.delete()
        flash('Product deleted successfully!', 'success')
    else:
        flash('Product not found!', 'error')
    
    return redirect(url_for('product_management'))

@app.route('/store')
def store():
    products = Product.get_all()
    return render_template('store.html', products=products)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)

