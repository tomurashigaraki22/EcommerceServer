from flask import Flask, jsonify, request, send_from_directory, make_response, send_file
import sqlite3
import shutil
import json
from git import Repo, GitCommandError
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from twilio.rest import Client
import subprocess
import datetime
import jwt
import random
import string
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'orenonawaerenjaeger'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'Trollz.mallstore@gmail.com'
app.config['MAIL_PASSWORD'] = 'zkhb hirb nmdc mbhz'
mail = Mail(app)

account_sid = 'ACd1d31fab44a914a7b7e84a02ccc1a344'
auth_token = '981027194c5a53227327f421ccded8eb'
twilio_phone_number = '+18317315755'
client = Client(account_sid, auth_token)

load_dotenv()

cors = CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")
conn = sqlite3.connect('./ecDB.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS authadmin (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT)')
conn.commit()
c.execute('CREATE TABLE IF NOT EXISTS auth (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT)')
print('Table Made')
conn.commit()
c.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, img TEXT, scorelvl INTEGER, caption TEXT, colors JSON, size JSON, category TEXT, stock_quantity INTEGER)')
conn.commit()
c.execute('CREATE TABLE IF NOT EXISTS shoppingcarts (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, products TEXT)')
conn.commit()
c.execute('CREATE TABLE IF NOT EXISTS orderwdp (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, address JSON, trackingnumber TEXT, amount TEXT, items JSON)')
conn.commit()
c.execute('CREATE TABLE IF NOT EXISTS trackorders (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, orderid TEXT, delivered TEXT, trackingid TEXT)')
conn.commit()


@app.route('/addtoTrack/<email>/<orderid>/', methods=['POST', 'GET'])
def addtoTrack(email, orderid):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()

        # Check if the email already has a tracking order
        c.execute('SELECT orderid FROM trackorders WHERE email = ?', (email,))
        cs = c.fetchone()

        if cs is not None:
            # If there is an existing tracking order, append the new orderid to it
            existing_orderids = cs[0].split(', ')
            existing_orderids.append(orderid)
            updated_orderids = ', '.join(existing_orderids)

            # Update the existing tracking order with the new orderid
            c.execute('UPDATE trackorders SET orderid = ? WHERE email = ?', (updated_orderids, email))
            conn.commit()
            conn.close()

            return {'status': 200, 'message': 'Added to tracking order successfully'}
        else:
            # If there is no existing tracking order, create a new one
            delivered = 'False'
            tid = generate_random_string()
            print('Tid: '+tid)
            c.execute('INSERT INTO trackorders (email, orderid, delivered, trackingid) VALUES (?, ?, ?, ?)', (email, orderid, delivered, tid))
            conn.commit()
            conn.close()

            return {'status': 200, 'message': 'Added to tracking order successfully'}

    except Exception as e:
        return {'status': 500, 'error': str(e)}


@app.route('/gettrackOrder', methods=['POST', 'GET'])
def gettrackOrder():
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        email = request.form.get('email')
        print('Email: ' + email)
        # Select completed orders for the given email
        c.execute('SELECT orderid FROM trackorders WHERE email = ?', (email,))
        cs = c.fetchone()
        print(cs)
        if cs is not None:
            order_ids = cs[0].split(', ')
            order_list = []

            for order_id in order_ids:
                order_id = int(order_id)
                conn = sqlite3.connect('./ecDB.db')
                c = conn.cursor()
                c.execute('SELECT * FROM posts WHERE id = ?', (order_id,))
                product = c.fetchone()
                conn.close()

                if product:
                    order_list.append({
                        'id': product[0],
                        'email': product[1],
                        'img': product[2].replace('\\', '/'),
                        'scorelvl': product[3],
                        'caption': product[4],
                        'colors': product[5],
                        'size': product[6],
                        'category': product[7],
                        'stock_quantity': product[8],
                        'timestamp': product[9],
                        'price': product[10],
                        'currency': product[11],
                    })

            return jsonify({'status': 200, 'orders': order_list})
        else:
            return jsonify({'status': 404, 'meaning': 'No completed orders found for the given email'})

    except Exception as e:
        return jsonify({'status': 500, 'error': str(e)})

@app.route('/adminlogin', methods=['POST', 'GET'])
def adminlogin():
    try:
        email = request.form.get('email')
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        password = request.form.get('password')
        if not all([email, password]):
            return jsonify({'message': 'Invalid input data', 'status': 400})
        
        c.execute('SELECT * FROM authadmin WHERE email = ?', (email,))
        cs = c.fetchone()

        if cs and cs[2] == password:
            payload = {
                    'email': email,
                    'password': password,
                }
            print('reach4')
            jwt_token = jwt.encode(payload, app.secret_key, algorithm='HS256')
            return jsonify({'message': 'Successful', 'status': 200, 'token': jwt_token})
        else:
            return jsonify({'message': 'Login Unsuccessful', 'status': 404})
    except Exception as e:
        return jsonify({'message': 'Internal Server Error', 'status': 500, 'Exception': str(e)})





