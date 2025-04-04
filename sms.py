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


