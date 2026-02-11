from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, jsonify
from models import db, RefundRequest, Order, OrderItem, Product, Cart, User
from datetime import datetime
from functools import wraps
import os
import secrets

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meod.db'
app.config['SQLALCHEMY_TRACK_IFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

db.init_app(app)

# Generate session ID for guest users
@app.before_request
def create_session():
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)

# ===== AUTH HELPERS =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('customer_login'))

        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('customer_homepage'))
        return f(*args, **kwargs)
    return decorated_function

# ===== AUTH ROUTES =====
@app.route('/customerloginpage', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        username = request.form.get('username')  # you use email as username
        password = request.form.get('password')

        user = User.query.filter_by(email=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('customer_homepage'))
        else:
            return render_template('customerloginpage.html', error='Invalid username or password')

    success = request.args.get('success')
    return render_template('customerloginpage.html', success=success)

@app.route('/customersignup', methods=['GET', 'POST'])
def customer_signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not password or len(password) < 8:
            return render_template('customersignup.html', error='Password must be at least 8 characters')

        existing_user = User.query.filter_by(email=username).first()
        if existing_user:
            return render_template('customersignup.html', error='Username already exists')

        new_user = User(email=username, full_name=username, is_admin=False)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('customer_login', success='true'))

    return render_template('customersignup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('customer_login'))

# ===== MAIN / HOME =====
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('customer_homepage'))
    return redirect(url_for('customer_login'))

@app.route('/customer-homepage')
@login_required
def customer_homepage():
    user = User.query.get(session['user_id'])
    return render_template('customerhomepage.html', user=user)

@app.route('/admin')
@admin_required
def admin_page():
    return render_template('adminpage.html')

@app.route('/employee-homepage')
def employee_homepage():
    return render_template('employeehomepage.html')

# ===== PRODUCTS =====
@app.route('/products')
@login_required
def products():
    all_products = Product.query.all()
    return render_template('products.html', products=all_products)

# ===== CART =====
@app.route('/cart')
@login_required
def shopping_cart():
    user_id = session.get('user_id')
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    return render_template('shopping_cart.html', cart_items=cart_items)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    user_id = session.get('user_id')
    product = Product.query.get_or_404(product_id)

    cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = Cart(
            user_id=user_id,
            product_id=product_id,
            quantity=1,
            selected=True
        )
        db.session.add(cart_item)

    db.session.commit()
    flash('Item added to cart!', 'success')
    return redirect(url_for('shopping_cart'))

