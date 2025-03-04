import os
import sqlite3
import json
from datetime import datetime, timedelta, timezone

class Task:
    def __init__(self, name: str, description: str, stages: list):
        self.name = name
        self.description = description
        self.stages = stages
        self.task_id = None

def init_db():
    if not os.path.exists('database'):
        os.makedirs('database')

    users_conn = sqlite3.connect('database/users.db')
    users_c = users_conn.cursor()

    users_c.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     telegram_id TEXT NOT NULL,
                     selected_lab TEXT DEFAULT NULL,
                     is_admin INTEGER NOT NULL DEFAULT 0)''')
    
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
                     equipment_id INTEGER NOT NULL,
                     task_id INTEGER NOT NULL)''')
    
    labs_conn.commit()
    labs_conn.close()
    
    connection_conn = sqlite3.connect('database/connection.db')
    connection_c = connection_conn.cursor()

    connection_c.execute('''CREATE TABLE IF NOT EXISTS connection_user_to_task
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id TEXT NOT NULL,
                     task_id INTEGER NOT NULL)''')
    
    connection_c.execute('''CREATE TABLE IF NOT EXISTS connection_user_to_lab
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id TEXT NOT NULL,
                     lab_id INTEGER NOT NULL)''')
    
    connection_conn.commit()
    connection_conn.close()

def is_user_registered(telegram_id: str):
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT COUNT(*) FROM users WHERE telegram_id = ?''', (telegram_id,))
        count = c.fetchone()[0]
        return count > 0
    except:
        return 'error'
    finally:
        conn.close()

def add_user(telegram_id: str):
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO users (telegram_id) VALUES (?)''', (telegram_id,))
        conn.commit()
        return True
    except:
        return 'error'
    finally:
        conn.close()

def is_user_admin_of_any_lab(telegram_id: str):
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT COUNT(*) FROM labs WHERE creator_id = ?''', (telegram_id,))
        count = c.fetchone()[0]
        return count > 0
    except:
        return 'error'
    finally:
        conn.close()

def create_template(name: str, description: str, stages: str):
    conn = sqlite3.connect('database/tasks.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO templates (name, description, stages) VALUES (?, ?, ?)''',
                  (name, description, stages))
        conn.commit()
        return True
    except:
        return 'error'
    finally:
        conn.close()

def delete_template(id: int):
    conn = sqlite3.connect('database/tasks.db')
    c = conn.cursor()
    try:
        c.execute('DELETE FROM templates WHERE id = ?', (id,))
        conn.commit()
        return True
    except:
        return 'error'
    finally:
        conn.close()

def assign_task_to_user(templates_id: int, user_id: str):
    conn_tasks = sqlite3.connect('database/tasks.db')
    c_tasks = conn_tasks.cursor()
    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()
    try:
        c_tasks.execute('''INSERT INTO tasks (templates_id) VALUES (?)''', (templates_id,))
        conn_tasks.commit()
        task_id = c_tasks.lastrowid
        c_connection.execute('''INSERT INTO connection_user_to_task (user_id, task_id) VALUES (?, ?)''',
                             (user_id, task_id))
        conn_connection.commit()
        return True
    except:
        return 'error'
    finally:
        conn_tasks.close()
        conn_connection.close()

def unassign_task_to_user(user_id: int, task_id: int):
    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()
    conn_tasks = sqlite3.connect('database/tasks.db')
    c_tasks = conn_tasks.cursor()
    try:
        c_connection.execute('''DELETE FROM connection_user_to_task WHERE user_id = ? AND task_id = ?''',
                             (user_id, task_id))
        conn_connection.commit()
        c_connection.execute('''SELECT COUNT(*) FROM connection_user_to_task WHERE task_id = ?''', (task_id,))
        count = c_connection.fetchone()[0]
        if count == 0:
            c_tasks.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn_tasks.commit()
        return True
    except:
        return 'error'
    finally:
        conn_connection.close()
        conn_tasks.close()

