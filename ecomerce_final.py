import google.generativeai as genai
import json
import webbrowser
from flask import Flask, render_template_string, request

# Configure the Google Generative AI API
genai.configure(api_key="AIzaSyBrgF20TimM0NULdq_mTIOKZHp2IeK55-I")

# Load the data from JSON
data_file = "random_customers_products.json"
with open(data_file, "r") as file:
    data = json.load(file)

# Update to match the correct JSON structure
customers = data["customers"]
products = data["product"]  

# Flask App
app = Flask(__name__)

# Store liked products per customer
liked_products = {}

def apply_first_order_logic(liked_categories, liked_prices, all_products):
    recommendations = []

    # FOL: Recommend products from liked categories
    for category in liked_categories:
        for product in all_products:
            if product["product_category"] == category and product["product_id"] not in recommendations:
                recommendations.append({
                    "product_name": product["product_name"],
                    "reason": f"Product from liked category: {category}"
                })
    # FOL: Recommend products from liked price ranges
    for price in liked_prices:
        for product in all_products:
            if product["price_range"] == price and product["product_id"] not in recommendations:
                recommendations.append({
                    "product_name": product["product_name"],
                    "reason": f"Product from liked price range: {price}"
                })

    # Return only the top 3 recommendations
    return recommendations[:3]


# Calculate saliency scores
def calculate_saliency(liked, all_products):
    saliency_scores = {"category": {}, "price_range": {}}
    liked_categories = {product["product_category"] for product in all_products if product["product_id"] in liked}
    liked_prices = {product["price_range"] for product in all_products if product["product_id"] in liked}

    for category in liked_categories:
        saliency_scores["category"][category] = sum(
            1 for product in all_products if product["product_category"] == category
        )
    for price in liked_prices:
        saliency_scores["price_range"][price] = sum(
            1 for product in all_products if product["price_range"] == price
        )
    return saliency_scores

# LLM Recommendation Logic using Google Generative AI
def get_llm_recommendations(liked_categories, liked_prices):
    query = f"""
    Recommend the top 3 products similar to categories {liked_categories} and price ranges {liked_prices}.
    Provide a short explanation for each recommendation in the format:
    "Product Name: Explanation".
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(query)
        
        recommendations = []
        for line in response.text.splitlines():
            if ":" in line:  # Ensures the format "Product: Reason"
                product, reason = line.split(":", 1)
                recommendations.append({
                    "product_name": product.strip(),
                    "reason": reason.strip()
                })
            if len(recommendations) >= 3:  # Limit to top 3 recommendations
                break
        
        return recommendations
    except Exception as e:
        print(f"Error using LLM API: {e}")
        return []


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
        <h3>First Order Logic Recommendations</h3>
        <table border="1">
            <thead>
                <tr>
                    <th>Recommended Product</th>
                    <th>Reason</th>
                </tr>
            </thead>
            <tbody>
                {% for product in fol_recommendations %}
                    <tr>
                        <td>{{ product['product_name'] }}</td>
                        <td>{{ product['reason'] }}</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>

        <h3>LLM Recommendations</h3>
        <table border="1">
            <thead>
                <tr>
                    <th>Recommended Product</th>
                    
                </tr>
            </thead>
            <tbody>
                {% for product in llm_recommendations %}
                    <tr>
                        <td>{{ product['product_name'] }}</td>
                        <td>{{ product['reason'] }}</td>
                    </tr>
                {% endfor %}
            </tbody>
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

    # Extract categories and prices of liked products
    liked_categories = {product["product_category"] for product in products if product["product_id"] in liked}
    liked_prices = {product["price_range"] for product in products if product["product_id"] in liked}

    # Generate FOL-based recommendations
    fol_recommendations = apply_first_order_logic(liked_categories, liked_prices, products)

    # Generate LLM-based recommendations
    llm_recommendations_text = get_llm_recommendations(liked_categories, liked_prices)
    llm_recommendations = [
        {"product_name": rec, "price_range": "N/A", "product_category": "N/A"} for rec in llm_recommendations_text
    ]

    # Calculate saliency scores
    saliency_scores = calculate_saliency(liked, products)

    return render_template_string(
        recommend_template,
        llm_recommendations=llm_recommendations,
        fol_recommendations=fol_recommendations,
        saliency_scores=saliency_scores
    )

# Run App
if __name__ == "__main__":
    webbrowser.open('http://127.0.0.1:5000/')
    app.run(debug=True)
