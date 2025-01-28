from flask import Flask, request, jsonify, render_template
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

# Airtable Configuration
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
AIRTABLE_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

@app.route('/')
def index():
    """Render the main page with the form."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Handle email and photo upload, save to Cloudinary, and send to Airtable."""
    try:
        email = request.form.get('email')
        photo_data = request.form.get('photo')

        if not email or not photo_data:
            return jsonify({"error": "Email and photo are required."}), 400

        # Decode the base64 photo and upload it to Cloudinary
        photo_binary = photo_data.split(',')[1]  # Remove the `data:image/...;base64,` prefix
        response = cloudinary.uploader.upload(
            f"data:image/jpeg;base64,{photo_binary}",
            folder="uploads"
        )
        photo_url = response.get("secure_url")  # Publicly accessible URL from Cloudinary

        # Prepare the data payload for Airtable
        airtable_data = {
            "records": [
                {
                    "fields": {
                        "Email": email,
                        "Photo": photo_url  # Now a plain string, not an attachment
                    }
                }
            ]
        }

        # Make the POST request to Airtable
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }
        airtable_response = requests.post(AIRTABLE_URL, json=airtable_data, headers=headers)

        # Log the Airtable response for debugging
        print("Airtable Response Status Code:", airtable_response.status_code)
        print("Airtable Response Text:", airtable_response.text)

        # Check Airtable response
        if airtable_response.status_code == 200:
            return jsonify({"message": "Attendance: Upload successful.", "data": airtable_response.json()}), 200
        else:
            return jsonify({
                "error": "Failed to upload to Airtable.",
                "details": airtable_response.json() if airtable_response.headers.get('Content-Type') == 'application/json' else airtable_response.text
            }), airtable_response.status_code

    except Exception as e:
        # Log exception for debugging
        print("Exception occurred:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