def create_connection_user_to_lab(user_id: str, lab_id: int):
    conn = sqlite3.connect('database/connection.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT COUNT(*) FROM connection_user_to_lab WHERE user_id = ? AND lab_id = ?''',
                  (user_id, lab_id))
        if c.fetchone()[0] > 0:
            return True
        c.execute('''INSERT INTO connection_user_to_lab (user_id, lab_id) VALUES (?, ?)''',
                  (user_id, lab_id))
        conn.commit()
        return True
    except:
        return 'error'
    finally:
        conn.close()

def create_lab(name: str, creator_id: str):
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO labs (name, admins) VALUES (?, ?)''', (name, json.dumps([creator_id])))
        conn.commit()
        lab_id = c.lastrowid
        connection_result = create_connection_user_to_lab(creator_id, lab_id)
        if connection_result == 'error' or connection_result is False:
            return 'error'
        return lab_id
    except:
        return 'error'
    finally:
        conn.close()

def delete_lab(id: int):
    conn_labs = sqlite3.connect('database/labs.db')
    c_labs = conn_labs.cursor()
    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()
    try:
        c_labs.execute('SELECT id FROM equipments WHERE lab_id = ?', (id,))
        equipment_ids = [row[0] for row in c_labs.fetchall()]
        for equipment_id in equipment_ids:
            c_labs.execute('DELETE FROM reserve WHERE equipment_id = ?', (equipment_id,))
        c_labs.execute('DELETE FROM equipments WHERE lab_id = ?', (id,))
        c_labs.execute('DELETE FROM labs WHERE id = ?', (id,))
        c_connection.execute('DELETE FROM connection_user_to_lab WHERE lab_id = ?', (id,))
        conn_labs.commit()
        conn_connection.commit()
        return True
    except:
        return 'error'
    finally:
        conn_labs.close()
        conn_connection.close()

def add_equipment(name: str, is_active: bool, lab_id: int):
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        is_active_int = 1 if is_active else 0
        c.execute('''INSERT INTO equipments (name, is_active, lab_id) VALUES (?, ?, ?)''',
                  (name, is_active_int, lab_id))
        conn.commit()
        return True
    except:
        return 'error'
    finally:
        conn.close()

def delete_equipment(id: int):
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('DELETE FROM equipments WHERE id = ?', (id,))
        conn.commit()
        return True
    except:
        return 'error'
    finally:
        conn.close()

def change_equipment_status(equipment_id: int):
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT is_active FROM equipments WHERE id = ?''', (equipment_id,))
        result = c.fetchone()
        if result is None:
            return False
        current_status = result[0]
        new_status = 0 if current_status == 1 else 1
        c.execute('''UPDATE equipments SET is_active = ? WHERE id = ?''', (new_status, equipment_id))
        conn.commit()
        return True
    except:
        return "error"
    finally:
        conn.close()

def get_equipment_list(lab_id: int) -> list:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT id FROM equipments WHERE lab_id = ?''', (lab_id,))
        return [row[0] for row in c.fetchall()]
    except:
        return []
    finally:
        conn.close()

def get_equipment_by_id(equipment_id: int) -> dict:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT id, name, is_active, lab_id FROM equipments WHERE id = ?''', (equipment_id,))
        result = c.fetchone()
        if result is None:
            return None
        return {'id': result[0], 'name': result[1], 'is_active': bool(result[2]), 'lab_id': result[3]}
    except:
        return None
    finally:
        conn.close()