@app.route('/cart/update/<int:cart_id>', methods=['POST'])
@login_required
def update_cart(cart_id):
    data = request.get_json() or {}
    cart_item = Cart.query.get_or_404(cart_id)

    if cart_item.user_id != session.get('user_id'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    if 'quantity' in data:
        try:
            quantity = int(data['quantity'])
        except:
            quantity = cart_item.quantity

        if quantity > 0:
            cart_item.quantity = quantity
        else:
            db.session.delete(cart_item)

    if 'selected' in data:
        cart_item.selected = bool(data['selected'])

    db.session.commit()
    return jsonify({'success': True})

@app.route('/cart/remove/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)

    if cart_item.user_id != session.get('user_id'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/cart/proceed', methods=['POST'])
@login_required
def cart_proceed():
    user_id = session.get('user_id')
    cart_items = Cart.query.filter_by(user_id=user_id, selected=True).all()

    if not cart_items:
        flash('No items selected', 'error')
        return redirect(url_for('shopping_cart'))

    session['pending_order_items'] = [
        {
            'product_id': item.product_id,
            'name': item.product.name,
            'unit': item.product.unit,
            'price': float(item.product.price),  # unit price
            'quantity': int(item.quantity),
            'image': item.product.image_filename
        }
        for item in cart_items
    ]

    return redirect(url_for('order_summary_page'))

@app.route('/apply-promo', methods=['POST'])
@login_required
def apply_promo():
    data = request.get_json() or {}
    discount = data.get('discount', 0)

    try:
        discount = float(discount)
    except:
        discount = 0.0

    session['promo_discount'] = discount
    return jsonify({'success': True})

# ===== ORDER SUMMARY / CHECKOUT =====
def _calc_pending_totals(pending_items):
    items_total = sum(float(i['price']) * int(i['quantity']) for i in pending_items)
    delivery_fee = 10.00
    discount = float(session.get('promo_discount', 0) or 0)
    grand_total = max(0.0, items_total + delivery_fee - discount)
    return items_total, delivery_fee, discount, grand_total

@app.route('/order-summary')
@login_required
def order_summary_page():
    pending_items = session.get('pending_order_items', [])
    if not pending_items:
        return redirect(url_for('shopping_cart'))

    user = User.query.get(session['user_id'])
    items_total, delivery_fee, discount, grand_total = _calc_pending_totals(pending_items)

    return render_template(
        'order_summary.html',
        items=pending_items,
        user=user,
        items_total=items_total,
        delivery_fee=delivery_fee,
        discount=discount,
        grand_total=grand_total
    )

@app.route('/checkout-page')
@login_required
def checkout_page():
    pending_items = session.get('pending_order_items', [])
    if not pending_items:
        return redirect(url_for('shopping_cart'))

    user = User.query.get(session['user_id'])
    items_total, delivery_fee, discount, grand_total = _calc_pending_totals(pending_items)

    return render_template(
        'checkout.html',
        items=pending_items,
        user=user,
        items_total=items_total,
        delivery_fee=delivery_fee,
        discount=discount,
        grand_total=grand_total
    )

@app.route('/place-order', methods=['POST'])
@login_required
def place_order():
    pending_items = session.get('pending_order_items', [])
    user_id = session.get('user_id')

    if not pending_items:
        flash('No items to order', 'error')
        return redirect(url_for('shopping_cart'))

    customer_name = request.form.get('customer_name')
    customer_phone = request.form.get('customer_phone')
    customer_email = request.form.get('customer_email')
    delivery_address = request.form.get('delivery_address')
    postal_code = request.form.get('postal_code')
    delivery_date_str = request.form.get('delivery_date')
    delivery_time = request.form.get('delivery_time')

    items_total, delivery_fee, discount, grand_total = _calc_pending_totals(pending_items)

    # unique order no
    order_number = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{user_id}"

    delivery_date = None
    try:
        if delivery_date_str and delivery_time:
            delivery_date = datetime.strptime(f"{delivery_date_str} {delivery_time}", "%d/%m/%Y %H:%M")
    except:
        delivery_date = None

    order = Order(
        order_number=order_number,
        user_id=user_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        delivery_address=delivery_address,
        postal_code=postal_code,
        total_price=grand_total,
        delivery_date=delivery_date,
        order_status='Order Placed',
        created_at=datetime.utcnow()
    )

    db.session.add(order)
    db.session.flush()  # order.id available

    for item_data in pending_items:
        # IMPORTANT: quantity uses item_data['quantity'], NOT unit
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data['product_id'],
            item_name=item_data['name'],
            quantity=int(item_data['quantity']),
            price=float(item_data['price'])  # unit price
        )
        db.session.add(order_item)

        Cart.query.filter_by(user_id=user_id, product_id=item_data['product_id']).delete()

    db.session.commit()

    session.pop('pending_order_items', None)
    session.pop('promo_discount', None)
    session['last_order_id'] = order.id

    return redirect(url_for('order_confirmation'))

@app.route('/order-confirmation')
@login_required
def order_confirmation():
    order_id = session.get('last_order_id')
    if not order_id:
        return redirect(url_for('customer_homepage'))

    order = Order.query.get_or_404(order_id)

    if order.user_id != session.get('user_id'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('customer_homepage'))

    return render_template('confirmation_page.html', order=order)

# ===== CUSTOMER ORDERS =====
@app.route('/order-history')
@login_required
def order_history():
    user_id = session.get('user_id')
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    return render_template('order_history.html', orders=orders)

@app.route('/order/<int:order_id>/status')
@login_required
def order_status(order_id):
    order = Order.query.get_or_404(order_id)

    if order.user_id != session.get('user_id') and not session.get('is_admin'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('customer_homepage'))

    return render_template('order_status.html', order=order)

@app.route('/order/<int:order_id>/summary')
@login_required
def order_summary(order_id):
    order = Order.query.get_or_404(order_id)

    if order.user_id != session.get('user_id'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('order_history'))

    # reuse the same order_summary.html if you want, or create another template
    return render_template('order_summary.html', order=order)

# ===== ADMIN ORDER MANAGEMENT =====
@app.route('/order-management')
@admin_required
def order_management():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('order_management.html', orders=orders)

# ⭐ NEW: ADMIN UPDATE ORDER STATUS
@app.route('/admin/order/<int:order_id>/update-status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)

    new_status = request.form.get('order_status', '').strip()
    allowed = {'Order Placed', 'Order Confirmed', 'Out for Delivery', 'Delivered'}

    if new_status not in allowed:
        flash('Invalid status selected.', 'error')
        return redirect(url_for('order_management'))

    order.order_status = new_status
    db.session.commit()

    flash(f'Order #{order.order_number} updated to: {new_status}', 'success')
    return redirect(url_for('order_management'))

# ===== REFUNDS =====
@app.route('/refund')
@login_required
def refund_lookup():
    return render_template('refund_lookup.html')

@app.route('/refund/search', methods=['POST'])
@login_required
def search_order():
    user_id = session.get('user_id')
    order_number = request.form.get('order_number')

    order = Order.query.filter_by(order_number=order_number, user_id=user_id).first()
    if order:
        return redirect(url_for('refund_form', order_id=order.id))

    flash('Order not found. Please check your order number.', 'error')
    return redirect(url_for('refund_lookup'))

@app.route('/order/<int:order_id>/refund')
@login_required
def refund_form(order_id):
    order = Order.query.get_or_404(order_id)

    if order.user_id != session.get('user_id'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('order_history'))

    return render_template('refund_form.html', order=order)

@app.route('/order/<int:order_id>/refund/submit', methods=['POST'])
@login_required
def submit_refund(order_id):
    """Submit a new refund request"""
    order = Order.query.get_or_404(order_id)

    if order.user_id != session.get('user_id'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('order_history'))

    refund_reason = request.form.get('refund_reason')
    customer_name = request.form.get('customer_name')
    customer_phone = request.form.get('customer_phone')
    customer_email = request.form.get('customer_email')

    # Update order contact details (optional)
    order.customer_name = customer_name
    order.customer_phone = customer_phone
    order.customer_email = customer_email

    # Create refund request
    refund_request = RefundRequest(
        order_id=order.id,
        refund_reason=refund_reason,
        status='Pending'
    )

    db.session.add(refund_request)
    db.session.commit()

    # ✅ Store for confirmation page
    session['last_refund_request_id'] = refund_request.id

    # ✅ Go to refund confirmation page
    return redirect(url_for('refund_confirmation'))

@app.route('/refund-confirmation')
@login_required
def refund_confirmation():
    """Refund confirmation page after customer submits refund request"""
    refund_id = session.get('last_refund_request_id')
    if not refund_id:
        return redirect(url_for('order_history'))

    refund_req = RefundRequest.query.get_or_404(refund_id)

    # Safety: make sure the refund belongs to the logged-in user
    if refund_req.order.user_id != session.get('user_id'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('order_history'))

    # Use your uploaded template name
    return render_template('refundconfirmation.html', refund_request=refund_req)

@app.route('/refund-requests')
@admin_required
def refund_requests():
    requests = RefundRequest.query.join(Order).order_by(RefundRequest.requested_at.desc()).all()
    return render_template('refund_requests.html', requests=requests)

@app.route('/refund-request/<int:request_id>')
@admin_required
def view_refund_request(request_id):
    refund_req = RefundRequest.query.get_or_404(request_id)
    return render_template('refund_detail.html', refund_request=refund_req)

@app.route('/refund-request/<int:request_id>/approve', methods=['POST'])
@admin_required
def approve_refund(request_id):
    refund_req = RefundRequest.query.get_or_404(request_id)
    refund_req.status = 'Approved'
    refund_req.processed_at = datetime.utcnow()
    refund_req.processed_by = session.get('user_name', 'Admin')

    db.session.commit()
    flash('Refund request approved successfully!', 'success')
    return redirect(url_for('refund_requests'))

@app.route('/refund-request/<int:request_id>/reject', methods=['POST'])
@admin_required
def reject_refund(request_id):
    refund_req = RefundRequest.query.get_or_404(request_id)
    refund_req.status = 'Rejected'
    refund_req.processed_at = datetime.utcnow()
    refund_req.processed_by = session.get('user_name', 'Admin')

    db.session.commit()
    flash('Refund request rejected.', 'warning')
    return redirect(url_for('refund_requests'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
