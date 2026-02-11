from app import app, db
from models import Order, OrderItem, RefundRequest, Product, Cart, User
from datetime import datetime

with app.app_context():
    # Create all tables first!
    db.create_all()
    print("✓ Tables created!")
    
    # Now clear old data (only if tables exist)
    try:
        Cart.query.delete()
        RefundRequest.query.delete()
        OrderItem.query.delete()
        Order.query.delete()
        Product.query.delete()
        User.query.delete()
        db.session.commit()
        print("✓ Cleared old data!")
    except:
        print("✓ No old data to clear (fresh database)")
    
    # CREATE USERS FIRST
    user1 = User(
        email='customer@test.com',
        full_name='John Smith',
        phone='+65 1234 5678',
        address='88 Bubblepop lane',
        postal_code='123456',
        is_admin=False
    )
    user1.set_password('password123')
    
    user2 = User(
        email='jane@test.com',
        full_name='Jane Doe',
        phone='+65 9871 2347',
        address='Stayville street 143 #03-25',
        postal_code='143218',
        is_admin=False
    )
    user2.set_password('password123')
    
    admin_user = User(
        email='admin@meod.com',
        full_name='Admin User',
        phone='+65 0000 0000',
        is_admin=True
    )
    admin_user.set_password('admin123')
    
    db.session.add_all([user1, user2, admin_user])
    db.session.commit()
    print(f"✓ Created {User.query.count()} users!")
    print("  📧 customer@test.com / password123")
    print("  📧 jane@test.com / password123")
    print("  🔐 admin@meod.com / admin123 (Admin)")
    
    # CREATE PRODUCTS
    products = [
        Product(name='Strawberry Jam', unit='250g', price=7.00, 
                image_filename='strawberryjam.webp', stock=50, category='Spreads'),
        Product(name='Broccoli', unit='280g', price=4.30, 
                image_filename='broccoli.webp', stock=30, category='Vegetables'),
        Product(name='Blueberry Granola', unit='400g', price=8.50, 
                image_filename='blueberrygranola.jpg', stock=25, category='Breakfast'),
        Product(name='Olive oil', unit='250ml', price=12.00, 
                image_filename='oliveoil.webp', stock=40, category='Oils'),
        Product(name='Garlic', unit='3 pieces', price=2.50, 
                image_filename='garlic.webp', stock=100, category='Vegetables'),
        Product(name='Eggs', unit='10pcs', price=5.80, 
                image_filename='eggs.jpg', stock=60, category='Dairy'),
    ]
    
    for product in products:
        db.session.add(product)
    
    db.session.commit()
    print(f"✓ Created {len(products)} products!")
    
    # Get products from database
    product_olive = Product.query.filter_by(name='Olive oil').first()
    product_garlic = Product.query.filter_by(name='Garlic').first()
    product_eggs = Product.query.filter_by(name='Eggs').first()
    product_jam = Product.query.filter_by(name='Strawberry Jam').first()
    product_broccoli = Product.query.filter_by(name='Broccoli').first()
    
    # Create sample order #1410 for user1
    order1 = Order(
        order_number='1410',
        user_id=user1.id,
        customer_name=user1.full_name,
        customer_phone=user1.phone,
        customer_email=user1.email,
        delivery_address=user1.address,
        postal_code=user1.postal_code,
        total_price=20.30,
        delivery_date=datetime(2025, 4, 16, 12, 45),
        order_status='Delivered'
    )
    db.session.add(order1)
    db.session.flush()
    print(f"✓ Created order #{order1.order_number} for {user1.email}")
    
    # Add items for order #1410
    item1 = OrderItem(
        order_id=order1.id, 
        product_id=product_olive.id,
        item_name=product_olive.name, 
        quantity=product_olive.unit, 
        price=product_olive.price
    )
    item2 = OrderItem(
        order_id=order1.id, 
        product_id=product_garlic.id,
        item_name=product_garlic.name, 
        quantity=product_garlic.unit, 
        price=product_garlic.price
    )
    item3 = OrderItem(
        order_id=order1.id, 
        product_id=product_eggs.id,
        item_name=product_eggs.name, 
        quantity=product_eggs.unit, 
        price=product_eggs.price
    )
    db.session.add_all([item1, item2, item3])
    
    refund1 = RefundRequest(
        order_id=order1.id,
        refund_reason='I received the wrong items.',
        status='Rejected'
    )
    db.session.add(refund1)
    
    # Create sample order #1412 for user2
    order2 = Order(
        order_number='1412',
        user_id=user2.id,
        customer_name=user2.full_name,
        customer_phone=user2.phone,
        customer_email=user2.email,
        delivery_address=user2.address,
        postal_code=user2.postal_code,
        total_price=11.30,
        delivery_date=datetime(2025, 4, 22, 17, 20),
        order_status='Out for Delivery'
    )
    db.session.add(order2)
    db.session.flush()
    print(f"✓ Created order #{order2.order_number} for {user2.email}")
    
    # Add items for order #1412
    item4 = OrderItem(
        order_id=order2.id, 
        product_id=product_jam.id,
        item_name=product_jam.name, 
        quantity=product_jam.unit, 
        price=product_jam.price
    )
    item5 = OrderItem(
        order_id=order2.id, 
        product_id=product_broccoli.id,
        item_name=product_broccoli.name, 
        quantity=product_broccoli.unit, 
        price=product_broccoli.price
    )
    db.session.add_all([item4, item5])
    
    refund2 = RefundRequest(
        order_id=order2.id,
        refund_reason='Product arrived damaged.',
        status='Pending'
    )
    db.session.add(refund2)
    
    db.session.commit()
    print("\n" + "="*50)
    print("✓ SAMPLE DATA CREATED SUCCESSFULLY!")
    print("="*50)
    print(f"📊 Total users: {User.query.count()}")
    print(f"📦 Total products: {Product.query.count()}")
    print(f"🛒 Total orders: {Order.query.count()}")
    print(f"📝 Total order items: {OrderItem.query.count()}")
    print(f"💰 Total refund requests: {RefundRequest.query.count()}")
    print("="*50)
    print("\n🔑 LOGIN CREDENTIALS:")
    print("   Customer: customer@test.com / password123")
    print("   Customer: jane@test.com / password123")
    print("   Admin: admin@meod.com / admin123")
    print("="*50)