def add_reserve(user_id: int, equipment_id: int, start_time: str, end_time: str, task_id: int):
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT is_active FROM equipments WHERE id = ?''', (equipment_id,))
        result = c.fetchone()
        if result is None or result[0] == 0:
            return False
        c.execute('''SELECT COUNT(*) FROM reserve WHERE equipment_id = ? AND 
                     ((start_time <= ? AND end_time >= ?) OR (start_time <= ? AND end_time >= ?) OR 
                     (start_time >= ? AND end_time <= ?))''',
                  (equipment_id, start_time, start_time, end_time, end_time, start_time, end_time))
        if c.fetchone()[0] > 0:
            return False
        c.execute('''INSERT INTO reserve (user_id, equipment_id, start_time, end_time, task_id) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, equipment_id, start_time, end_time, task_id))
        conn.commit()
        return True
    except:
        return "error"
    finally:
        conn.close()

def delete_reserve(reserve_id: int) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT COUNT(*) FROM reserve WHERE id = ?''', (reserve_id,))
        if c.fetchone()[0] == 0:
            return False
        c.execute('DELETE FROM reserve WHERE id = ?', (reserve_id,))
        conn.commit()
        return True
    except:
        return "error"
    finally:
        conn.close()

def user_task_exists(user_id: int, task_id: int):
    conn = sqlite3.connect('database/connection.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT COUNT(*) FROM connection_user_to_task WHERE user_id = ? AND task_id = ?''',
                  (user_id, task_id))
        count = c.fetchone()[0]
        return count > 0
    except:
        return "error"
    finally:
        conn.close()

def user_is_admin(user_id: str):
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT is_admin FROM users WHERE telegram_id = ?''', (user_id,))
        result = c.fetchone()
        if result is None:
            return False
        return result[0] == 1
    except:
        return "error"
    finally:
        conn.close()

def get_labname_by_id(lab_id: int) -> str:
    if lab_id is None or lab_id == "":
        return "Не выбрано"
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT name FROM labs WHERE id = ?''', (lab_id,))
        result = c.fetchone()
        if result is None:
            return None
        return result[0]
    except:
        return None
    finally:
        conn.close()

def get_available_labs(user_id: str) -> list:
    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()
    try:
        c_connection.execute('''SELECT lab_id FROM connection_user_to_lab WHERE user_id = ?''', (user_id,))
        lab_ids = [row[0] for row in c_connection.fetchall()]
        return lab_ids
    except:
        return []
    finally:
        conn_connection.close()

