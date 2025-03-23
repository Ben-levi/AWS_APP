import mysql.connector
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection function to ensure fresh connections
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "mysql-service.database.svc.cluster.local"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "password"),
            port=os.getenv("DB_PORT", "3306"),
            database=os.getenv("DB_NAME", "todos"),
            autocommit=False
        )
        return connection
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        return None

def create_db():
    connection = get_db_connection()
    if not connection:
        logger.error("Failed to connect to database during create_db")
        return
        
    cursor = connection.cursor()
    database = os.getenv("DB_NAME", "todos")
    
    try:
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        connection.commit()
        
        # Use the database
        cursor.execute(f"USE {database}")
        
        # Create the tasks table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                priority VARCHAR(50),
                status VARCHAR(50),
                person VARCHAR(255),
                photo VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        
        logger.info(f"Database '{database}' initialized successfully")
    except mysql.connector.Error as err:
        logger.error(f"Error in create_db: {err}")
    finally:
        cursor.close()
        connection.close()

# Initialize the database
create_db()

def get_tasks():
    connection = get_db_connection()
    if not connection:
        logger.error("Failed to connect to database in get_tasks")
        return []
        
    cursor = connection.cursor(dictionary=True)
    tasks = []
    
    try:
        # Simple direct query - don't try to be too clever with columns
        cursor.execute("SELECT id, title, description, priority, status, person, photo, created_at FROM tasks")
        tasks = cursor.fetchall()
        
        if tasks:
            logger.info(f"Retrieved {len(tasks)} tasks")
        else:
            logger.info("No tasks found")
    except mysql.connector.Error as err:
        logger.error(f"Error in get_tasks: {err}")
    finally:
        cursor.close()
        connection.close()
        
    return tasks

def create_task(title, priority="", status="", person="", description="", photo=""):
    connection = get_db_connection()
    if not connection:
        logger.error("Failed to connect to database in create_task")
        return False
        
    cursor = connection.cursor()
    success = False
    
    try:
        query = "INSERT INTO tasks (title, priority, status, person, description, photo) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (title, priority, status, person, description, photo))
        connection.commit()
        success = True
        logger.info(f"Task created: {title}")
    except mysql.connector.Error as err:
        logger.error(f"Error in create_task: {err}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()
        
    return success

def delete_task(id):
    connection = get_db_connection()
    if not connection:
        logger.error(f"Failed to connect to database in delete_task for id {id}")
        return False
        
    cursor = connection.cursor()
    success = False
    
    try:
        # Delete the task
        query = "DELETE FROM tasks WHERE id = %s"
        cursor.execute(query, (id,))
        connection.commit()
        
        # Check if deletion was successful
        affected_rows = cursor.rowcount
        success = affected_rows > 0
        
        if success:
            logger.info(f"Task {id} deleted successfully")
        else:
            logger.warning(f"Failed to delete task {id}, no rows affected")
    except mysql.connector.Error as err:
        logger.error(f"Error in delete_task for id {id}: {err}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()
        
    return success

def findByNumber(id):
    connection = get_db_connection()
    if not connection:
        logger.error(f"Failed to connect to database in findByNumber for id {id}")
        return None
        
    cursor = connection.cursor(dictionary=True)
    task = None
    
    try:
        query = "SELECT id, title, description, priority, status, person, photo, created_at FROM tasks WHERE id = %s"
        cursor.execute(query, (id,))
        task = cursor.fetchone()
        
        if task:
            logger.info(f"Found task {id}: {task.get('title', 'N/A')}")
        else:
            logger.warning(f"Task {id} not found")
    except mysql.connector.Error as err:
        logger.error(f"Error in findByNumber for id {id}: {err}")
    finally:
        cursor.close()
        connection.close()
        
    return task

def update_task(id, title, priority="", status="", person="", description="", photo=None):
    connection = get_db_connection()
    if not connection:
        logger.error(f"Failed to connect to database in update_task for id {id}")
        return False
        
    cursor = connection.cursor()
    success = False
    
    try:
        if photo:
            query = "UPDATE tasks SET title = %s, priority = %s, status = %s, person = %s, description = %s, photo = %s WHERE id = %s"
            cursor.execute(query, (title, priority, status, person, description, photo, id))
        else:
            # Don't update photo if not provided
            query = "UPDATE tasks SET title = %s, priority = %s, status = %s, person = %s, description = %s WHERE id = %s"
            cursor.execute(query, (title, priority, status, person, description, id))
            
        connection.commit()
        
        # Check if update was successful
        affected_rows = cursor.rowcount
        success = affected_rows > 0
        
        if success:
            logger.info(f"Task {id} updated successfully")
        else:
            logger.warning(f"No changes made to task {id}")
    except mysql.connector.Error as err:
        logger.error(f"Error in update_task for id {id}: {err}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()
        
    return success

def search_task(search_term):
    connection = get_db_connection()
    if not connection:
        logger.error("Failed to connect to database in search_task")
        return []
        
    cursor = connection.cursor(dictionary=True)
    tasks = []
    
    try:
        query = "SELECT id, title, description, priority, status, person, photo, created_at FROM tasks WHERE title LIKE %s"
        cursor.execute(query, (f'%{search_term}%',))
        tasks = cursor.fetchall()
        
        logger.info(f"Found {len(tasks)} tasks matching '{search_term}'")
    except mysql.connector.Error as err:
        logger.error(f"Error in search_task: {err}")
    finally:
        cursor.close()
        connection.close()
        
    return tasks

def check_task_exist(title):
    connection = get_db_connection()
    if not connection:
        logger.error(f"Failed to connect to database in check_task_exist for title {title}")
        return False
        
    cursor = connection.cursor()
    exists = False
    
    try:
        cursor.execute("SELECT id FROM tasks WHERE title = %s", (title,))
        result = cursor.fetchone()
        exists = result is not None
        
        if exists:
            logger.info(f"Task with title '{title}' already exists")
    except mysql.connector.Error as err:
        logger.error(f"Error in check_task_exist for title {title}: {err}")
    finally:
        cursor.close()
        connection.close()
        
    return exists
