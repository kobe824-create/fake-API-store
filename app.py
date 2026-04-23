from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests as http_requests

app = Flask(__name__)
app.secret_key = 'shopvault-secret-key-2026'

# ── Cache for API data ──
_products_cache = None

def get_all_products():
    """Fetch products from FakeStore API (cached in memory)."""
    global _products_cache
    if _products_cache is None:
        try:
            resp = http_requests.get('https://fakestoreapi.com/products', timeout=10)
            resp.raise_for_status()
            _products_cache = resp.json()
        except Exception:
            _products_cache = []
    return _products_cache

def get_product_by_id(product_id):
    """Find a single product by ID from the cached list."""
    for p in get_all_products():
        if p['id'] == product_id:
            return p
    return None

def get_categories():
    """Get unique category names from products."""
    return sorted(set(p['category'] for p in get_all_products()))

def login_required(f):
    """Simple decorator to guard routes behind login."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated

# ── Auth Routes ──

@app.route('/')
def home():
    if session.get('logged_in'):
        return redirect(url_for('store'))
    return render_template('app.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    # Simple check for demo purposes
    if username == 'admin' and password == 'password':
        session['logged_in'] = True
        session['cart'] = []
        flash('Welcome back!', 'success')
        return redirect(url_for('store'))
    else:
        return render_template('app.html', error='Invalid credentials. Please try again.')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ── Store Routes ──

@app.route('/store')
@login_required
def store():
    products = get_all_products()
    categories = get_categories()
    active_category = request.args.get('category')
    if active_category:
        products = [p for p in products if p['category'] == active_category]

    # Convert dicts to SimpleNamespace for dot-access in templates
    from types import SimpleNamespace
    def to_ns(p):
        ns = SimpleNamespace(**p)
        ns.rating = SimpleNamespace(**p['rating'])
        return ns

    products_ns = [to_ns(p) for p in products]
    return render_template('store.html',
                           products=products_ns,
                           categories=categories,
                           active_category=active_category)

@app.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('store'))

    from types import SimpleNamespace
    p = SimpleNamespace(**product)
    p.rating = SimpleNamespace(**product['rating'])
    return render_template('product.html', product=p)

# ── Cart Routes ──

@app.route('/cart')
@login_required
def cart():
    cart_items = session.get('cart', [])
    from types import SimpleNamespace
    items = [SimpleNamespace(**item) for item in cart_items]
    total = sum(item.price * item.qty for item in items)
    return render_template('cart.html', cart_items=items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def cart_add(product_id):
    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('store'))

    cart = session.get('cart', [])
    # Check if already in cart
    for item in cart:
        if item['id'] == product_id:
            item['qty'] += 1
            session['cart'] = cart
            flash(f'Updated quantity for "{product["title"]}"', 'success')
            return redirect(request.referrer or url_for('store'))

    cart.append({
        'id': product['id'],
        'title': product['title'],
        'price': product['price'],
        'image': product['image'],
        'qty': 1
    })
    session['cart'] = cart
    flash(f'Added "{product["title"]}" to cart!', 'success')
    return redirect(request.referrer or url_for('store'))

@app.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def cart_update(product_id):
    action = request.form.get('action')
    cart = session.get('cart', [])
    for item in cart:
        if item['id'] == product_id:
            if action == 'increase':
                item['qty'] += 1
            elif action == 'decrease':
                item['qty'] -= 1
                if item['qty'] <= 0:
                    cart.remove(item)
            break
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def cart_remove(product_id):
    cart = session.get('cart', [])
    cart = [item for item in cart if item['id'] != product_id]
    session['cart'] = cart
    flash('Item removed from cart.', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    cart_items = session.get('cart', [])
    if not cart_items:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('cart'))

    from types import SimpleNamespace
    items = [SimpleNamespace(**item) for item in cart_items]
    total = sum(item.price * item.qty for item in items)
    session['cart'] = []
    return render_template('checkout.html', order_items=items, total=total)

if __name__ == '__main__':
    app.run(debug=True)