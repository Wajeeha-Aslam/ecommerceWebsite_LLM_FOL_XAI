import json
import webbrowser
from flask import Flask, render_template_string, request

# Load the data from JSON
data_file = "random_customers_products.json"
with open(data_file, "r") as file:
    data = json.load(file)

# Update to match the correct JSON structure
customers = data["customers"]
products = data["product"]  # Changed from 'products' to 'product' to match JSON structure

# Flask App
app = Flask(__name__)

# Store liked products per customer
liked_products = {}

#XAI part
def calculate_saliency(liked, all_products):
    # Initialize saliency scores
    saliency_scores = {"category": {}, "price_range": {}}
    
    # Get categories and price ranges of liked products
    liked_categories = {product["product_category"] for product in all_products if product["product_id"] in liked}
    liked_prices = {product["price_range"] for product in all_products if product["product_id"] in liked}
    
    # Calculate category saliency
    for category in liked_categories:
        saliency_scores["category"][category] = sum(
            1 for product in all_products if product["product_category"] == category
        )
    
    # Calculate price range saliency
    for price in liked_prices:
        saliency_scores["price_range"][price] = sum(
            1 for product in all_products if product["price_range"] == price
        )
    
    return saliency_scores


# HTML Templates
index_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-Commerce Recommendation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f8f8f8; color: #333; }
        header { background-color: #4CAF50; color: white; text-align: center; padding: 1rem; font-size: 1.5rem; }
        main { text-align: center; padding: 1rem; }
        footer { background-color: #4CAF50; color: white; text-align: center; padding: 0.5rem; position: fixed; bottom: 0; width: 100%; }
    </style>
</head>
<body>
    <header>Welcome to the E-Commerce Product Recommendation System</header>
    <main>
        <form action="/products" method="POST">
            <label for="customer_id">Choose a Customer:</label>
            <select name="customer_id" required>
                {% for customer in customers %}
                    <option value="{{ customer['customer_id'] }}">{{ customer['customer_name'] }}</option>
                {% endfor %}
            </select>
            <br><br>
            <button type="submit">View Products</button>
        </form>
    </main>
    <footer>&copy; 2024 E-Commerce Recommendation System</footer>
</body>
</html>
'''

products_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Products</title>
    <style>
    body { font-family: Arial, sans-serif; background-color: #f8f8f8; color: #333; margin: 0; }
    header { background-color: #4CAF50; color: white; text-align: center; padding: 1rem; font-size: 1.5rem; }
    main { text-align: center; padding: 1rem; margin-bottom: 2rem; } /* Added margin-bottom */
    .product { display: inline-block; border: 1px solid #ddd; border-radius: 5px; margin: 10px; padding: 10px; background-color: #fff; box-shadow: 0 0 5px rgba(0,0,0,0.1); }
    .product img { width: 150px; height: 150px; object-fit: cover; }
    form { margin: 0; padding: 0; } /* Removed default margins for form */
    button { margin: 20px 0; padding: 0.5rem; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
    button:hover { background-color: #45a049; }
    footer { background-color: #4CAF50; color: white; text-align: center; padding: 0.5rem; position: fixed; bottom: 0; width: 100%; }
</style>

</head>
<body>
    <header>Available Products</header>
   <main>
    <form action="/recommend" method="POST" style="display: flex; flex-wrap: wrap; justify-content: center; gap: 10px;">
        <input type="hidden" name="customer_id" value="{{ customer_id }}">
        {% for product in products %}
            <div class="product">
                <img src="{{ product['image_url'] }}" alt="{{ product['product_name'] }}">
                <h3>{{ product['product_name'] }}</h3>
                <p>Price: {{ product['price_range'] }}</p>
                <p>Category: {{ product['product_category'] }}</p>
                <label>
                    <input type="checkbox" name="liked_products" value="{{ product['product_id'] }}"> Like
                </label>
            </div>
        {% endfor %}
        <div style="width: 100%; text-align: center; margin-top: 20px;">
            <button type="submit">Get Recommendations</button>
        </div>
    </form>
</main>

    <footer>&copy; 2024 E-Commerce Recommendation System</footer>
</body>
</html>
'''

recommend_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recommendations</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; background-color: #f8f8f8; color: #333; margin: 0; }
        header { background-color: #4CAF50; color: white; padding: 1rem; font-size: 1.5rem; }
        main { padding: 1rem; }
        footer { background-color: #4CAF50; color: white; text-align: center; padding: 0.5rem; position: fixed; bottom: 0; width: 100%; }
    </style>
</head>
<body>
    <header>Your Recommendations</header>
    <main>
        <h2>Based on your liked products, we recommend:</h2>
        <table border="1" style="margin: 0 auto; border-collapse: collapse; width: 80%;">
            <tr>
                <th>LLM Recommendations</th>
                <th>First Order Logic Recommendations</th>
            </tr>
            <tr>
                <td>
                    {% for product in llm_recommendations %}
                        <p>{{ product['product_name'] }} - {{ product['price_range'] }}</p>
                    {% endfor %}
                </td>
                <td>
                    {% for product in fol_recommendations %}
                        <p>{{ product['product_name'] }} - {{ product['price_range'] }}</p>
                    {% endfor %}
                </td>
            </tr>
        </table>
        
        <h3>Saliency Maps (Feature Importance)</h3>
        <h4>Category Importance</h4>
       <table border="1" style="margin: 0 auto; border-collapse: collapse;">
          <tr>
              <th>Category</th>
              <th>Importance Score</th>
         </tr>
         {% for category, score in saliency_scores["category"].items() %}
         <tr>
             <td>{{ category }}</td>
             <td>{{ score }}</td>
         </tr>
         {% endfor %}
       </table>

        <h4>Price Range Importance</h4>
        <table border="1" style="margin: 0 auto; border-collapse: collapse;">
         <tr>
            <th>Price Range</th>
            <th>Importance Score</th>
        </tr>
        {% for price_range, score in saliency_scores["price_range"].items() %}
        <tr>
            <td>{{ price_range }}</td>
            <td>{{ score }}</td>
        </tr>
        {% endfor %}
        </table>

    </main>
    <footer>&copy; 2024 E-Commerce Recommendation System</footer>
</body>
</html>
'''

# Routes
@app.route('/')
def index():
    return render_template_string(index_template, customers=customers)

@app.route('/products', methods=['POST'])
def products_page():
    customer_id = request.form.get("customer_id")
    return render_template_string(products_template, products=products, customer_id=customer_id)

@app.route('/recommend', methods=['POST'])
def recommend():
    customer_id = request.form.get("customer_id")
    liked = request.form.getlist("liked_products")

    # Store liked products
    liked_products[customer_id] = liked

    # LLM Recommendations: Products in the same category but not already liked
    liked_categories = {product["product_category"] for product in products if product["product_id"] in liked}
    llm_recommendations = [
        product for product in products
        if product["product_category"] in liked_categories and product["product_id"] not in liked
    ][:3]

    # First Order Logic Recommendations: Products with similar price range but not already liked
    liked_prices = {product["price_range"] for product in products if product["product_id"] in liked}
    fol_recommendations = [
        product for product in products
        if product["price_range"] in liked_prices and product["product_id"] not in liked and product["product_id"] not in [p["product_id"] for p in llm_recommendations]
    ][:3]

    # Calculate saliency scores
    saliency_scores = calculate_saliency(liked, products)

    return render_template_string(
        recommend_template,
        llm_recommendations=llm_recommendations,
        fol_recommendations=fol_recommendations,
        saliency_scores=saliency_scores,  # Pass saliency data to the template
    )

# Run App
if __name__ == "__main__":
    webbrowser.open('http://127.0.0.1:5000/')
    app.run(debug=True)
