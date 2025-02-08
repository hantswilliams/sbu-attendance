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
TABLE_NAME_ATTENDANCE = os.getenv("AIRTABLE_TABLE_NAME_ATTENDANCE")
TABLE_NAME_CLASS= os.getenv("AIRTABLE_TABLE_NAME_CLASS")
AIRTABLE_URL_ATTENDANCE = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME_ATTENDANCE}"
AIRTABLE_URL_CLASSES = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME_CLASS}"

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


@app.route('/')
def classes():
    """Render the page with the list of classes."""
    return render_template('classes.html')

@app.route('/create_class', methods=['GET', 'POST'])
def create_class():
    """Create a new class endpoint."""
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        if not class_name:
            return jsonify({"error": "Class name is required."}), 400
        # Save the class name to Airtable where the class list is stored
        airtable_data = {
            "records": [
                {
                    "fields": {
                        "Class Name": class_name
                    }
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        airtable_response = requests.post(AIRTABLE_URL_CLASSES, json=airtable_data, headers=headers)
        print("Airtable Response Status Code:", airtable_response.status_code)
        print("Airtable Response Text:", airtable_response.text)
  
        return jsonify({"message": f"Classroom {class_name} created successfully."}), 201
    return render_template('create_class.html')

@app.route('/list_classes')
def list_classes():
    """List all classes endpoint."""
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}  # Authorization header
    airtable_response = requests.get(AIRTABLE_URL_CLASSES, headers=headers)  # GET request to Airtable

    if airtable_response.status_code == 200:
        data = airtable_response.json()
        class_names = [record.get('fields').get('Class Name') for record in data.get('records')]
        ## remove None and null values
        class_names = [x for x in class_names if x]
        return jsonify({"classes": class_names}), 200
    else:
        return jsonify({"error": "Failed to fetch class data."}), airtable_response.status_code
    



@app.route('/upload', methods=['POST'])
def upload():
    """Handle email and photo upload, save to Cloudinary, and send to Airtable."""
    try:
        email = request.form.get('email')
        photo_data = request.form.get('photo')
        ip_address = request.form.get('ip')
        emotion = request.form.get('emotion', 'Unknown')  # Get emotion, default to 'Unknown'
        emotion_confidence = request.form.get('emotion_confidence', 0)  # Get confidence, default to 0
        age = request.form.get('age', 0)  # Get age, default to 0
        class_name = request.form.get('class_name')  # Get class name

        print(f"📸 Received upload - Email: {email}, \
                IP: {ip_address}, Emotion: {emotion}, \
                Confidence: {emotion_confidence}, \
                Age: {age}, Class: {class_name}")

        if not email or not photo_data or not class_name:
            return jsonify({"error": "Email, photo, and class name are required."}), 400

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
                        "Photo": photo_url,  # Now a plain string, not an attachment,
                        "IP Address": ip_address,
                        "Emotion": emotion,
                        "Emotion Confidence": emotion_confidence,
                        "Age": age,
                        "Class Name": class_name
                    }
                }
            ]
        }

        # Make the POST request to Airtable
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }
        airtable_response = requests.post(AIRTABLE_URL_ATTENDANCE, json=airtable_data, headers=headers)

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

## dynamic route for class
@app.route('/<class_name>')
def get_class(class_name):
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    params = {
        "filterByFormula": f"{{Class Name}} = '{class_name}'"
    }
    airtable_response = requests.get(AIRTABLE_URL_CLASSES, headers=headers, params=params)
    if airtable_response.status_code == 200:
        data = airtable_response.json()
        if data.get('records'):
            return render_template('capture.html', class_name=class_name)
        else:
            return jsonify({"error": f"Class {class_name} not found."}), 404
    else:
        return jsonify({"error": "Failed to fetch class data."}), airtable_response.status_code
    

@app.route('/test')
def index():
    """Render the main page with the form."""
    return render_template('capture.html')




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
