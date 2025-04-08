import pymysql
import os

# database configuration
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT'))

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
                CREATE TABLE IF NOT EXISTS sms_messages (
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
                    INDEX idx_task_id (task_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        conn.commit()
    finally:
        conn.close()