def user_get_selected_lab_id(user_id: str) -> int:
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT selected_lab FROM users WHERE telegram_id = ?''', (user_id,))
        result = c.fetchone()
        if result is None:
            return None
        return result[0]
    except:
        return None
    finally:
        conn.close()

def user_set_admin(user_id: str, is_admin: bool):
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT COUNT(*) FROM users WHERE telegram_id = ?''', (user_id,))
        if c.fetchone()[0] == 0:
            return False
        is_admin_int = 1 if is_admin else 0
        c.execute('''UPDATE users SET is_admin = ? WHERE telegram_id = ?''', (is_admin_int, user_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def is_user_admin_of_lab(user_id: str, lab_id: int) -> bool:
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT admins FROM labs WHERE id = ?''', (lab_id,))
        result = c.fetchone()
        if result is None:
            return False
        admins_json = result[0]
        admin_ids = json.loads(admins_json)
        return user_id in admin_ids
    except json.JSONDecodeError:
        return False
    except:
        return False
    finally:
        conn.close()

def add_template(name: str, description: str, stages: list) -> int:
    conn = sqlite3.connect('database/tasks.db')
    c = conn.cursor()
    try:
        stages_json = json.dumps(stages)
        c.execute('''INSERT INTO templates (name, description, stages) VALUES (?, ?, ?)''',
                  (name, description, stages_json))
        conn.commit()
        template_id = c.lastrowid
        return template_id
    except:
        return 'error'
    finally:
        conn.close()

def user_select_lab(user_id: str, lab_id: int) -> bool:
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT COUNT(*) FROM users WHERE telegram_id = ?''', (user_id,))
        if c.fetchone()[0] == 0:
            return False
        if lab_id is not None:
            available_labs = get_available_labs(user_id)
            if lab_id not in available_labs:
                return False
        c.execute('''UPDATE users SET selected_lab = ? WHERE telegram_id = ?''', (lab_id, user_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_tasks_by_user_id(user_id: str) -> list:
    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()
    task_conn_connection = sqlite3.connect('database/tasks.db')
    task_c_connection = task_conn_connection.cursor()
    try:
        tasks = []
        c_connection.execute('''SELECT task_id FROM connection_user_to_task WHERE user_id = ?''', (user_id,))
        task_ids = [row[0] for row in c_connection.fetchall()]
        for task_id in task_ids:
            task_c_connection.execute('''SELECT templates_id FROM tasks WHERE id = ?''', (task_id,))
            template_id = task_c_connection.fetchone()[0]
            task_c_connection.execute('''SELECT name, description, stages FROM templates WHERE id = ?''',
                                      (template_id,))
            name, description, stages_json = task_c_connection.fetchone()
            stages = json.loads(stages_json)
            task = Task(name=name, description=description, stages=stages)
            task.task_id = task_id
            tasks.append(task)
        return tasks
    except:
        return []
    finally:
        task_conn_connection.close()
        conn_connection.close()

def get_equipment_reservations(equipment_id):
    """Возвращает список броней для оборудования."""
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT start_time, end_time FROM reserve WHERE equipment_id = ?''', (equipment_id,))
        return [(row[0], row[1]) for row in c.fetchall()]
    except:
        return []
    finally:
        conn.close()

def get_equipment_id_by_name(equipment_name, lab_id):
    """Возвращает ID оборудования по имени и lab_id."""
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT id FROM equipments WHERE name = ? AND lab_id = ?''', (equipment_name, lab_id))
        result = c.fetchone()
        return result[0] if result else None
    except:
        return None
    finally:
        conn.close()

def get_branch_duration(branch):
    """Вычисляет продолжительность одной ветки в минутах."""
    branch_duration = 0
    for step in branch:
        timing = step["timing"]  # ['5a', '15p', '7a']
        active_time = int(timing[0].rstrip('a'))
        passive_time = int(timing[1].rstrip('p'))
        processing_time = int(timing[2].rstrip('a'))
        branch_duration += active_time + passive_time + processing_time
    return branch_duration

def get_task_duration(task):
    """Вычисляет продолжительность задачи с учётом параллельных веток."""
    branch_durations = [get_branch_duration(branch) for branch in task.stages]
    return max(branch_durations) if branch_durations else 0


def find_available_slots(task, lab_id, selected_date=None):
    """Ищет доступные временные окна для задачи на указанную дату."""
    if selected_date is None:
        selected_date = datetime.now(tz=timezone(timedelta(hours=10))).replace(second=0, microsecond=0)
    else:
        selected_date = selected_date.replace(hour=8, minute=0, second=0, microsecond=0)

    day_start = selected_date.replace(hour=8, minute=0)
    day_end = selected_date.replace(hour=17, minute=0)

    print(f"find_available_slots: Date {selected_date}, Day start {day_start}, Day end {day_end}")  # Отладка
    
    total_duration = reserve_task_equipment(None, task, lab_id, datetime(2023, 1, 1, 0, 0), None, dry_run=True)
    print(f"Total duration: {total_duration}")  # Отладка
    if not total_duration or total_duration <= 0:
        print("No valid duration found")  # Отладка
        return []

    equipment_usage = {}
    for branch_idx, branch in enumerate(task.stages):
        branch_offset = 0
        if branch_idx > 0:
            first_step = task.stages[0][0]
            branch_offset = int(first_step["timing"][0].rstrip('a'))
        for step in branch:
            equipment_name = step["equipment"]
            step_duration = sum(int(t.rstrip('ap')) for t in step["timing"])
            if equipment_name not in equipment_usage:
                equipment_usage[equipment_name] = []
            equipment_usage[equipment_name].append((branch_offset, step_duration))
            branch_offset += step_duration

    print(f"Equipment usage: {equipment_usage}")  # Отладка

    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    equipment_instances = {}
    c.execute('''SELECT id, name FROM equipments WHERE lab_id = ? AND is_active = 1''', (lab_id,))
    for equip_id, equip_name in c.fetchall():
        if equip_name not in equipment_instances:
            equipment_instances[equip_name] = []
        equipment_instances[equip_name].append(equip_id)
    conn.close()

    print(f"Equipment instances: {equipment_instances}")  # Отладка

    available_slots = []
    current_time = day_start
    
    while current_time + timedelta(minutes=total_duration) <= day_end:
        slot_end = current_time + timedelta(minutes=total_duration)
        is_slot_available = True
        
        for equipment_name, usages in equipment_usage.items():
            if equipment_name not in equipment_instances:
                is_slot_available = False
                print(f"Equipment {equipment_name} not found in lab")  # Отладка
                break
            available_equip_ids = equipment_instances[equipment_name].copy()
            used_equip_ids = set()

            for start_offset, duration in usages:
                step_start = current_time + timedelta(minutes=start_offset)
                step_end = step_start + timedelta(minutes=duration)
                assigned = False

                for equip_id in available_equip_ids:
                    if equip_id not in used_equip_ids:
                        reservations = get_equipment_reservations(equip_id)
                        is_free = True
                        for res_start, res_end in reservations:
                            res_start_dt = datetime.strptime(res_start, "%Y-%m-%d %H:%M")
                            res_end_dt = datetime.strptime(res_end, "%Y-%m-%d %H:%M")
                            if step_start < res_end_dt and step_end > res_start_dt:
                                is_free = False
                                break
                        if is_free:
                            used_equip_ids.add(equip_id)
                            assigned = True
                            break
                if not assigned:
                    is_slot_available = False
                    print(f"No available equipment for {equipment_name} at {step_start} - {step_end}")  # Отладка
                    break
            if not is_slot_available:
                break

        if is_slot_available:
            available_slots.append((current_time, slot_end))
            print(f"Slot found: {current_time} - {slot_end}")  # Отладка
            if len(available_slots) == 1:
                minutes = current_time.minute
                if minutes < 30:
                    delta_to_30 = 30 - minutes
                    current_time += timedelta(minutes=delta_to_30)
                else:
                    delta_to_next_hour = 60 - minutes
                    current_time += timedelta(minutes=delta_to_next_hour)
            elif len(available_slots) > 1:
                current_time += timedelta(minutes=15)
        else:
            current_time += timedelta(minutes=1)
    
    return available_slots


  

def reserve_task_equipment(user_id, task, lab_id, start_time, end_time, dry_run=False):
    """Бронирует оборудование, находя минимальное время выполнения с учетом параллельных веток и фаз."""
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        # Получаем task_id
        if not dry_run:
            conn_connection = sqlite3.connect('database/connection.db')
            c_connection = conn_connection.cursor()
            conn_tasks = sqlite3.connect('database/tasks.db')
            c_tasks = conn_tasks.cursor()
            c_connection.execute('''SELECT task_id FROM connection_user_to_task WHERE user_id = ?''', (user_id,))
            task_ids = [row[0] for row in c_connection.fetchall()]
            task_id = None
            stages_json = json.dumps(task.stages)
            for tid in task_ids:
                c_tasks.execute('''SELECT templates_id FROM tasks WHERE id = ?''', (tid,))
                templates_id = c_tasks.fetchone()[0]
                c_tasks.execute('''SELECT stages FROM templates WHERE id = ?''', (templates_id,))
                stored_stages = c_tasks.fetchone()[0]
                if stored_stages == stages_json:
                    task_id = tid
                    break
            if task_id is None:
                raise ValueError("Could not find matching task_id.")
            conn_connection.close()
            conn_tasks.close()
        else:
            task_id = None

        # Доступное оборудование
        c.execute('''SELECT id, name FROM equipments WHERE lab_id = ? AND is_active = 1''', (lab_id,))
        equipment_instances = {}
        for equip_id, equip_name in c.fetchall():
            if equip_name not in equipment_instances:
                equipment_instances[equip_name] = []
            equipment_instances[equip_name].append(equip_id)

        # Проверка доступности оборудования
        def is_equipment_available(equip_id, step_start, step_end):
            reservations = get_equipment_reservations(equip_id)
            for res_start, res_end in reservations:
                res_start_dt = datetime.strptime(res_start, "%Y-%m-%d %H:%M")
                res_end_dt = datetime.strptime(res_end, "%Y-%m-%d %H:%M")
                if step_start < res_end_dt and step_end > res_start_dt:
                    return False
            return True

        # Структура шага: [(branch_idx, step_idx, start_time, end_time, active_start1, active_end1, active_start2, active_end2, equip_id)]
        best_schedule = None
        min_duration = float('inf')

        # Функция для вычисления длительности ветки
        def get_branch_duration(branch):
            return sum(int(t.rstrip('ap')) for step in branch for t in step["timing"])

        # Перебор смещений второй ветки относительно первой
        branch1_duration = get_branch_duration(task.stages[0])
        branch2_duration = get_branch_duration(task.stages[1]) if len(task.stages) > 1 else 0
        max_shift = branch1_duration + branch2_duration  # Максимальный диапазон для поиска

        for shift in range(0, max_shift + 1, 1):  # Шаг 1 минута
            schedule = []
            equipment_used = {}  # {equip_id: [(start, end), ...]}
            active_times = []    # [(start, end), ...] для проверки пересечений

            # Размещаем первую ветку с начала
            offset = 0
            for step_idx, step in enumerate(task.stages[0]):
                active_time = int(step["timing"][0].rstrip('a'))
                passive_time = int(step["timing"][1].rstrip('p'))
                processing_time = int(step["timing"][2].rstrip('a'))
                step_start = start_time + timedelta(minutes=offset)
                active_end1 = step_start + timedelta(minutes=active_time)
                passive_end = active_end1 + timedelta(minutes=passive_time)
                step_end = passive_end + timedelta(minutes=processing_time)

                equip_id = None
                for eid in equipment_instances.get(step["equipment"], []):
                    if is_equipment_available(eid, step_start, step_end):
                        equip_id = eid
                        break
                if equip_id is None:
                    break  # Пропускаем этот вариант, если оборудование занято

                schedule.append((0, step_idx, step_start, step_end, step_start, active_end1, passive_end, step_end, equip_id))
                active_times.append((step_start, active_end1))
                active_times.append((passive_end, step_end))
                equipment_used[equip_id] = equipment_used.get(equip_id, []) + [(step_start, step_end)]
                offset += active_time + passive_time + processing_time

            if len(schedule) != len(task.stages[0]):
                continue  # Первая ветка не размещена полностью

            # Размещаем вторую ветку со смещением
            offset = shift
            branch2_placed = True
            for step_idx, step in enumerate(task.stages[1]):
                active_time = int(step["timing"][0].rstrip('a'))
                passive_time = int(step["timing"][1].rstrip('p'))
                processing_time = int(step["timing"][2].rstrip('a'))
                step_start = start_time + timedelta(minutes=offset)
                active_end1 = step_start + timedelta(minutes=active_time)
                passive_end = active_end1 + timedelta(minutes=passive_time)
                step_end = passive_end + timedelta(minutes=processing_time)

                equip_id = None
                for eid in equipment_instances.get(step["equipment"], []):
                    if eid in equipment_used:
                        for res_start, res_end in equipment_used[eid]:
                            if step_start < res_end and step_end > res_start:
                                break
                        else:
                            if is_equipment_available(eid, step_start, step_end):
                                equip_id = eid
                                break
                    elif is_equipment_available(eid, step_start, step_end):
                        equip_id = eid
                        break
                if equip_id is None:
                    branch2_placed = False
                    break

                schedule.append((1, step_idx, step_start, step_end, step_start, active_end1, passive_end, step_end, equip_id))
                active_times.append((step_start, active_end1))
                active_times.append((passive_end, step_end))
                equipment_used[equip_id] = equipment_used.get(equip_id, []) + [(step_start, step_end)]
                offset += active_time + passive_time + processing_time

            if not branch2_placed or len(schedule) != len(task.stages[0]) + len(task.stages[1]):
                continue

            # Проверка пересечения активных фаз
            active_times.sort()
            overlap = False
            for i in range(1, len(active_times)):
                if active_times[i][0] < active_times[i-1][1]:
                    overlap = True
                    break
            if overlap:
                continue

            # Вычисляем длительность
            end_time = max(s[3] for s in schedule)
            duration = (end_time - start_time).total_seconds() / 60
            if duration < min_duration:
                min_duration = duration
                best_schedule = schedule

        if best_schedule is None:
            raise ValueError("No valid schedule found.")

        # Выполняем бронирование
        if not dry_run:
            for _, _, step_start, step_end, _, _, _, _, equip_id in best_schedule:
                c.execute('''INSERT INTO reserve (user_id, equipment_id, start_time, end_time, task_id)
                             VALUES (?, ?, ?, ?, ?)''',
                          (user_id, equip_id, step_start.strftime("%Y-%m-%d %H:%M"),
                           step_end.strftime("%Y-%m-%d %H:%M"), task_id))
            conn.commit()

        return min_duration if dry_run else True

    except Exception as e:
        print(f"Error in reserve_task_equipment: {e}")
        if not dry_run:
            conn.rollback()
        return False
    finally:
        conn.close()


def get_user_reservations(user_id):
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT r.id, r.start_time, r.end_time, r.equipment_id, r.task_id 
                     FROM reserve r 
                     WHERE r.user_id = ? 
                     ORDER BY r.start_time''', (user_id,))
        reservations = c.fetchall()

        tasks = get_tasks_by_user_id(user_id)
        # Создаем словарь задач для быстрого поиска по task_id
        task_dict = {str(task.task_id): task for task in tasks}
        reserved_steps = []

        for res_id, start_time, end_time, equipment_id, task_id in reservations:
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            except ValueError as e:
                print(f"Invalid datetime format: {e}")
                continue

            equipment = get_equipment_by_id(equipment_id)
            if not equipment:
                continue

            # Приводим task_id из резервации к строке для совместимости
            task = task_dict.get(str(task_id))
            if not task:
                continue

            # Поиск соответствующего шага в задаче
            for branch in task.stages:
                for step in branch:
                    if step["equipment"] != equipment["name"]:
                        continue

                    # Расчет длительности шага
                    try:
                        step_duration = sum(int(t.rstrip('ap').rstrip('m')) for t in step["timing"])
                    except ValueError as e:
                        print(f"Invalid timing format: {e}")
                        continue

                    reservation_duration = (end_dt - start_dt).total_seconds() / 60
                    if abs(reservation_duration - step_duration) < 1:
                        reserved_steps.append({
                            "task_name": task.name,
                            "step_name": step["name"],
                            "equipment": step["equipment"],
                            "start_time": start_dt,
                            "end_time": end_dt,
                            "task_id": task.task_id
                        })
                        break  # Прерываем после первого совпадения в ветке
                else:
                    continue  # Переходим к следующей ветке, если не нашли в текущей
                break  # Прерываем поиск по веткам после нахождения совпадения

        reserved_steps.sort(key=lambda x: x["start_time"])
        return reserved_steps
    except Exception as e:
        print(f"Error in get_user_reservations: {e}")
        return []
    finally:
        conn.close()


def get_all_users():
    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT telegram_id FROM users''')
        return [row[0] for row in c.fetchall()]
    except:
        return []
    finally:
        conn.close()

def get_equipment_summary_by_lab(lab_id):
    """Возвращает словарь с количеством оборудования по названию для указанной лаборатории."""
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT name, COUNT(*) as count 
                     FROM equipments 
                     WHERE lab_id = ? AND is_active = 1 
                     GROUP BY name''', (lab_id,))
        result = {row[0]: row[1] for row in c.fetchall()}
        return result
    except:
        return {}
    finally:
        conn.close()


def delete_reservations_by_task(user_id, task_id):
    """Удаляет все брони для указанной задачи пользователя."""
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    try:

        conn_connection = sqlite3.connect('database/connection.db')
        c_connection = conn_connection.cursor()
        c_connection.execute('''SELECT COUNT(*) FROM connection_user_to_task WHERE user_id = ? AND task_id = ?''',
                             (user_id, task_id))
        if c_connection.fetchone()[0] == 0:
            return False
        

        c.execute('''DELETE FROM reserve WHERE user_id = ? AND task_id = ?''', (user_id, task_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in delete_reservations_by_task: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
        if 'conn_connection' in locals():
            conn_connection.close()

def remove_equipments(lab_id: int, equipment_list: list) -> list:
    """Удаляет указанное количество оборудования из лаборатории. Возвращает список ошибок."""
    conn = sqlite3.connect('database/labs.db')
    c = conn.cursor()
    errors = []
    
    try:
        for line in equipment_list:
            if len(line.split(' ')) != 2:
                errors.append(line)
                continue
            name, count_str = line.split(' ')
            try:
                count_to_remove = int(count_str)
                if count_to_remove <= 0:
                    errors.append(f"{line} (количество должно быть положительным)")
                    continue
            except ValueError:
                errors.append(line)
                continue
            
            # Получаем текущее количество оборудования
            c.execute('''SELECT id FROM equipments WHERE name = ? AND lab_id = ? AND is_active = 1''', 
                      (name, lab_id))
            equip_ids = [row[0] for row in c.fetchall()]
            current_count = len(equip_ids)
            
            if current_count < count_to_remove:
                errors.append(f"{name}: запрошено удалить {count_to_remove}, но доступно только {current_count}")
                continue
            
            # Удаляем указанное количество
            for i in range(count_to_remove):
                equip_id = equip_ids[i]
                c.execute('DELETE FROM reserve WHERE equipment_id = ?', (equip_id,))
                c.execute('DELETE FROM equipments WHERE id = ?', (equip_id,))
        
        conn.commit()
    except Exception as e:
        print(f"Error in remove_equipments: {e}")
        conn.rollback()
        errors.append("Произошла ошибка при удалении оборудования")
    finally:
        conn.close()
    
    return errors


def share_template(template_id: int, from_user_id: str, to_user_id: str) -> bool:
    """Передает шаблон задачи от одного пользователя другому."""
    conn_tasks = sqlite3.connect('database/tasks.db')
    c_tasks = conn_tasks.cursor()
    conn_connection = sqlite3.connect('database/connection.db')
    c_connection = conn_connection.cursor()
    try:
        # Проверяем, существует ли шаблон
        c_tasks.execute('''SELECT COUNT(*) FROM templates WHERE id = ?''', (template_id,))
        if c_tasks.fetchone()[0] == 0:
            return False
        
        # Создаем новую задачу на основе шаблона
        c_tasks.execute('''INSERT INTO tasks (templates_id) VALUES (?)''', (template_id,))
        new_task_id = c_tasks.lastrowid
        
        # Привязываем задачу к получателю
        c_connection.execute('''INSERT INTO connection_user_to_task (user_id, task_id) VALUES (?, ?)''',
                             (to_user_id, new_task_id))
        
        conn_tasks.commit()
        conn_connection.commit()
        return True
    except Exception as e:
        print(f"Error in share_template: {e}")
        return False
    finally:
        conn_tasks.close()
        conn_connection.close()