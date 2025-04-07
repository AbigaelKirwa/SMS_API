from flask import Flask, request, jsonify
from celery import Celery
from dotenv import load_dotenv
import requests
import os
import pymysql

# load content from .env file
load_dotenv()

# configure flask app
app = Flask(__name__)

# configure celery
app.config['CELERY_BROKER_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# database configuration
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT'))


# initialize celery 
celery = Celery(
    app.name,
    broker = app.config['CELERY_BROKER_URL'],
    backend = app.config['CELERY_RESULT_BACKEND']
)
celery.conf.update(app.config)

# store the message in memory
messages = []

# sms provider configuration
SMS_API_ENDPOINT = os.getenv('SMS_API_ENDPOINT', '')
SMS_API_KEY = os.getenv('SMS_API_KEY', '')
SMS_SENDER_ID = os.getenv('SMS_SENDER_ID', '')

# connect to db
def get_db_connection():
    """Create and return a database connection"""
    return pymysql.connect(
        host = DB_HOST,
        user = DB_USER, 
        password = DB_PASSWORD,
        database = DB_NAME,
        port = DB_PORT,
        cursorclass = pymysql.cursors.DictCursor
    )

# create a table
def create_messages_table():
    """Create a message table if it does not exist"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sms_messages(
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    phone_number VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    provider_response TEXT,
                    response_code INT,
                    task_id VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_phone_number (phone_number),
                    INDEX idx_status (status),
                    INDEX idx_task_id (task_id),
                )ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        conn.commit()
    finally:
        conn.close()
    
# create table when app starts
with app.app_context():
    create_messages_table()

# save messages to the db
def save_message_to_db(phone_number, message, task_id):
    """Save message to the database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO sms_messages(phone_number, message, task_id, status)
                VALUES(%s, %s, %s, %s)
            """
            cursor.execute(sql, (phone_number, message_task, task_id, 'queued'))
        conn.commit()
    finally:
        conn.close()

# update messages table in the db
def update_message_status(task_id, status, provider_response=None, response_code=None):
    """Update message status in database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """"
                UPDATE sms_messages
                SET status = %s, provider_response = %s, response_code = %s, updated_at = NOW()
                WHERE task_id = %s
            """
            cursor.execute(sql, (status, provider_response, response_code, task_id))
        conn.commit()
    finally:
        conn.close()

@celery.task
def send_sms_task(phone_number, message, provider_endpoint= None):
    """ Celery task to send an SMS to the specified phone number """
    try:
        # use provider-specific enpoint if provided otherwise use default
        endpoint = provider_endpoint if provider_endpoint else SMS_API_KEY

        if not endpoint:
            return {
                "status":500,
                "response":"No SMS Provider enpoint provided",
                "success":False
            }

        # this gives the payload structure of how data is sent to the API endpoint
        payload = {
            "api_key": SMS_API_ENDPOINT,
            "to": phone_number,
            "message": message,
            "sender_id": SMS_SENDER_ID
        }

        # fetch the response after sending the payload
        response = requests.post(endpoint, json=payload)

        return{
            "status":response.status_code,
            "response":response.text,
            "success":response.ok,
            "phone_number":phone_number
        }
    except Exception as e:
        return{
            "status":500,
            "response":str(e),
            "success":False,
            "phone_number":phone_number
        }

@app.route('/send-bulk-sms', methods=['POST'])
def send_bulk_sms():
    """ api endpoint to send the same sms to different users """
    data = request.get_json()

    if not data:
        return jsonify({"error: request must contain JSON DATA"}), 400
    
    # check for required fields
    if 'phone_numbers' not in data:
        return jsonify({"error: missing required field phone_numbers"}), 400
    if 'message' not in data:
        return jsonify({"error: missing required field message"}), 400
    if not isinstance(data['phone_numbers'], list):
        return jsonify({"error: phone numbers must be a list"}), 400


    # fetch the data from the request and store in variables
    phone_numbers = data['phone_numbers']
    message = data['message']
    provider_endpoint = data.get('provider_endpoint', None)

    # creating an empty list that will store task ids
    task_ids=[]

    # queue an sms task for every phone number
    for phone_number in phone_numbers:
        #store the message
        messages.append({
            "phone_number":phone_number,
            "message":message,
        })
    
        # calling the celery function that will interact with the message API
        task = send_sms_task.delay(phone_number, message, provider_endpoint)
        task_ids.append({"phone_number":phone_number, "task_id":task.id})

    return jsonify({
        "status":f"Bulk SMS successfully sent for {len(phone_numbers)} recepients",
        "tasks": task_ids
    })

@app.route('/messages', methods=['GET'])
def get_messages():
    """API endpoint to get all messages"""
    return jsonify({"messages":messages})

@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """API endpoint to get the status of a task"""
    task = send_sms_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state':task.state,
            'status':str(task.info)
        }
    elif task.state == 'FAILURE':
        response = {
            'state':task.state,
            'status':str(task.info)
        }
    else:
        response = {
            'state':task.state,
            'status':str(task.info)
        }
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))