from flask import Flask, requests, jsonify
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
    broker = app.config['CELERY_BROKER_URL']
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
    # Celery task to send an SMS to the specified phone number
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

