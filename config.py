import os
from dotenv import load_dotenv

#load the environment variables
load_dotenv()

# sms provider configuration
SMS_API_ENDPOINT = os.getenv('SMS_API_ENDPOINT')
SMS_API_KEY = os.getenv('SMS_API_KEY')
SMS_SENDER_ID = os.getenv('SMS_SENDER_ID')
SMS_CLIENT_ID = os.getenv('SMS_CLIENT_ID')
SMS_ACCESS_KEY = os.getenv('SMS_ACCESS_KEY')