from flask import Flask, jsonify, request
import sqlite3
import json
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import datetime
import jwt
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'orenonawaerenjaeger'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'emmanuelhudson355@gmail.com'
app.config['MAIL_PASSWORD'] = 'pdlw wmnu leov yqyv'
mail = Mail(app)

cors = CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")
conn = sqlite3.connect('./ecDB.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS auth (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT)')
print('Table Made')
conn.commit()
c.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, img TEXT, scorelvl INTEGER, caption TEXT, colors JSON, size JSON, category TEXT, stock_quantity INTEGER)')
conn.commit()
c.execute('CREATE TABLE IF NOT EXISTS shoppingcarts (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, products TEXT)')
conn.close()

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



@app.route('/deleteFromCart/<id>/<email>', methods=['POST', 'GET'])
def deleteFromCart(id, email):
    print(id, email)
    try:
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT products FROM shoppingcarts WHERE email = ?', (email,))
        products = c.fetchone()
        if products is not None:
            print(products)
            product_list = products[0].split(', ') if products and products[0] else []
            if id in product_list:
                # Remove the product from the list
                product_list.remove(id)
                
                # Convert the list back to a string
                updated_products = ', '.join(product_list)
                
                # Update the shopping cart with the new product list
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
        c.execute('SELECT * FROM posts WHERE email LIKE ? OR caption LIKE ?', (search_query, search_query))
        cs = c.fetchall()
        if cs is not None:
            return jsonify({'status': 200, 'feedback': cs})
        else:
            return jsonify({'status': 404, 'feedback': 'No related posts found'})
    except Exception as e:
        return jsonify({'Exception': str(e), 'Message':'Exception Found'})

@app.route('/getItems', methods=['POST', 'GET'])
def getItems():
    print('Fins')
    try:
        email = request.form.get('email')
        conn = sqlite3.connect('./ecDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM posts')
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
                product_ids = cart[1].split(', ') if cart[1] else []
                product_ids.append(str(id))
                updated_cart = ', '.join(product_ids)
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
            cart_list = []

            for product_id in product_ids:
                conn = sqlite3.connect('./ecDB.db')
                c = conn.cursor()
                c.execute('SELECT * FROM posts WHERE id = ?', (product_id,))
                product = c.fetchone()
                conn.close()

                if product:
                    cartItem = {
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
                        'currency': product[11]
                    }
                    cart_list.append(cartItem)

            return jsonify({'message': 'Cart items retrieved successfully', 'cart_items': cart_list, 'status': 200})
        else:
            return jsonify({'message': 'Cart is empty', 'status': 200})
    except Exception as e:
        return jsonify({'message': 'Error while retrieving cart items', 'exception': str(e)})


    
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
        category = category.replace(" ", "").replace("\t", "").replace("\n", "")

        stock_quantity = request.form.get('stock_quantity')

        if category is not None:
            conn = sqlite3.connect('./ecDB.db')
            c = conn.cursor()
            c.execute('SELECT * FROM auth WHERE email = ?', (email,))
            cs = c.fetchone()
            if cs is not None:
                items_dir = 'items'
                current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]  # Format timestamp
                filename = secure_filename(f"{current_timestamp}.png")
                if not os.path.exists(items_dir):
                    os.makedirs(items_dir)
                image_path = os.path.join(items_dir, filename)
                image_data = request.files.get('image')  # Get the uploaded image data
                image_data.save(image_path)

                image_url = f"http://192.168.0.188:5432/{image_path.replace(os.path.sep, '/')}"
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
            if '@gmail.com' in email:
                conn = sqlite3.connect('./ecDB.db')
                c = conn.cursor()
                c.execute('SELECT * FROM auth WHERE email = ? AND password = ?', (email, password))
                cs = c.fetchone()
                payload = {
                    'email': email,
                    'password': password,
                }
                jwt_token = jwt.encode(payload, app.secret_key, algorithm='HS256')
                if cs is not None:
                    return jsonify({'message': 'Login Successful', 'status': 200, 'token': jwt_token})
                else:
                    return jsonify({'message': 'Incorrect email or Password', 'status': 404})
            else:
                return jsonify({'message': 'Not a valid email address', 'status': 509})

        except Exception as e:
            return jsonify({'message': 'Error. Db may be busy'})
    else:
        return
    

@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
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
                    c.execute('INSERT INTO auth (email, password) VALUES (?, ?)', (email, password))
                    conn.commit()
                    conn.close()
                    payload = {
                        'email': email,
                        'password': password,
                    }
                    jwt_token = jwt.encode(payload, app.secret_key, algorithm='HS256')
                    welcome_message = f"Welcome to Trollz Ecommerce, {email}!\n\n"\
                  "We are delighted to have you join our online shopping community, where you'll discover a world of exquisite products and exceptional service.\n\n"\
                  "At Trollz Ecommerce, we are committed to providing you with an unparalleled shopping experience. Whether you're seeking the latest fashion trends, innovative gadgets, or timeless classics, our platform offers a curated selection to meet your every need.\n\n"\
                  "Our dedicated support team is here to assist you at every step of your journey. Should you have any questions or require assistance, please don't hesitate to reach out to us at emmanuelhudson355@gmail.com. We're available to address your inquiries and ensure your shopping experience is nothing short of outstanding.\n\n"\
                  "Thank you for choosing Trollz Ecommerce. We look forward to serving you and making your online shopping dreams a reality."


                    # Send the welcome email
                    msg = Message('Welcome to XOX Ecommerce Site', sender='emmanuelhudson355@gmail.com', recipients=[email])
                    msg.body = welcome_message

                    mail.send(msg)

                    return jsonify({'message': 'Signup Successful', 'status': 200, 'token': jwt_token})
                else:
                    return jsonify({'message': 'Not a valid email address', 'status': 509})
        except Exception as e:
            return jsonify({'message': 'Error. Db may be busy', 'exception': str(e)})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5432, use_reloader=True)