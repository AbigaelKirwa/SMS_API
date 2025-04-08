from config import SMS_API_ENDPOINT, SMS_ACCESS_KEY, SMS_API_KEY, SMS_CLIENT_ID, SMS_SENDER_ID
from dbconfig import get_db_connection
import json
import requests

# update messages table in the db
def update_message_status(task_id, status, provider_response=None, response_code=None):
    """Update message status in database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE sms_messages
                SET status = %s, provider_response = %s, response_code = %s, updated_at = NOW()
                WHERE task_id = %s
            """
            cursor.execute(sql, (status, provider_response, response_code, task_id))
        conn.commit()
    finally:
        conn.close()

# send message to API
def send_sms_bridge(phone_number, message, task_id):
    "This section of the code sends data to the sms service provider"
    try:
        # use provider-specific enpoint if provided otherwise use default
        endpoint = SMS_API_ENDPOINT

        if not endpoint:
            result = {
                "status":500,
                "response":"No SMS Provider enpoint provided",
                "success":False
            }
            update_message_status(task_id, 'failed', 'No SMS provider endpoint configured', 500)
            return result

        # adding the header structure
        headers = {
            "Content-Type": "application/json",
            "AccessKey": SMS_ACCESS_KEY
        }

        # this gives the payload structure of how data is sent to the API endpoint
        payload = {
            "ApiKey": SMS_API_KEY,
            "ClientId": SMS_CLIENT_ID,
            "SenderId": SMS_SENDER_ID,
            "MessageParameters":[
                {
                    "Number":phone_number, 
                    "Text":message
                }
            ],
            "Number": phone_number,
            "Text": message,
            "IsUnicode": True,
            "IsFlash":True
        }

        # fetch the response after sending the payload
        response = requests.post(endpoint, json=payload, headers=headers)

        result = {
            "status":response.status_code,
            "response":response.text,
            "success":response.ok,
            "phone_number":phone_number
        }

        # update message status
        status = 'sent' if response.ok else 'failed'
        update_message_status(task_id, status, response.text, response.status_code)
        
        return result

    except Exception as e:
        error_msg = str(e)
        update_message_status(task_id, 'failed', error_msg, 500)
        return{
            "status":500,
            "response":str(e),
            "success":False,
            "phone_number":phone_number
        }