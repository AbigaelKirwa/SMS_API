import os
import load_dotenv from dotenv

#load the environment variables
load_dotenv()

# sms provider configuration
SMS_API_ENDPOINT = os.getenv('SMS_API_ENDPOINT')
SMS_API_KEY = os.getenv('SMS_API_KEY')
SMS_SENDER_ID = os.getenv('SMS_SENDER_ID')
SMS_CLIENT_ID = os.getenv('SMS_CLIENT_ID')
SMS_ACCESS_KEY = os.getenv('SMS_ACCESS_KEY')

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