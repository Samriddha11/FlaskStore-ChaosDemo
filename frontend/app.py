import requests
from flask import Flask, render_template, jsonify
from featureflags.client import CfClient
from featureflags.evaluations.auth_target import Target

app = Flask(__name__)

api_key = '8430c8fb-711f-4215-92b9-0f4c738a9899'
client = CfClient(api_key)
client.wait_for_initialization()

beta_testers = Target(identifier="test1", name="test1", attributes={"org": "blue"})

HOST_NAME = 'http://storefront-service:8989'
SERVICE_PATH = '/getproductdetails'

URL = HOST_NAME + SERVICE_PATH

def validate(response):
    return "P" in response  # Simple validation for product data

@app.route('/')
def hello():
    return 'Welcome to the Site'

def get_flag_status(flagstate):
    return client.bool_variation(flagstate, beta_testers, False)

@app.route('/productdetails', methods=['GET'])
def product_details():
    result = get_flag_status("ProductDetails")
    
    if result:
        response = requests.get(URL)
        products = response.json()  # Assuming the response returns JSON data
        
        if validate(str(products)):
            # Pass product data to the HTML template to display in a catalog format
            return render_template('catalog.html', products=products)
        else:
            return "Bad Request, Corrupted Response", 500
    else:
        return jsonify({"error": "Feature Not Available"}), 404

if __name__ == '__main__':
    app.run(debug=True)
