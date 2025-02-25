from flask import Flask, render_template, request, redirect, url_for, session
import json
import stripe
import os
from dotenv import load_dotenv

load_dotenv()

def load_products():
    with open("product.json") as file:
        return json.load(file)

products = load_products()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

stripe.api_key = os.environ["API_KEY"]


@app.route('/')
def home():
    cart_items = session.get("cart", [])
    cart_quantity = sum(item["quantity"] for item in cart_items)
    return render_template("index.html", products=products, cart_quantity=cart_quantity)

@app.route('/cart')
def cart():
    cart_items = session.get("cart", [])
    sum_cart = 0
    cart_quantity = 0
    if cart_items:
        for item in cart_items:
           sum_cart += item["quantity"] * item["price"]
           cart_quantity += item["quantity"]
    return render_template("cart.html", cart=cart_items,cart_quantity=cart_quantity, sum_cart="{:.2f}".format(sum_cart))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        return redirect(url_for('home'))

    quantity = int(request.form.get("quantity", 1))

    cart = session.get("cart", [])
    found = False

    for item in cart:
        if item["id"] == product["id"]:
            item["quantity"] += quantity
            found = True
            break

    if not found:
        product["quantity"] = quantity
        cart.append(product)

    session["cart"] = cart
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    cart = session.get("cart", [])
    new_quantity = int(request.form.get("quantity", 1))

    for item in cart:
        if item["id"] == product_id:
            item["quantity"] = max(1, new_quantity)  # Množstvo musí byť aspoň 1
            break

    session["cart"] = cart
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get("cart", [])
    cart = [item for item in cart if item["id"] != product_id]

    session["cart"] = cart
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST','GET'])
def checkout():
    cart = session.get("cart", [])
    if not cart:
        return redirect(url_for('home'))

    # Vytvorenie Stripe Checkout session
    line_items = [{
        "price_data": {
            "currency": "eur",
            "product_data": {
                "name": item["name"],
            },
            "unit_amount": int(float(item["price"]) * 100),  # Stripe používa centy
        },
        "quantity": item["quantity"],
    } for item in cart]

    stripe_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        shipping_address_collection={"allowed_countries": ["SK", "CZ", "DE"]},
        shipping_options=[
            {
                "shipping_rate_data": {
                    "display_name": "Standard Shipping",
                    "type": "fixed_amount",
                    "fixed_amount": {
                        "amount": 500,  # 5.00 €
                        "currency": "eur",
                    },
                    "delivery_estimate": {
                        "minimum": {"unit": "business_day", "value": 3},
                        "maximum": {"unit": "business_day", "value": 7},
                    },
                }
            }
        ],
        line_items=line_items,
        mode='payment',
        success_url=url_for('success', _external=True),
        cancel_url=url_for('cart', _external=True),
    )

    return redirect(stripe_session.url, code=303)

@app.route('/success')
def success():
    session["cart"] = []  # Vyprázdni košík po úspešnej platbe
    return "Payment successful! Thank you for your purchase."


@app.route('/product/<int:product_id>')
def show_product(product_id):
    cart_items = session.get("cart", [])
    cart_quantity = sum(item["quantity"] for item in cart_items)
    if product_id == 1:
        return render_template("product-1.html", product_id=product_id, cart_quantity=cart_quantity)
    elif product_id ==2:
        return render_template("product-2.html", product_id=product_id, cart_quantity=cart_quantity)
    else:
        return render_template("product-3.html", product_id=product_id, cart_quantity=cart_quantity)


if __name__ == "__main__":
    # Get the PORT from environment variable, default to 5000 if not set
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)