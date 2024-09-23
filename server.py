from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import os
import werkzeug
import logging
import traceback

# Initialize Flask application and enable CORS
app = Flask(__name__, static_folder='Dx_pre_processor/build', static_url_path='')
CORS(app)

# Configure logging to capture errors and save them to a log file
logging.basicConfig(level=logging.ERROR, filename='app.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Allowed file extensions and maximum file size (10 MB)
ALLOWED_EXTENSIONS = {'csv'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
UPLOAD_FOLDER = 'uploads'

# List of valid states/territories for validation
VALID_STATES = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'ACT', 'TAS', 'NT']

# Ensure the uploads directory exists; create it if it does not
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_column_case_insensitive(df, column_name):
    """Return the actual column name and the column itself, ignoring case."""
    cols = df.columns
    for col in cols:
        if col.strip().upper() == column_name.upper():
            return col, df[col]
    raise ValueError(f"Column '{column_name}' not found in the uploaded file.")

def validate_state(state):
    """Validate state entry against the list of valid states."""
    if isinstance(state, str) and state.strip().upper() in VALID_STATES:
        return state.strip().upper()  # Normalize state to uppercase
    return ''  # Invalid state becomes an empty string

def validate_postcode(pcode):
    """Validate postcode entry to ensure it is exactly 4 digits long."""
    if isinstance(pcode, str) and pcode.strip().isdigit() and len(pcode.strip()) == 4:
        return pcode.strip()  # Keep valid postcode as is
    return ''  # Invalid postcode becomes an empty string

def validate_phone(phone):
    """Validate phone number, ensuring it is alphanumeric and up to 15 characters long."""
    if isinstance(phone, str) and len(phone.strip()) <= 15 and phone.strip().replace(' ', '').isalnum():
        return phone.strip()  # Normalize valid phone number
    return ''  # Invalid phone becomes an empty string

def validate_email(email):
    """Validate email format and ensure it does not exceed 130 characters."""
    if isinstance(email, str):
        emails = [e.strip() for e in email.split(',')]  # Support multiple emails
        if emails:
            first_email = emails[0]  # Validate the first email
            if len(first_email) <= 130 and '@' in first_email and '.' in first_email and ' ' not in first_email:
                return first_email  # Return valid email
    return ''  # Invalid email becomes an empty string

# Define column validation functions for each software
COLUMNS_TO_VALIDATE_MAXSOFT = {
    'State': validate_state,
    'PCode': validate_postcode,
    'Phone': validate_phone,
    'Mobile': validate_phone,
    'Fax': validate_phone,
    'Email': validate_email,
}

COLUMNS_TO_VALIDATE_RP = {
    'State': validate_state,
    'PCode': validate_postcode,
}

def preprocess_file(file_path, original_filename):
    """Read the uploaded CSV file, process it based on software provider, and return the processed file path."""
    # Read the CSV file into a DataFrame
    df = pd.read_csv(file_path, encoding='ISO-8859-1')
    print(f"Columns in the uploaded file: {df.columns.tolist()}")

    # Get the value of the 'SOFTVEND' column, case-insensitively
    softvend_col, softvend = get_column_case_insensitive(df, 'SOFTVEND')
    softvend_value = softvend.iloc[0].strip()

    # Determine processing based on software vendor
    softvend_upper = softvend_value.upper()
    if softvend_upper in ['ROCKEND', 'PROPERTYIQ']:
        df = process_rockend_property_iq(df)
    elif softvend_upper == 'MAXSOFT':
        df = process_maxsoft(df)
    elif softvend_upper in ['STRATASPHERE', 'STRATA PLUS']:
        print("No processing needed for Stratasphere/Strata Plus.")
        return df  # Return unprocessed DataFrame if no processing needed

    # Save the processed file
    processed_file_name = f"{os.path.splitext(original_filename)[0]}_processed.csv"
    processed_file_path = os.path.join(UPLOAD_FOLDER, processed_file_name)
    df.to_csv(processed_file_path, index=False)  # Save as CSV without the index
    print(f"Processed file saved as {processed_file_path}")

    return processed_file_path

def process_rockend_property_iq(df):
    """Process the DataFrame for Rockend and Property IQ software, validating specific columns."""
    for col_name, validate_func in COLUMNS_TO_VALIDATE_RP.items():
        try:
            actual_col_name, col = get_column_case_insensitive(df, col_name)
            df[actual_col_name] = col.apply(validate_func)  # Apply validation function
        except ValueError:
            print(f"Column '{col_name}' not found. Skipping validation.")

    return df  # Return the modified DataFrame

def process_maxsoft(df):
    """Process the DataFrame for Maxsoft software, validating specific columns."""
    for col_name, validate_func in COLUMNS_TO_VALIDATE_MAXSOFT.items():
        try:
            actual_col_name, col = get_column_case_insensitive(df, col_name)
            df[actual_col_name] = col.apply(validate_func)  # Apply validation function
        except ValueError:
            print(f"Column '{col_name}' not found. Skipping validation.")

    return df  # Return the modified DataFrame

def clean_up_processed_files(limit=3):
    """Remove old processed files, keeping only the most recent ones."""
    # List all processed files in the upload folder
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('_processed.csv')]
    # Sort files by creation time (oldest first)
    files.sort(key=lambda x: os.path.getctime(os.path.join(UPLOAD_FOLDER, x)))

    # Remove files exceeding the limit
    while len(files) > limit:
        oldest_file = files.pop(0)  # Get the oldest file
        os.remove(os.path.join(UPLOAD_FOLDER, oldest_file))  # Delete the file
        logging.info(f"Removed old processed file: {oldest_file}")

@app.route('/', methods=['GET'])
def serve_react_app():
    """Serve the main React application."""
    return app.send_static_file('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    # Check if the request contains a file
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    # Check if the file is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check if the uploaded file is allowed
    if file and allowed_file(file.filename):
        try:
            # Secure the filename and save the file
            file_path = os.path.join(UPLOAD_FOLDER, werkzeug.utils.secure_filename(file.filename))
            file.save(file_path)

            # Process the uploaded file
            processed_file = preprocess_file(file_path, file.filename)

            # Clean up old processed files, keeping the last 3
            clean_up_processed_files()

            # Send the processed file back to the user
            return send_file(processed_file, as_attachment=True, mimetype='text/csv', download_name=os.path.basename(processed_file))
        except Exception as e:
            # Log the error and return a generic error message
            logging.error(f"Error processing file: {str(e)}\n{traceback.format_exc()}")
            return jsonify({'error': 'An error occurred while processing the file. Please refresh the page and try again. If softvend is STRATASPHERE, they do not need pre processing'}), 500
        finally:
            # Clean up the uploaded file after processing
            if os.path.exists(file_path):
                os.remove(file_path)

    # If the file type is invalid
    return jsonify({'error': 'Invalid file type. Only CSV files are allowed.'}), 400

# Set the maximum content length for uploads
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

if __name__ == '__main__':
    # Run the Flask app in debug mode
    app.run(debug=True)
