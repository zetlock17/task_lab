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
    
    tasks_conn = sqlite3.connect('database/tasks.db')
    tasks_c = tasks_conn.cursor()

    tasks_c.execute('''CREATE TABLE IF NOT EXISTS tasks
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     description TEXT NOT NULL,
                     stages TEXT NOT NULL''')
    
    tasks_c.execute('''CREATE TABLE IF NOT EXISTS templates
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     description TEXT NOT NULL,
                     stages TEXT NOT NULL''')
    
    labs_conn = sqlite3.connect('database/labs.db')
    labs_c = labs_conn.cursor()

    labs_c.execute('''CREATE TABLE IF NOT EXISTS labs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL''')
    
    labs_c.execute('''CREATE TABLE IF NOT EXISTS equipments
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     is_active INTEGER
                     lab_id INTEGER NOT NULL''')
    
    labs_c.execute('''CREATE TABLE IF NOT EXISTS reserv
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER NOT NULL
                     start_time TEXT NOT NULL
                     end_time TEXT NOT_NULL
                     equipment_id INTEGER NOT NULL''')
    
def add_user(telegram_id: str, labs: str, tasks: str) -> bool:

    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()

    try:
        c.execute('''INSERT INTO users (telegram_id, labs, tasks)
                     VALUES (?, ?, ?)''',
                 (telegram_id, labs, tasks))
        
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