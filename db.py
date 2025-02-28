import os
import sqlite3

def init_db():

    if not os.path.exists('database'):
        os.makedirs('database')

    users_conn = sqlite3.connect('database/users.db')
    users_c = users_conn.cursor()

    users_c.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     telegram_id TEXT NOT NULL''')
    
    users_conn.commit()
    users_conn.close()
    
    tasks_conn = sqlite3.connect('database/tasks.db')
    tasks_c = tasks_conn.cursor()

    tasks_c.execute('''CREATE TABLE IF NOT EXISTS tasks
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     templates_id INTEGER NOT NULL''')
    
    tasks_c.execute('''CREATE TABLE IF NOT EXISTS templates
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     description TEXT NOT NULL,
                     stages TEXT NOT NULL''')
    
    tasks_conn.commit()
    tasks_conn.close()
    
    labs_conn = sqlite3.connect('database/labs.db')
    labs_c = labs_conn.cursor()

    labs_c.execute('''CREATE TABLE IF NOT EXISTS labs
                    (id TEXT NOT NULL,
                     name TEXT NOT NULL''')
    
    labs_c.execute('''CREATE TABLE IF NOT EXISTS equipments
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     is_active INTEGER
                     lab_id INTEGER NOT NULL''')
    
    labs_c.execute('''CREATE TABLE IF NOT EXISTS reserve
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER NOT NULL
                     start_time TEXT NOT NULL
                     end_time TEXT NOT_NULL
                     equipment_id INTEGER NOT NULL''')
    
    labs_conn.commit()
    labs_conn.close()
    
    connection_conn = sqlite3.connect('database/labs.db')
    connection_c = connection_conn.cursor()

    connection_c.execute('''CREATE TABLE IF NOT EXISTS connection_user_to_task
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id TEXT NOT NULL,
                     task_id TEXT NOT NULL''')
    
    connection_c.execute('''CREATE TABLE IF NOT EXISTS connection_user_to_lab
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id TEXT NOT NULL,
                     lab_id TEXT NOT NULL''')
    
    connection_conn.commit()
    connection_conn.close()
    
def add_user(telegram_id: str) -> bool:

    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()

    try:
        c.execute('''INSERT INTO users (telegram_id)
                     VALUES (?, ?, ?)''',
                 (telegram_id))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def create_template(name: str, description: str, stages: str) -> bool:
    conn = sqlite3.connect('database/tasks.db')
    c = conn.cursor()

    try:
        c.execute('''INSERT INTO templates (name, description, stages)
                     VALUES (?, ?, ?)''',
                 (name, description, stages))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def delete_template(id: int) -> bool:
    conn = sqlite3.connect('database/tasks.db')
    c = conn.cursor()

    try:
        c.execute('DELETE FROM templates WHERE id = ?', (id))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def assing_task_to_user(templates_id: str, user_id: str, task_id) -> bool:
    conn_tasks = sqlite3.connect('database/tasks.db')
    c_tasks = conn_tasks.cursor()

    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()

    try:
        c_tasks.execute('''INSERT INTO tasks (templates_id)
                     VALUES (?)''',
                    (templates_id))
        
        conn_tasks.commit()

        c_connection.execute('''INSERT INTO connection_user_to_task (user_id, template_id)
                        VALUES (?, ?)''',
                        (user_id, task_id))
        
        conn_connection.commit()

        return True
    
    except:
        return False
    
    finally:
        conn_tasks.close()
        conn_connection.close()