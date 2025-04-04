from flask import Flask, request, jsonify
from celery import Celery
from dotenv import load_dotenv
import requests
import os

# load content from .env file
load_dotenv()

# configure flask app
app = Flask(__name__)

# configure celery
app.config['CELERY_BROKER_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

#initialize celery 
celery = Celery(
    app.name,
    broker = app.config['CELERY_BROKER_URL'],
    backend = app.config['CELERY_RESULT_BACKEND']
)
celery.conf.update(app.config)

#store the message in memory
messages = []

#sms provider configuration
SMS_API_ENDPOINT = os.getenv('SMS_API_ENPOINT', '')
SMS_API_KEY = os.getenv('SMS_API_KEY', '')
SMS_SENDER_ID = os.getenv('SMS_SENDER_ID', '')

@celery.task
def send_sms_task(phone_number, message, provider_endpoint= None):
    """ Celery task to send an SMS to the specified phone number """
    try:
        # use provider-specific enpoint if provided otherwise use default
        endpoint = provider_endpoint if provider_endpoint else SMS_API_ENDPOINT

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
    if not isinstance(data[phone_numbers], list):
        return jsonify({"error: phone numbers must be a list"}), 400

    # fetch the data from the request and store in variables
    phone_numbers = data['phone_numbers']
    message = data['message']
    provider_endpoint = data.get('provider_enpoint', none)

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
    task_ids.append({"phone_number":phone_number, "task_id":task_id})

    return jsonify({
        "status":f"Bulk SMS successfully sent for ${len(phone_numbers)} recepients",
        "tasks": tasks_ids
    })

@app.route('/messages', methods=['GET'])
def get_messages():
    """API endpoint to get all messages"""
    return jsonify({"messages":messages})

@app.route('/task/<task_id>', methods=['GET'])
def get_task_status():
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