@app.route('/payondelivery', methods=['POST'])
def payondelivery():
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()

        # Assuming items is a list of items; adjust as needed
        items = request.form.get('items')
        address = request.form.get('address')
        email = request.form.get('email')
        amount = request.form.get('amount')

        # Validate input data
        if not all([items, address, email, amount]):
            return jsonify({'message': 'Invalid input data', 'status': 400})

        trackingnumber = generate_random_string()

        message = f"Your order has been completed successfully. \n Your address is {address} \n The items you ordered are {items} \n The amount to be paid plus fee is {amount}"
        msg3 = Message('Pending Order', sender='trollz.mallstore@gmail.com', recipients=[email])
        msg3.body = message

        mail.send(msg3)

        message = f"New Order Placed (On delivery). \n The address is {address} \n The items he/she ordered are {items} \n The amount to be paid plus fee is {int(amount) + 10000}"
        msg3 = Message('Pending Order', sender='trollz.mallstore@gmail.com', recipients=['trollz.mallstore@gmail.com'])
        msg3.body = message

        mail.send(msg3)


        c.execute('INSERT INTO orderwdp (email, address, trackingnumber, amount, items) VALUES (?, ?, ?, ?, ?)',
                  (email, address, trackingnumber, amount, items))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Order Successful', 'trackingid': trackingnumber, 'amount': amount, 'address': address, 'status': 200})

    except Exception as e:
        # Log the exception for debugging purposes
        print(f'Exception in payondelivery route: {str(e)}')

        return jsonify({'message': 'Internal Server Error', 'status': 500})

def generate_random_string():
    letters = string.ascii_letters
    numbers = string.digits

    random_letters = ''.join(random.choice(letters) for _ in range(8))
    random_numbers = ''.join(random.choice(numbers) for _ in range(16))

    random_string = random_letters + random_numbers

    # If you want to shuffle the characters in the final string
    random_string = ''.join(random.sample(random_string, len(random_string)))

    return random_string

@app.route('/items/<path:filename>')
def serve_video(filename):
    video_path = 'items'  # Replace with the actual path to your video files directory
    full_path = os.path.join(video_path, filename)

    # Check if the file exists
    if not os.path.isfile(full_path):
        return "Video not found", 404

    # Determine the content type based on the file extension
    if filename.endswith('.mp4'):
        content_type = 'video/mp4'
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        return send_from_directory(os.path.join(root_dir, 'items'), filename)

    # Set the Content-Disposition header to display the file inline
    response = make_response(send_from_directory(video_path, filename, mimetype=content_type))
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'

    return response
    
@app.route('/deleteAcct/<email>', methods=['GET', 'POST'])
def deleteAcct(email):
    return jsonify({'message': 'Account will be deleted shortly '+ email})

