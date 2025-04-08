from flask import Flask, request, jsonify
from celery import Celery
from dotenv import load_dotenv
import os
from config import SMS_API_ENDPOINT, SMS_API_KEY, SMS_SENDER_ID, SMS_ACCESS_KEY, SMS_CLIENT_ID
from dbconfig import get_db_connection, create_messages_table
from send_sms_bridge import send_sms_bridge

# load content from .env file
load_dotenv()

# configure flask app
app = Flask(__name__)

# configure celery
app.config['CELERY_BROKER_URL'] = os.getenv('REDIS_URL')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('REDIS_URL')

# initialize celery 
celery = Celery(
    app.name,
    broker = app.config['CELERY_BROKER_URL'],
    backend = app.config['CELERY_RESULT_BACKEND']
)
celery.conf.update(app.config)

# store the message in memory
messages = []   
    
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
            cursor.execute(sql, (phone_number, message, task_id, 'queued'))
        conn.commit()
    finally:
        conn.close()

@celery.task(bind=True)
def send_sms_task(self, phone_number, message):
    """ Celery task to send an SMS to the specified phone number """
    number = phone_number
    text = message
    task_id = self.request.id

    # call the send sms function
    send_sms_bridge(number, text, task_id)

@app.route('/send-bulk-sms', methods=['POST'])
def send_bulk_sms():
    """ api endpoint to send the same sms to different users """
    data = request.get_json()

    if not data:
        return jsonify({"error": "request must contain JSON DATA"}), 400
    
    # check for required fields
    if 'phone_numbers' not in data:
        return jsonify({"error": "missing required field phone_numbers"}), 400
    if 'message' not in data:
        return jsonify({"error": "missing required field message"}), 400
    if not isinstance(data['phone_numbers'], list):
        return jsonify({"error": "phone numbers must be a list"}), 400


    # fetch the data from the request and store in variables
    phone_numbers = data['phone_numbers']
    message = data['message']

    # creating an empty list that will store task ids
    task_ids=[]

    # queue an sms task for every phone number
    for phone_number in phone_numbers:
        #format phone number
        number = "{}{}".format("254", phone_number.replace(" ","")[-9:])
        #store the message
        messages.append({
            "phone_number":number,
            "message":message,
        })
    
        # calling the celery function that will interact with the message API
        task = send_sms_task.delay(number, message)

        #save messages to db
        save_message_to_db(number, message, task.id)

        task_ids.append({"phone_number":number, "task_id":task.id})

    return jsonify({
        "status":f"Bulk SMS successfully sent for {len(phone_numbers)} recepients",
        "tasks": task_ids
    })

@app.route('/messages', methods=['GET'])
def get_messages():
    """API endpoint to get all messages with optional filtering"""
    # fetch argument from request and store in variables
    status = request.args.get('status', None)
    phone = request.args.get('phone', None)
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM sms_messages WHERE 1=1"
            # initialize an empty list to store all the parameters from the request
            params = []

            # check if status is present in argument
            if status:
                # concatenates status to query
                query += " AND status =%s"
                # adds status to params list
                params.append(status)

            # check if phone is present in arument
            if phone:
                # concatenates phone to query 
                query += " AND phone =%s"
                # adds phone to params list
                params.append(phone)

            # concatenates order by property
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset]) 

            cursor.execute(query, params)
            messages = cursor.fetchall()

            # convert datetime objects to strings for JSON serialization
            for msg in messages:
                if 'created_at' in msg and msg['created_at']:
                    msg['created_at'] = msg['created_at'].isoformat()
                if 'updated_at' in msg and msg['updated_at']:
                    msg['updated_at'] = msg['updated_at'].isoformat()

        return jsonify({"messages":messages, "count":len(messages)})
    finally:
        conn.close()

@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """API endpoint to get the status of a task"""
    task = send_sms_task.AsyncResult(task_id)

    # get message details from DB
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM sms_messages WHERE task_id = %s", (task_id,)) 
            message = cursor.fetchone()

            if message:
                # Convert datetime objects to strings
                if 'created_at' in message and message['created_at']:
                    message['created_at'] = message['created_at'].isoformat()
                if 'updated_at' in message and message['updated_at']:
                    message['updated_at'] = message['updated_at'].isoformat()
    finally:
        conn.close()

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