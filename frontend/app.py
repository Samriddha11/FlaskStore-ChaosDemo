import requests
import boto3
from flask import Flask, render_template, jsonify
from featureflags.client import CfClient
from featureflags.evaluations.auth_target import Target
import json

app = Flask(__name__)

beta_testers = Target(identifier="test1", name="test1", attributes={"org": "blue"})

HOST_NAME = 'http://storefront-service:8989'
SERVICE_PATH = '/getproductdetails'

URL = HOST_NAME + SERVICE_PATH

# AWS Secrets Manager setup
def get_secret():
    secret_name = "harness_api_key"
    region_name = "us-east-1"  # Change this to your AWS region

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)

    try:
        # Retrieve secret value
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)['api_key']  # Assuming the key is stored as a JSON object
    except Exception as e:
        print(f"Error fetching API key from Secrets Manager: {e}")
        raise

def validate(products):
    """
    Validates the structure of the product data to ensure it contains
    the necessary keys: 'name', 'description', and 'price'.
    """
    if not isinstance(products, list):
        return False
    for product in products:
        if not all(key in product for key in ["name", "description", "price"]):
            return False
    return True

def get_flag_status(flagstate):
    """
    Retrieves the feature flag status for the given flag state and target.
    """
    try:
        # Fetch the API key from Secrets Manager
        api_key = get_secret()

        # Initialize the feature flag client with the latest API key
        client = CfClient(api_key)

        # Wait for client initialization
        client.wait_for_initialization()

        # Ensure client is initialized before evaluating feature flag
        if not client.is_initialized():
            raise Exception("Failed to Initialize")
        
        return client.bool_variation(flagstate, beta_testers, False)
    except Exception as e:
        print(f"Error fetching feature flag status: {e}")
        return False  # Consider the feature flag off in case of an error

@app.route('/')
def hello():
    return 'Welcome to the Site'

@app.route('/productdetails', methods=['GET'])
def product_details():
    """
    Retrieves product details from the storefront-service and displays them in
    a catalog format if the feature flag is enabled. If the response is invalid,
    returns an appropriate error message.
    """
    flag_enabled = get_flag_status("ProductDetails")
    if flag_enabled:
        try:
            response = requests.get(URL)
            products = response.json()  # Try to parse the JSON response

            if validate(products):
                # Pass product data to the HTML template to display in a catalog format
                return render_template('catalog.html', products=products)
            else:
                return "Bad Request, Corrupted Response", 500
        
        except ValueError:  # Catches JSONDecodeError or invalid JSON
            return "Bad Request, Corrupted Response", 500
        except requests.RequestException as e:
            # Handle connection issues or other request-related errors
            return jsonify({"error": "Service unavailable", "details": str(e)}), 503
    else:
        # Return a beautiful webpage when the feature is unavailable
        return render_template('feature_unavailable.html'), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