@app.route('/recoverPassword/<email>', methods=['POST', 'GET'])
def recoverPassword(email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM auth WHERE email = ?', (email, ))
        cs = c.fetchone()
        if cs is not None:
            password = cs[2]
            print(password)
            message = Message('Password Recovery', sender='Trollz.mallstore@gmail.com', recipients=[email])
            message.body = f'Your account in Trollz Ecommerce has sent a request for password recovery \n Please delete this message as soon as you read it \n\n\n Your password is {password}, \n\n\n Thanks for using Trollz Ecommerce'  # Include the retrieved password here

            # Send the email
            mail.send(message)
            return jsonify({'message': 'Check Email', 'status': 200})
        else:
            return jsonify({'message': 'Error In sending', 'status': 404})
    except Exception as e:
        return jsonify({'Exception': str(e), 'Message': 'Exception Found'})
    
@app.route('/getItem/<id>/<email>', methods=['POST', 'GET'])
def getItem(id, email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM posts WHERE id = ?', (id, ))
        cs = c.fetchone()
        item_array = []
        if cs is not None:
            item_dict = {
                    'id': cs[0],
                    'email': cs[1],
                    'img': cs[2],
                    'score_lvl': cs[3],
                    'caption': cs[4],
                    'colors': cs[5],
                    'size': cs[6],
                    'category': cs[7],
                    'stock_quantity': cs[8],
                    'timestamp': cs[9],
                    'price': cs[10],
                    'currency': cs[11]
                }
            item_array.append(item_dict)
            conn.close()
            return jsonify({'message': item_array})
        else:
            conn.close()
            return jsonify({'bad_message': 'nothing'})
    except Exception as e:
        conn.close()
        return jsonify({'Exception': str(e), 'Message': 'Exception Found'})


@app.route('/checkout/<email>', methods=['POST', 'GET'])
def checkout(email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT products FROM shoppingcarts WHERE email = ?', (email,))
        cs = c.fetchone()

        if cs is not None:
            product_list = cs[0].split(', ')
            print(product_list)

            total_usd_price = 0  # Initialize the total price in USD
            converted_products = []  # Create a list to store the converted products

            for product_id in product_list:
                # Fetch the product information from the database
                c.execute('SELECT * FROM posts WHERE id = ?', (product_id,))
                product = c.fetchone()

                if product:
                    # Extract product information from the database
                    id, email, img, scorelvl, caption, colors, size, category, stock_quantity, timestamp, price, currency = product
                    print('Product', product)

                    if currency == 'USD':
                        # If the currency is already USD, no conversion needed
                        mPrice = price
                    else:
                        exchange_api_url = f"http://192.168.1.188:3000/NGNTOUSD"
                        response = requests.get(exchange_api_url)

                        if response.status_code == 200:
                            data = response.json()
                            print(data)
                            mainPrice = float(data.get('ngnValue'))
                            print(mainPrice)
                            add = 600
                            mainPrice = float(mainPrice)+add
                            mPrice = price / mainPrice
                            print(mPrice)
                        else:
                            return jsonify({'error': 'Unable to fetch exchange rate data'})
                    
                    # Create a dictionary to store the product information including the converted price
                    converted_product = {
                        'id': id,
                        'email': email,
                        'img': img,
                        'scorelvl': scorelvl,
                        'caption': caption,
                        'colors': colors,
                        'size': size,
                        'category': category,
                        'stock_quantity': stock_quantity,
                        'timestamp': timestamp,
                        'price': mPrice,  # Store the converted price in USD
                        'currency': 'USD'  # Update the currency to USD
                    }

                    converted_products.append(converted_product)
                    total_usd_price += mPrice

                else:
                    conn.close()
                    return jsonify({'error': f'Product with ID {product_id} not found'})
            conn.close()
            # Assuming 'total_usd_price' and 'converted_products' are already defined

# Create a message for successful checkout
            messageBody = f'''
            Dear {email},

            We are thrilled to inform you that your recent purchase at Trollz Mall Store was successful! Thank you for choosing us for your shopping needs.

            Here are the details of your order:

            Order Total: ${total_usd_price:.2f}

            Products:
            {", ".join(product['caption'] for product in converted_products)}

            Your satisfaction is our top priority, and we are working diligently to prepare and dispatch your order. You will receive a confirmation email with tracking information once your order has been shipped.

            If you have any questions or need further assistance, feel free to reply to this email or contact our customer support team at +234 807 127 3078.

            Thank you again for shopping with us. We appreciate your business!

            Best Regards,
            The Trollz Mall Store Team
            '''

            # Create a message object
            message = Message('Checkout Successful', sender='Trollz.mallstore@gmail.com', recipients=[email])
            message.body = messageBody


            mail.send(message)

            return jsonify({'message': 'Checkout successful', 'total_usd_price': total_usd_price, 'converted_products': converted_products})
        else:
            conn.close()
            return jsonify({'message': 'Shopping cart is empty'})

    except Exception as e:
        conn.close()
        return jsonify({'Exception': str(e), 'Message': 'Exception Found'})



@app.route('/deleteItemSeller/<id>/<email>', methods=['POST', 'GET'])
def deleteItemSeller(id, email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()

        # Check if the item with the given id and email exists
        c.execute('SELECT * FROM posts WHERE id = ? AND email = ?', (id, email))
        cs = c.fetchone()

        if cs is not None:
            # If the item exists, delete it
            c.execute('DELETE FROM posts WHERE id = ? AND email = ?', (id, email))
            conn.commit()
            conn.close()
            return "Item deleted successfully"

        conn.close()
        return "Item not found"  # Return a message if the item was not found
    except sqlite3.Error as e:
        return f"An error occurred: {str(e)}"  # Handle any potential errors

@app.route('/getAllUsers', methods=['POST', 'GET'])
def getAllUsers():
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM auth')
        cs = c.fetchall()
        conn.close()
        return jsonify({'Number of users': len(cs)})
    except Exception as e:
        conn.close()
        return jsonify({'message': str(e)})


@app.route('/deleteFromCart/<id>/<email>', methods=['POST', 'GET'])
def deleteFromCart(id, email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()

        # Retrieve the list of products from the shopping cart
        c.execute('SELECT products FROM shoppingcarts WHERE email = ?', (email,))
        products = c.fetchone()

        if products is not None:
            product_list = products[0].split(', ') if products and products[0] else []

            if id in product_list:
                # Remove all instances of the product ID from the list
                while id in product_list:
                    product_list.remove(id)

                # Join the remaining product IDs back into a string with commas
                updated_products = ', '.join(product_list)

                # Update the shopping cart with the updated product list
                c.execute('UPDATE shoppingcarts SET products = ? WHERE email = ?', (updated_products, email))
                conn.commit()
                conn.close()

                return jsonify({'message': 'Item removed successfully', 'status': 200})
            else:
                return jsonify({'message': 'Item not in cart', 'status': 404})
        else:
            return jsonify({'message': 'No products in cart', 'status': 409})
    except Exception as e:
        return jsonify({'Exception': str(e), 'Message': 'Exception Found'})



@app.route('/search/<query>', methods=['GET', 'POST'])
def search(query):
    print(query)
    search_query = f"%{query}%"
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM posts WHERE category LIKE ? OR caption LIKE ?', (search_query, search_query))
        cs = c.fetchall()
        if cs:
            # Creating a list of dictionaries where each dictionary represents an item
            feedback_list = []
            for row in cs:
                item_dict = {
                    'id': row[0],
                    'email': row[1],
                    'img': row[2],
                    'score_lvl': row[3],
                    'caption': row[4],
                    'colors': row[5],
                    'size': row[6],
                    'category': row[7],
                    'stock_quantity': row[8],
                    'timestamp': row[9],
                    'price': row[10],
                    'currency': row[11]
                }
                feedback_list.append(item_dict)

            return jsonify({'status': 200, 'feedback': feedback_list})
        else:
            return jsonify({'status': 404, 'feedback': []})
    except Exception as e:
        return jsonify({'Exception': str(e), 'Message': 'Exception Found'})

@app.route('/getItems4', methods=['GET', 'POST'])
def getItems4():
    print('Fins')
    try:
        email = request.form.get('email')
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM posts ORDER BY id DESC LIMIT 4')
        cs = c.fetchall()
        post_list = []
        for row in cs:
            posts = {
                'id': row[0],
                'email': row[1],
                'img': row[2],
                'scorelvl': row[3],
                'caption': row[4],
                'colors': row[5],
                'size': row[6],
                'category': row[7],
                'stock_quantity': row[8],
                'timestamp': row[9],
                'price': row[10],
                'currency': row[11]
            }
            post_list.append(posts)
        if post_list:
            return jsonify({'message': 'Gotten', 'posts': post_list, 'status': 200})
        else:
            return jsonify({'message': 'No posts found', 'status': 404})
    except Exception as e:
        return jsonify({'Message': 'Exception Found', 'Exception': str(e)})

@app.route('/getItems', methods=['POST', 'GET'])
def getItems():
    print('Fins')
    try:
        email = request.form.get('email')
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM posts ORDER BY id DESC LIMIT 20')
        cs = c.fetchall()
        post_list = []
        for row in cs:
            posts = {
                'id': row[0],
                'email': row[1],
                'img': row[2],
                'scorelvl': row[3],
                'caption': row[4],
                'colors': row[5],
                'size': row[6],
                'category': row[7],
                'stock_quantity': row[8],
                'timestamp': row[9],
                'price': row[10],
                'currency': row[11]
            }
            post_list.append(posts)
        if post_list:
            return jsonify({'message': 'Gotten', 'posts': post_list, 'status': 200})
        else:
            return jsonify({'message': 'No posts found', 'status': 404})
    except Exception as e:
        return jsonify({'Message': 'Exception Found', 'Exception': str(e)})

@app.route('/getItemses/<category>', methods=['GET', 'POST'])
def getItemses(category):
    print(category)
    try:
        email = request.form.get('email')
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM posts WHERE category = ?', (category,))
        cs = c.fetchall()
        post_list_category = []
        for row in cs:
            posts = {
                'id': row[0],
                'email': row[1],
                'img': row[2],
                'scorelvl': row[3],
                'caption': row[4],
                'colors': row[5],
                'size': row[6],
                'category': row[7],
                'stock_quantity': row[8],
                'timestamp': row[9],
                'price': row[10],
                'currency': row[11]
            }
            post_list_category.append(posts)
        if post_list_category:
            return jsonify({'message': 'Gotten', 'posts': post_list_category, 'status': 200})
        else:
            return jsonify({'message': 'No posts found', 'status': 404})
    except Exception as e:
        return jsonify({'Message': 'Exception Found', 'Exception': str(e)})
    
@app.route('/addToCart/<id>/<email>', methods=['POST', 'GET'])
def addToCart(id, email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()

        # Check if the product with the specified ID exists
        c.execute('SELECT * FROM posts WHERE id = ?', (id,))
        product = c.fetchone()

        if product:
            # Check if the user's shopping cart exists
            c.execute('SELECT * FROM shoppingcarts WHERE email = ?', (email,))
            cart = c.fetchone()

            if cart:
                # Update the existing cart by adding the product ID
                product_ids = cart[2].split(',') if cart[2] else []
                product_ids.append(str(id))
                updated_cart = ','.join(product_ids)  # Join without spaces
                c.execute('UPDATE shoppingcarts SET products = ? WHERE email = ?', (updated_cart, email))

            else:
                # Create a new cart for the user
                c.execute('INSERT INTO shoppingcarts (email, products) VALUES (?, ?)', (email, str(id)))

            conn.commit()
            conn.close()
            return jsonify({'message': 'Added to cart successfully', 'status': 200})
        else:
            return jsonify({'message': 'No such product', 'status': 404})
    except Exception as e:
        return jsonify({'message': 'Exception Found', 'exception': str(e), 'status': 409})


@app.route('/getCartId/<email>', methods=['POST', 'GET'])
def getCartId(email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT id FROM shoppingcarts WHERE email = ?', (email,))
        cs = c.fetchone()
        conn.close()
        return jsonify({'m': cs})
    except Exception as e:
        conn.close()
        return jsonify({'ex': str(e)})

@app.route('/getCartItems/<email>', methods=['GET', 'POST'])
def getCartItems(email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT products FROM shoppingcarts WHERE email = ?', (email,))
        cart_data = c.fetchone()
        conn.close()

        if cart_data:
            product_ids = cart_data[0].split(', ')  # Assuming product IDs are stored as a comma-separated string
            cart_items_dict = {}  # Dictionary to store product IDs and their occurrences

            for product_id in product_ids:
                # Add a check for an empty string before attempting conversion
                if not product_id:
                    continue  # Skip to the next iteration if product_id is empty

                try:
                    product_id = int(product_id)  # Convert product_id to an integer

                    if product_id in cart_items_dict:
                        cart_items_dict[product_id]['quantity'] += 1
                        print('Quantity: ' + str(cart_items_dict[product_id]['quantity']))
                    else:
                        conn = sqlite3.connect('./ecDB.db')
                        c = conn.cursor()
                        c.execute('SELECT * FROM posts WHERE id = ?', (product_id,))
                        product = c.fetchone()
                        conn.close()

                        if product:
                            cart_items_dict[product_id] = {
                                'id': product[0],
                                'email': product[1],
                                'img': product[2].replace('\\', '/'),
                                'scorelvl': product[3],
                                'caption': product[4],
                                'colors': product[5],
                                'size': product[6],
                                'category': product[7],
                                'stock_quantity': product[8],
                                'timestamp': product[9],
                                'price': product[10],
                                'currency': product[11],
                                'quantity': 1  # Set initial quantity to 1
                            }

                except ValueError as ve:
                    print(f"Error converting {product_id} to int: {ve}")
                    continue  # Skip to the next iteration in case of a conversion error

            cart_list = list(cart_items_dict.values())

            return jsonify({'message': 'Cart items retrieved successfully', 'cart_items': cart_list, 'status': 200})
        else:
            return jsonify({'message': 'Cart is empty', 'status': 404})
    except Exception as e:
        return jsonify({'message': 'Error while retrieving cart items', 'exception': str(e)})
        

@app.route('/incQuantity/<id>/<email>', methods=['GET', 'POST'])
def incQuantity(id, email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        
        # Retrieve the user's shopping cart
        c.execute('SELECT * FROM shoppingcarts WHERE email = ?', (email,))
        cart = c.fetchone()

        if cart:
            # Update the quantity of the specified product in the cart
            product_ids = cart[2].split(', ') if cart[2] else []
            if str(id) in product_ids:
                # Increment the quantity for the specified product
                product_ids.append(str(id))
                updated_cart = ', '.join(product_ids)
                c.execute('UPDATE shoppingcarts SET products = ? WHERE email = ?', (updated_cart, email))
                conn.commit()
                conn.close()
                return jsonify({'message': 'Quantity increased successfully', 'status': 200})
            else:
                return jsonify({'message': 'Product not found in the cart', 'status': 404})
        else:
            return jsonify({'message': 'Cart not found for the user', 'status': 404})

    except Exception as e:
        return jsonify({'message': 'Exception found', 'exception': str(e), 'status': 409})


@app.route('/decQuantity/<id>/<email>', methods=['GET', 'POST'])
def decQuantity(id, email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        
        # Retrieve the user's shopping cart
        c.execute('SELECT * FROM shoppingcarts WHERE email = ?', (email,))
        cart = c.fetchone()

        if cart:
            # Update the quantity of the specified product in the cart
            product_ids = cart[2].split(', ') if cart[2] else []
            if str(id) in product_ids:
                # Decrease the quantity for the specified product
                product_ids.remove(str(id))
                updated_cart = ', '.join(product_ids)
                c.execute('UPDATE shoppingcarts SET products = ? WHERE email = ?', (updated_cart, email))
                conn.commit()
                conn.close()
                return jsonify({'message': 'Quantity decreased successfully', 'status': 200})
            else:
                return jsonify({'message': 'Product not found in the cart', 'status': 404})
        else:
            return jsonify({'message': 'Cart not found for the user', 'status': 404})

    except Exception as e:
        return jsonify({'message': 'Exception found', 'exception': str(e), 'status': 409})


    
@app.route('/addItem/<email>', methods=['POST', 'GET'])
def addItem(email):
    print(email)
    try:
        scorelvl = 0
        caption = request.form.get('caption')
        colors = request.form.get('colors')
        size = request.form.get('size')
        category = request.form.get('category')
        price = request.form.get('price')
        currency = request.form.get('currency')
        print('Pass')
        print(request.files)
        print(category)

        stock_quantity = request.form.get('stock_quantity')

        if category is not None:
            conn = sqlite3.connect('./ecDB.db')
            c = conn.cursor()
            c.execute('SELECT * FROM auth WHERE email = ?', (email,))
            cs = c.fetchone()
            if cs is not None:
                items_dir = 'items'
                print('Here')
                print(request.files)
                current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]  # Format timestamp
                filename = secure_filename(f"{current_timestamp}.png")
                if not os.path.exists(items_dir):
                    os.makedirs(items_dir)
                print('Here2')
                image_path = os.path.join(items_dir, filename)
                print('Here3')
                image_data = request.files.get('image')  # Get the uploaded image data
                print(image_data)
                print('Here4')
                image_data.save(image_path)

                image_url = f"http://192.168.1.188:5442/{image_path.replace(os.path.sep, '/')}"
                print(image_url)
                c.execute('INSERT INTO posts (email, img, scorelvl, caption, colors, size, category, stock_quantity, timestamp, price, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (email, image_path, scorelvl, caption, colors, size, category, stock_quantity, current_timestamp, price, currency))
                conn.commit()
                conn.close()
                return jsonify({'message': 'Item added successfully', 'image_path': image_url}), 200
            else:
                c.execute('SELECT * FROM authadmin WHERE email = ?', (email,))
                cs = c.fetchone()
                if cs is not None:
                    items_dir = 'items'
                    print('Here')
                    print(request.files)
                    current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]  # Format timestamp
                    filename = secure_filename(f"{current_timestamp}.png")
                    if not os.path.exists(items_dir):
                        os.makedirs(items_dir)
                    print('Here2')
                    image_path = os.path.join(items_dir, filename)
                    print('Here3')
                    image_data = request.files.get('img')  # Get the uploaded image data
                    print(image_data)
                    print('Here4')
                    image_data.save(image_path)

                    image_url = f"http://192.168.1.188:5442/{image_path.replace(os.path.sep, '/')}"
                    print(image_url)
                    c.execute('INSERT INTO posts (email, img, scorelvl, caption, colors, size, category, stock_quantity, timestamp, price, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (email, image_path, scorelvl, caption, colors, size, category, stock_quantity, current_timestamp, price, currency))
                    conn.commit()
                    conn.close()
                    return jsonify({'message': 'Item added successfully', 'image_path': image_url}), 200
                else:
                    return jsonify({'message': 'User not found', 'status': 404}), 404
        else:
            return jsonify({'message': 'Category cannot be none', 'status': 404}), 404
    except Exception as e:
        return jsonify({'message':'Error Somewhere', 'Exception': str(e)})



@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')

            if not email or not password:
                return jsonify({'message': 'Email and password are required', 'status': 400})

            if '@gmail.com' not in email:
                return jsonify({'message': 'Not a valid email address', 'status': 400})

            conn = sqlite3.connect('./ecDB.db')
            c = conn.cursor()
            c.execute('SELECT * FROM auth WHERE email = ? AND password = ?', (email, password))
            cs = c.fetchone()

            if cs is not None:
                payload = {
                    'email': email,
                    'password': password,
                    'address': cs[3]
                }
                jwt_token = jwt.encode(payload, app.secret_key, algorithm='HS256')
                return jsonify({'message': 'Login Successful', 'status': 200, 'token': jwt_token})
            else:
                return jsonify({'message': 'Incorrect email or password', 'status': 401})

        except sqlite3.Error as e:
            return jsonify({'message': 'Database error', 'exception': str(e), 'status': 500})
        except Exception as e:
            return jsonify({'message': 'Internal Server Error', 'exception': str(e), 'status': 500})

    return jsonify({'message': 'Method Not Allowed', 'status': 405})
    

@app.route('/clearCart/<email>', methods=['POST', 'GET'])
def clearCart(email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        print('Help')
        cart = request.form.get('cart')
        print(request.form)
        address = request.form.get('address')
        print(address)

        # Parse cart as JSON
        cart_items = json.loads(cart)
        print(cart_items)

        # Iterate through cart items and structure the message
        message_body = "Order Completed:\n"
        print(cart)
        print(len(cart))
        for item in cart_items:
            caption = item.get('caption', 'N/A')
            category = item.get('category', 'N/A')
            price = item.get('price', 0)
            quantity = item.get('quantity', 0)
            message_body += f"\nCaption: {caption}, \nCategory: {category}, \nPrice: {price}, \nQuantity: {quantity}\n"
            print(message_body)
        # Send order completion message to the user
        msg = Message('Trollz Ecommerce', sender='trollz.mallstore@gmail.com', recipients=[email])
        msg.body = message_body 
        mail.send(msg)

        # Send new order notification to the store
        message2 = f"New Order:\n{message_body}\nAddress: {address}"
        msg2 = Message('New Order Placed', sender='trollz.mallstore@gmail.com', recipients=['trollz.mallstore@gmail.com'])
        msg2.body = message2
        mail.send(msg2)

        c = conn.cursor()
        c.execute('UPDATE shoppingcarts SET products = NULL WHERE email = ?', (email,))
        conn.commit()
        print('HereI reached dw')
        conn.close()
        return jsonify({'message': 'Cart cleared successfully', 'status': 200})
    except Exception as e:
        print('Error Message: ' + str(e))
        return jsonify({'message': 'Error while clearing the cart', 'exception': str(e), 'status': 500})


@app.route('/signup', methods=['POST'])
def signup():
    print('here')
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            address = request.form.get('address')
            phone_number = request.form.get('phone')
            conn = sqlite3.connect('./ecDB.db')
            c = conn.cursor()
            c.execute('SELECT * FROM auth WHERE email = ?', (email,))
            cs = c.fetchone()
            if cs is not None:
                return
            else:
                password = request.form.get('password')
                if '@gmail.com' in email:
                    conn = sqlite3.connect('./ecDB.db')
                    c = conn.cursor()
                    c.execute('INSERT INTO auth (email, password, address, phonenumber) VALUES (?, ?, ?, ?)', (email, password, address, phone_number))
                    conn.commit()
                    conn.close()
                    payload = {
                        'email': email,
                        'password': password,
                        'address': address
                    }
                    jwt_token = jwt.encode(payload, app.secret_key, algorithm='HS256')
                    welcome_message = f"Welcome to Trollz Ecommerce, {email}!\n\n"\
                  "We are delighted to have you join our online shopping community, where you'll discover a world of exquisite products and exceptional service.\n\n"\
                  "At Trollz Ecommerce, we are committed to providing you with an unparalleled shopping experience. Whether you're seeking the latest fashion trends, innovative gadgets, or timeless classics, our platform offers a curated selection to meet your every need.\n\n"\
                  "Our dedicated support team is here to assist you at every step of your journey. Should you have any questions or require assistance, please don't hesitate to reach out to us at Trollz.mallstore@gmail.com .  We're available to address your inquiries and ensure your shopping experience is nothing short of outstanding.\n\n"\
                  "Thank you for choosing Trollz Ecommerce. We look forward to serving you and making your online shopping dreams a reality."


                    # Send the welcome email
                    msg = Message('Welcome to XOX Ecommerce Site', sender='Trollz.mallstore@gmail.com', recipients=[email])
                    msg.body = welcome_message

                    mail.send(msg)

                    return jsonify({'message': 'Signup Successful', 'status': 200, 'token': jwt_token})
                else:
                    return jsonify({'message': 'Not a valid email address', 'status': 509})
        except Exception as e:
            return jsonify({'message': 'Error. Db may be busy', 'exception': str(e)})

@app.route('/changePassword/<email>', methods=['GET', 'POST'])
def changePassword(email):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        password = request.form.get('password')
        changedPassword = request.form.get('changedPassword')
        c.execute('SELECT * FROM auth WHERE email = ?', (email,))
        cs = c.fetchone()
        if cs is not None:
            if cs[2] == password:
                c.execute('UPDATE auth SET password = ? WHERE email = ?', (changedPassword, email))
                conn.commit()
                conn.close()
                return jsonify({'message': 'Password changed successfully', 'status': 200})
            else:
                conn.close()
                return jsonify({'message': 'Old Password is Wrong Please try again', 'status': 404})
        else:
            return jsonify({'message': 'No such email', 'status': 409})
    except Exception as e:
        return jsonify({'message': 'Error somewhere though', 'status': 509, 'Exception': str(e)})

@app.route('/editItemCate/<id>/<email>/<catse>', methods=['GET', 'POST'])
def editItemCate(id, email, cates):
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM posts WHERE id = ? AND email = ?', (id, email))
        cs = c.fetchone()
        if cs is not None:
            c.execute('UPDATE posts SET category = ? WHERE email = ? AND id = ?', (cates, email, id))
            conn.commit()
            conn.close()
            return jsonify({'Message': 'Successful Change', 'status': 200})
        else:
            return jsonify({'Message': 'No such post', 'status': 404})
    except Exception as e:
        return jsonify({'Exception': str(e)})



@app.route('/downloadDb/<password>', methods=['GET'])
def download_db(password):
    try:
        # Specify the path to your database file
        db_path = './ecDB.db'
        if password == 'Godwithus22':
        
        # Set up the response headers
            headers = {
                'Content-Disposition': 'attachment; filename=ecDB.db',
                'Content-Type': 'application/octet-stream',
            }

            # Send the file as a response
            return send_file(db_path, as_attachment=True)
        else:
            return jsonify({'Message': 'Wrong Password'})

    except Exception as e:
        return jsonify({'message': 'Error while downloading the database file', 'status': 500, 'Exception': str(e)})

@app.route('/downloaditems/<password>', methods=['GET', 'POST'])
def downloaditems(password):
    try:
        # Specify the path to the 'items' folder
        items_folder_path = './'
        if password == 'Godwithus22':
        
        # Create a temporary zip file
            zip_file_path = '/tmp/items.zip'
            shutil.make_archive(zip_file_path[:-4], 'zip', items_folder_path)

            # Set up the response headers
            headers = {
                'Content-Disposition': 'attachment; filename=items.zip',
                'Content-Type': 'application/zip',
            }

            # Send the zip file as a response
            response = send_file(zip_file_path, as_attachment=True)
            return response
        else:
            return jsonify({'Message': 'Wrong Password'})
    except Exception as e:
        return jsonify({'message': 'Error while downloading the items folder', 'status': 500, 'Exception': str(e)})

@app.route('/push-to-github', methods=['GET'])
def push_to_github():
    try:
        # Replace '/path/to/your/repo' with the actual path to your Git repository
        repo_path = './'
        os.chdir(repo_path)

        # Hardcode the GitHub access token
        access_token = os.getenv('GITHUB_ACCESS_TOKEN')
        print('Do you want this')
        print('I do')

        # Initialize Git repository if not already initialized
        if not os.path.exists(os.path.join(repo_path, '.git')):
            subprocess.run(['git', 'init'], check=True)

        # Remove 'origin' remote if it exists
        try:
            subprocess.run(['git', 'remote', 'remove', 'origin'], check=True)
        except subprocess.CalledProcessError:
            pass  # Ignore if 'origin' does not exist

        # Add 'origin' remote with the new URL
        subprocess.run(['git', 'remote', 'add', 'origin', f"https://tomurashigaraki22:{access_token}@github.com/tomurashigaraki22/EcommerceServer.git"])

        # Add, commit, and push changes
        subprocess.run(['git', 'add', '.'])  # Add specific files and folders
        subprocess.run(['git', 'commit', '-m', 'Automated commitss'])
        subprocess.run(['git', 'pull', 'origin', 'master'])
        subprocess.run(['git', 'push', 'origin', 'master'])
        # Add the remote 'origin' with the GitHub repository URL and access token



        return jsonify({'message': 'Changes pushed to GitHub', 'status': 200})

    except subprocess.CalledProcessError as e:
        return jsonify({'message': 'Error pushing to GitHub', 'status': 500, 'exception': str(e)})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5442, use_reloader=True)

