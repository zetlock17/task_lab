import os
import sqlite3

def init_db():
    if not os.path.exists('database'):
        os.makedirs('database')

    users_conn = sqlite3.connect('database/users.db')
    users_c = users_conn.cursor()

    users_c.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     telegram_id TEXT NOT NULL,
                     selected_lab TEXT DEFAULT NULL)''')
    
    users_conn.commit()
    users_conn.close()
    
    tasks_conn = sqlite3.connect('database/tasks.db')
    tasks_c = tasks_conn.cursor()

    tasks_c.execute('''CREATE TABLE IF NOT EXISTS tasks
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     templates_id INTEGER NOT NULL)''')
    
    tasks_c.execute('''CREATE TABLE IF NOT EXISTS templates
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     description TEXT NOT NULL,
                     stages TEXT NOT NULL)''')
    
    tasks_conn.commit()
    tasks_conn.close()
    
    labs_conn = sqlite3.connect('database/labs.db')
    labs_c = labs_conn.cursor()

    labs_c.execute('''CREATE TABLE IF NOT EXISTS labs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     admins TEXT NOT NULL)''')
    
    labs_c.execute('''CREATE TABLE IF NOT EXISTS equipments
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     is_active INTEGER NOT NULL,
                     lab_id INTEGER NOT NULL)''')
    
    labs_c.execute('''CREATE TABLE IF NOT EXISTS reserve
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER NOT NULL,
                     start_time TEXT NOT NULL,
                     end_time TEXT NOT NULL,
                     equipment_id INTEGER NOT NULL)''')
    
    labs_conn.commit()
    labs_conn.close()
    
    connection_conn = sqlite3.connect('database/connection.db')
    connection_c = connection_conn.cursor()

    connection_c.execute('''CREATE TABLE IF NOT EXISTS connection_user_to_task
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id TEXT NOT NULL,
                     task_id TEXT NOT NULL)''')
    
    connection_c.execute('''CREATE TABLE IF NOT EXISTS connection_user_to_lab
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id TEXT NOT NULL,
                     lab_id TEXT NOT NULL)''')
    
    connection_conn.commit()
    connection_conn.close()
    
def is_user_registered(telegram_id: str) -> bool:
    """Check if a user with the given telegram_id exists in the database"""
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    
    try:
        c.execute('''SELECT COUNT(*) FROM users WHERE telegram_id = ?''', 
                 (telegram_id,))
        
        count = c.fetchone()[0]
        return count > 0
    
    except:
        return False
    
    finally:
        conn.close()

def add_user(telegram_id: str) -> bool:
    """Add a new user to the database"""
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()

    try:
        c.execute('''INSERT INTO users (telegram_id)
                     VALUES (?)''',
                 (telegram_id,))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def is_user_admin_of_any_lab(telegram_id: str) -> bool:
    """Check if the user is an admin of any lab"""
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    
    try:
        c.execute('''SELECT COUNT(*) FROM labs WHERE creator_id = ?''', 
                 (telegram_id,))
        
        count = c.fetchone()[0]
        return count > 0
    
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
        c.execute('DELETE FROM templates WHERE id = ?', (id,))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def assing_task_to_user(templates_id: int, user_id: int, task_id: int) -> bool:
    conn_tasks = sqlite3.connect('database/tasks.db')
    c_tasks = conn_tasks.cursor()

    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()

    try:
        c_tasks.execute('''INSERT INTO tasks (templates_id)
                     VALUES (?)''',
                    (templates_id,))
        
        conn_tasks.commit()

        c_connection.execute('''INSERT INTO connection_user_to_task (user_id, task_id)
                        VALUES (?, ?)''',
                        (user_id, task_id))
        
        conn_connection.commit()

        return True
    
    except:
        return False
    
    finally:
        conn_tasks.close()
        conn_connection.close()

def unassign_task_to_user(user_id: int, task_id: int) -> bool:
    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()
    
    conn_tasks = sqlite3.connect('database/tasks.db')
    c_tasks = conn_tasks.cursor()
    
    try:
        c_connection.execute('''DELETE FROM connection_user_to_task 
                             WHERE user_id = ? AND task_id = ?''', 
                             (user_id, task_id))
        
        conn_connection.commit()
        
        c_connection.execute('''SELECT COUNT(*) FROM connection_user_to_task 
                             WHERE task_id = ?''', 
                             (task_id,))
        
        count = c_connection.fetchone()[0]
        
        if count == 0:
            c_tasks.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn_tasks.commit()
        
        return True
    
    except:
        return False
    
    finally:
        conn_connection.close()
        conn_tasks.close()

def create_lab(name: str, creator_id: str) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()

    try:
        c.execute('''INSERT INTO labs (name, creator_id)
                     VALUES (?, ?)''',
                 (name, creator_id))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def delete_lab(id: int) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()

    try:
        c.execute('DELETE FROM labs WHERE id = ?', (id,))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def add_equipment(name: str, is_active: bool, lab_id: int) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()

    try:
        # Convert boolean to integer (1 for True, 0 for False)
        is_active_int = 1 if is_active else 0
        
        c.execute('''INSERT INTO equipments (name, is_active, lab_id)
                     VALUES (?, ?, ?)''',
                 (name, is_active_int, lab_id))
        
        conn.commit()
        return True
    
    except:
        return False

    finally:
        conn.close()
    
def delete_equipment(id: int) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()

    try:
        c.execute('DELETE FROM equipments WHERE id = ?', (id,))
        
        conn.commit()
        return True
    
    except:
        return False

    finally:
        conn.close()

def change_equipment_status(equipment_id: int) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()

    try:
        c.execute('''SELECT is_active FROM equipments WHERE id = ?''', 
                  (equipment_id,))
        
        result = c.fetchone()
        if result is None:
            return False 
        
        current_status = result[0]

        new_status = 0 if current_status == 1 else 1

        c.execute('''UPDATE equipments 
                     SET is_active = ? 
                     WHERE id = ?''', 
                  (new_status, equipment_id))
        
        conn.commit()
        return True
    
    except:
        return False

    finally:
        conn.close()

def add_reserve(user_id: int, equipment_id: int, start_time: str, end_time: str) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()

    try:
        c.execute('''SELECT is_active FROM equipments WHERE id = ?''', 
                  (equipment_id,))
        
        result = c.fetchone()
        if result is None or result[0] == 0:
            return False

        c.execute('''SELECT COUNT(*) FROM reserve 
                   WHERE equipment_id = ? AND 
                   ((start_time <= ? AND end_time >= ?) OR 
                    (start_time <= ? AND end_time >= ?) OR 
                    (start_time >= ? AND end_time <= ?))''', 
                  (equipment_id, start_time, start_time, end_time, end_time, start_time, end_time))
        
        if c.fetchone()[0] > 0:
            return False
        
        c.execute('''INSERT INTO reserve (user_id, equipment_id, start_time, end_time)
                   VALUES (?, ?, ?, ?)''',
                 (user_id, equipment_id, start_time, end_time))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def delete_reserve(reserve_id: int) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()

    try:
        c.execute('''SELECT COUNT(*) FROM reserve WHERE id = ?''', 
                  (reserve_id,))
        
        if c.fetchone()[0] == 0: 
            return False
            
        c.execute('DELETE FROM reserve WHERE id = ?', (reserve_id,))
        
        conn.commit()
        return True
    
    except:
        return False
    
    finally:
        conn.close()

def user_task_exists(user_id: int, task_id: int) -> bool:
    conn = sqlite3.connect('database/connection.db')
    c = conn.cursor()
    
    try:
        c.execute('''SELECT COUNT(*) FROM connection_user_to_task 
                   WHERE user_id = ? AND task_id = ?''', 
                  (user_id, task_id))
        
        count = c.fetchone()[0]
        return count > 0
    except:
        return False
    
    finally:
        conn.close()

def user_is_admin(user_id: str, lab_id: int) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    
    try:
        c.execute('''SELECT COUNT(*) FROM labs 
                   WHERE id = ? AND creator_id = ?''', 
                  (lab_id, user_id))
        
        count = c.fetchone()[0]
        return count > 0
    
    except:
        return False
    
    finally:
        conn.close()

def user_get_selected_lab_id(user_id: int) -> str:
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    
    try:
        c.execute('''SELECT selected_lab FROM users 
                   WHERE id = ?''', 
                  (user_id,))
        
        result = c.fetchone()
        if result is None:
            return None
            
        return result[0]
    
    except:
        return None
    
    finally:
        conn.close()

def get_available_labs(user_id: str) -> list:
    conn = sqlite3.connect('database/labs.db')
    conn_connection = sqlite3.connect('database/connection.db')
    c = conn.cursor()
    c_connection = conn_connection.cursor()
    
    try:
        c.execute('''SELECT id, name FROM labs WHERE creator_id = ?''', 
                 (user_id,))
        
        admin_labs = [(lab_id, lab_name, True) for lab_id, lab_name in c.fetchall()]

        c_connection.execute('''SELECT lab_id FROM connection_user_to_lab 
                             WHERE user_id = ?''', (user_id,))
        
        member_lab_ids = [row[0] for row in c_connection.fetchall()]

        member_labs = []
        if member_lab_ids:
            placeholders = ','.join(['?' for _ in member_lab_ids])
            c.execute(f'''SELECT id, name FROM labs 
                       WHERE id IN ({placeholders}) 
                       AND creator_id != ?''', 
                     member_lab_ids + [user_id])
            
            member_labs = [(lab_id, lab_name, False) for lab_id, lab_name in c.fetchall()]

        return admin_labs + member_labs
    
    except:
        return []
    
    finally:
        conn.close()
        conn_connection.close()