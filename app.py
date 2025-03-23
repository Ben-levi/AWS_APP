from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dotenv import load_dotenv
import logging
import os
import time
load_dotenv()

from data_sql import (get_tasks, create_task, delete_task, 
                      findByNumber, update_task, search_task, 
                      check_task_exist)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def health_check():
    return 'OK', 200

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/addtask')
def addtask():
    return render_template('addtasksForm.html')

@app.route('/createtask', methods=['POST'])
def createtask():
    # Map form fields to database columns
    title = request.form.get('title', '')
    priority = request.form.get('priority', '')
    status = request.form.get('status', '')
    person = request.form.get('person', '')
    description = request.form.get('description', '')
    
    if not check_task_exist(title):
        # Handle photo upload if present
        photo = request.files.get('photo')
        photo_filename = ""
        if photo and photo.filename:
            try:
                # Create uploads directory if it doesn't exist
                uploads_dir = os.path.join('static', 'uploads')
                os.makedirs(uploads_dir, exist_ok=True)
                
                # Save the file
                photo_filename = f"{title}_{int(time.time())}_{photo.filename}"
                photo_path = os.path.join(uploads_dir, photo_filename)
                photo.save(photo_path)
                print(f"Photo saved at: {photo_path}")
            except Exception as e:
                print(f"Error saving photo: {str(e)}")
                photo_filename = ""
        
        success = create_task(title, priority, status, person, description, photo_filename)
        if success:
            print(f"Task created: {title}")
        else:
            print(f"Failed to create task: {title}")
        return redirect('/viewtasks')
    else: 
        return render_template('addtasksForm.html', message='Task already exists')

@app.route('/viewtasks')
def viewtasks():
    tasks = get_tasks()
    print(f"Retrieved {len(tasks)} tasks")
    for task in tasks:
        print(f"Task ID: {task['id']}, Title: {task.get('title', 'N/A')}")
    return render_template('tasksTable.html', tasks=tasks)

@app.route('/deletetask/<number>')
def deletetask(number):
    print(f"Deleting task with ID: {number}")
    # Add a delay to ensure the request is processed
    time.sleep(1)
    success = delete_task(number)
    if success:
        print(f"Task {number} successfully deleted")
    else:
        print(f"Failed to delete task {number}")
    # Add another delay before redirecting
    time.sleep(1)
    return redirect('/viewtasks')

@app.route('/edittask/<int:number>')
def edittask(number):
    try:
        task = findByNumber(number)
        if task:
            print(f"Editing task {number}: {task}")
            return render_template('edittaskForm.html', task=task)
        else:
            logging.debug(f"Task with number {number} not found.")
            return render_template('error.html', message="Task not found"), 404
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return render_template('error.html', message=f"An error occurred: {str(e)}"), 500

@app.route('/search', methods=['POST'])
def search():
    task_name = request.form.get('search_name', '')
    filtered_tasks = search_task(task_name)
    return render_template('tasksTable.html', tasks=filtered_tasks)

@app.route('/saveUpdatedtask/<number>', methods=['POST'])
def saveUpdatedtask(number):
    try:
        # Map form fields to database columns
        title = request.form.get('title', '')
        priority = request.form.get('priority', '')
        status = request.form.get('status', '')
        person = request.form.get('person', '')
        description = request.form.get('description', '')
        
        # Handle photo upload
        current_task = findByNumber(number)
        photo_filename = current_task.get('photo', '') if current_task else ''
        
        photo = request.files.get('photo')
        if photo and photo.filename:
            try:
                # Create uploads directory if it doesn't exist
                uploads_dir = os.path.join('static', 'uploads')
                os.makedirs(uploads_dir, exist_ok=True)
                
                # Save the file
                photo_filename = f"{title}_{int(time.time())}_{photo.filename}"
                photo_path = os.path.join(uploads_dir, photo_filename)
                photo.save(photo_path)
                print(f"Photo saved at: {photo_path}")
            except Exception as e:
                print(f"Error saving photo: {str(e)}")
        
        print(f"Updating task {number} with: {title}, {priority}, {status}, {person}, {description}, {photo_filename}")
        update_task(number, title, priority, status, person, description, photo_filename)
        # Add a delay before redirecting
        time.sleep(1)
        return redirect(url_for('viewtasks'))
    except Exception as e:
        logging.error(f"Error updating task: {str(e)}")
        return render_template('error.html', message=f"An error occurred while updating the task: {str(e)}"), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5052)
