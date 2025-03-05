from types import NoneType
import telebot
from datetime import datetime, tzinfo, timezone, timedelta
import sqlite3
from telebot.types import BotCommand

import db
import os
from dotenv import load_dotenv
import threading
import time

load_dotenv()

token = os.environ.get('TELEGRAM_BOT_TOKEN')

if not token:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
    exit(1)

bot = telebot.TeleBot(token, parse_mode="HTML")

# Глобальные словари для временного хранения
user_tasks = {}  # {user_id: Task}
user_steps = {}  # {user_id: [{"name": str, "equipment": str, "timing": list}, ...]}
# Словарь блокировок для каждого пользователя
user_locks = {}
lock_for_locks = threading.Lock()  # Блокировка для создания новых блокировок в user_locks

def get_user_lock(user_id):
    """Получает или создаёт блокировку для конкретного пользователя."""
    with lock_for_locks:  # Синхронизация доступа к user_locks
        if user_id not in user_locks:
            user_locks[user_id] = threading.Lock()
        return user_locks[user_id]

def isFirstMessage(message):
    return not db.is_user_registered(str(message.from_user.id))

@bot.message_handler(func=lambda message: isFirstMessage(message))
def firstMessageHandler(message):
    db.add_user(message.from_user.id)
    try:
        with open("greeting_text.txt", 'r', encoding='utf-8') as text:
            greeting_message = text.read()
            bot.send_message(message.from_user.id, greeting_message)
    except UnicodeDecodeError:
        try:
            with open("greeting_text.txt", 'r', encoding='windows-1251') as text:
                greeting_message = text.read()
                bot.send_message(message.from_user.id, greeting_message)
        except:
            bot.send_message(message.from_user.id, "Добро пожаловать в task_lab!")
    showMainMenu(message)

@bot.message_handler(commands=['main_menu'])
def showMainMenu(message):
    available_labs = db.get_available_labs(str(message.from_user.id))
    db.user_select_lab(str(message.from_user.id), None)
    if available_labs:
        lab_buttons = {}
        for lab_id in available_labs:
            prefix = "👑 " if db.is_user_admin_of_lab(str(message.from_user.id), lab_id) else "🔬 "
            lab_buttons[f'{prefix}[id{lab_id}] {db.get_labname_by_id(lab_id)}'] = {"callback_data": f"lab_menu?{lab_id}"}
        markup = telebot.util.quick_markup(lab_buttons)
        bot.send_message(message.from_user.id, "Список доступных вам лабораторий. Выберите подходящую:", reply_markup=markup)
    else:
        bot.send_message(message.from_user.id, "К сожалению, у вас пока нет доступных лабораторий.")

@bot.callback_query_handler(func=lambda query: "lab_menu" in query.data
                            and int(query.data.split('?')[1]) in db.get_available_labs(str(query.from_user.id)))
def lab_menu(query):
    lab_id = query.data.split('?')[1]
    markup = telebot.util.quick_markup({
        "Ссылка - приглашение": {"callback_data": f"link_to?{lab_id}"},
        "Создать задачу": {"callback_data": "create_task"},
        "Список задач": {"callback_data": "task_list"},
        "Мои задачи": {"callback_data": f"my_tasks?{lab_id}"}
    })
    db.user_select_lab(str(query.from_user.id), int(lab_id))
    bot.send_message(query.from_user.id, f"Вы в меню лаборатории [id{lab_id}] <b>'{db.get_labname_by_id(lab_id)}'</b>. Что вы хотите сделать?",
                     reply_markup=markup)
    bot.answer_callback_query(query.id)

@bot.callback_query_handler(func=lambda query: "link_to" in query.data
                            and int(query.data.split('?')[1]) in db.get_available_labs(str(query.from_user.id)))
def get_link_to_lab(query):
    lab_id = query.data.split('?')[1]
    bot.send_message(query.from_user.id, "Ссылка на присоединение к текущей лаборатории:\n"
                                         f"<code>t.me/tasks_lab_bot?start=lab_{lab_id}_{query.from_user.id}</code>\n"
                                         f"<i> (нажмите, чтобы скопировать) </i>")

@bot.callback_query_handler(func=lambda query: query.data == "create_task")
def create_task(query):
    user_id = str(query.from_user.id)
    with get_user_lock(user_id):
        user_tasks[user_id] = None
    bot.send_message(query.from_user.id, "Пожалуйста, введите название и описание <b>ответом</b> на сообщение в следующем формате:\nНазвание...\nОписание...")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите название и описание" in message.reply_to_message.text
                     and 8127922870 == message.reply_to_message.from_user.id)
def apply_task_name_and_description(message):
    def msg():
        bot.send_message(message.from_user.id, "Пожалуйста, введите название и описание <b>ответом</b> на сообщение в следующем формате:\nНазвание...\nОписание...")
    
    user_id = str(message.from_user.id)
    lines = message.text.split("\n")

    if len(lines) < 2:
        bot.send_message(message.from_user.id, "Ошибка: Отсутствует название или описание\n")
        msg()
        return

    title = lines[0]
    title_length = len(title)
    description = lines[1]
    description_length = len(description)

    if title_length > 100:
        bot.send_message(message.from_user.id, f"Ошибка! Название {title_length}/100 симв..\n")
        msg()
        return
    elif description_length > 1500:
        bot.send_message(message.from_user.id, f"Ошибка! Описание {description_length}/1500 симв..\n")
        msg()
        return
    
    with get_user_lock(user_id):
        user_tasks[user_id] = db.Task(title, description, [])
    markup = telebot.util.quick_markup({"Добавить шаги": {"callback_data": "хз"}})
    bot.send_message(message.from_user.id, f"Название и описание сохранены в задачу '{title}'. Теперь введите шаги.", reply_markup=markup)

@bot.callback_query_handler(func=lambda query: query.data == "хз")
def add_step(query):
    user_id = str(query.from_user.id)
    with get_user_lock(user_id):
        if user_id not in user_steps:
            user_steps[user_id] = []
    bot.send_message(query.from_user.id, 
                     "Введите данные для шага в формате:\n"
                     "Название\n"
                     "Название_прибора\n"
                     "Активное время: X\n"
                     "Время ожидания: Y\n"
                     "Время обработки: Z\n\n"
                     "Пример:\n"
                     "Подготовка образца\n"
                     "Микроскоп\n"
                     "Активное время: 5\n"
                     "Время ожидания: 15\n"
                     "Время обработки: 7")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "Введите данные для шага" in message.reply_to_message.text
                     and 8127922870 == message.reply_to_message.from_user.id)
def apply_step_data(message):
    user_id = str(message.from_user.id)
    lines = message.text.split("\n")

    if len(lines) != 5:
        bot.send_message(message.from_user.id, "Ошибка: Нужно ввести 5 строк (Название, Прибор, Активное время, Время ожидания, Время обработки).")
        add_step_helper(user_id)
        return
    
    name, equipment, active_time_str, passive_time_str, processing_time_str = lines

    if len(name) > 100:
        bot.send_message(message.from_user.id, f"Ошибка: Название слишком длинное ({len(name)}/100 символов).")
        add_step_helper(user_id)
        return

    lab_id = db.user_get_selected_lab_id(user_id)
    if not lab_id:
        bot.send_message(message.from_user.id, "Ошибка: Сначала выберите лабораторию.")
        add_step_helper(user_id)
        return
    
    equipment_id = db.get_equipment_id_by_name(equipment, lab_id)
    if not equipment_id:
        bot.send_message(message.from_user.id, f"Ошибка: Оборудование '{equipment}' не найдено в лаборатории [id{lab_id}].")
        add_step_helper(user_id)
        return
    
    if not active_time_str.startswith("Активное время: "):
        bot.send_message(message.from_user.id, "Ошибка: Строка должна начинаться с 'Активное время: '.")
        add_step_helper(user_id)
        return
    try:
        active_time = int(active_time_str.replace("Активное время: ", "").strip())
        if active_time < 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.from_user.id, "Ошибка: Активное время должно быть положительным числом.")
        add_step_helper(user_id)
        return

    if not passive_time_str.startswith("Время ожидания: "):
        bot.send_message(message.from_user.id, "Ошибка: Строка должна начинаться с 'Время ожидания: '.")
        add_step_helper(user_id)
        return
    try:
        passive_time = int(passive_time_str.replace("Время ожидания: ", "").strip())
        if passive_time < 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.from_user.id, "Ошибка: Время ожидания должно быть положительным числом.")
        add_step_helper(user_id)
        return

    if not processing_time_str.startswith("Время обработки: "):
        bot.send_message(message.from_user.id, "Ошибка: Строка должна начинаться с 'Время обработки: '.")
        add_step_helper(user_id)
        return
    try:
        processing_time = int(processing_time_str.replace("Время обработки: ", "").strip())
        if processing_time < 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.from_user.id, "Ошибка: Время обработки должно быть положительным числом.")
        add_step_helper(user_id)
        return

    timing = [f"{active_time}a", f"{passive_time}p", f"{processing_time}a"]
    step = {"name": name, "equipment": equipment, "timing": timing}
    with get_user_lock(user_id):
        user_steps[user_id].append(step)
    
    markup = telebot.util.quick_markup({
        "Добавить ещё шаг": {"callback_data": "add_another_step"},
        "Завершить": {"callback_data": "finish_steps"}
    })
    bot.send_message(message.from_user.id, f"Шаг '{name}' успешно добавлен. Что дальше?", reply_markup=markup)

def add_step_helper(user_id):
    bot.send_message(user_id, 
                     "Введите данные для шага в формате:\n"
                     "Название\n"
                     "Название_прибора\n"
                     "Активное время: X\n"
                     "Время ожидания: Y\n"
                     "Время обработки: Z")

@bot.callback_query_handler(func=lambda query: query.data == "add_another_step")
def add_another_step(query):
    add_step(query)

@bot.callback_query_handler(func=lambda query: query.data == "finish_steps")
def finish_steps(query):
    user_id = str(query.from_user.id)
    with get_user_lock(user_id):
        if not user_steps.get(user_id):
            bot.send_message(user_id, "Вы не добавили ни одного шага.")
            bot.answer_callback_query(query.id)
            return
        steps_list = "\n".join(f"{i+1}. {step['name']} (Прибор: {step['equipment']}, Время: {step['timing']})" 
                               for i, step in enumerate(user_steps[user_id]))
    bot.send_message(user_id, f"Ваши шаги:\n{steps_list}\n\n"
                              "Теперь укажите порядок выполнения в формате:\n"
                              "В одной строчке пишется те шаги, которые выполняются последовательно\n"
                              "Действия с разных строчек можно выполнять параллельно\n"
                              "Количество параллельных строчек не ограничено\n"
                              "Шаги (через пробел): 1 2 3\n"
                              "Шаги (через пробел): 4 5")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "Теперь укажите порядок выполнения" in message.reply_to_message.text
                     and 8127922870 == message.reply_to_message.from_user.id)
def apply_step_order(message):
    user_id = str(message.from_user.id)
    lines = message.text.split("\n")
    
    if not lines:
        bot.send_message(user_id, "Ошибка: Укажите хотя бы одну ветку шагов.")
        return
    
    branches = []
    all_indices = set()
    
    try:
        for line in lines:
            if not line.strip():
                continue
            branch = [int(x) - 1 for x in line.split()]
            branches.append(branch)
            all_indices.update(branch)
    except ValueError:
        bot.send_message(user_id, "Ошибка: Укажите номера шагов числами через пробел в каждой строке.")
        return

    with get_user_lock(user_id):
        total_steps = len(user_steps[user_id])
        
        if len(all_indices) != total_steps or max(all_indices, default=-1) >= total_steps or min(all_indices, default=0) < 0:
            bot.send_message(user_id, "Ошибка: Указаны неверные, пропущенные или повторяющиеся номера шагов.")
            return

        task = user_tasks[user_id]
        task.stages = [[user_steps[user_id][i] for i in branch] for branch in branches]
        
        template_id = db.add_template(task.name, task.description, task.stages)
        db.assign_task_to_user(templates_id=template_id, user_id=user_id)

        # Очистка временных данных
        del user_steps[user_id]
        del user_tasks[user_id]
        # Удаляем блокировку для пользователя после завершения
        if user_id in user_locks:
            del user_locks[user_id]

    confirmation = f"Задача '{task.name}' успешно сохранена со стадиями:\n"
    for i, branch in enumerate(branches, 1):
        branch_str = " ".join(str(idx + 1) for idx in branch)
        confirmation += f"Ветка {i}: {branch_str}\n"
    
    bot.send_message(user_id, confirmation)
    showMainMenu(message)

@bot.callback_query_handler(func=lambda query: query.data == "task_list")
def task_list(query):
    user_id = str(query.from_user.id)
    tasks = db.get_tasks_by_user_id(user_id=user_id)
    
    if not tasks:
        bot.send_message(query.from_user.id, "У вас нет сохранённых задач.")
    else:
        buttons = {}
        for i, task in enumerate(tasks):
            buttons[f"{i+1}. {task.name}"] = {"callback_data": f"task_{i}"}
            buttons[f"Поделиться '{task.name}'"] = {"callback_data": f"share_task_{task.task_id}"}
        
        markup = telebot.util.quick_markup(buttons)
        bot.send_message(query.from_user.id, "Ваши задачи:", reply_markup=markup)
    
    bot.answer_callback_query(query.id)

@bot.callback_query_handler(func=lambda query: query.data.startswith("share_task_"))
def share_task(query):
    user_id = str(query.from_user.id)
    task_id = int(query.data.split("_")[2])
    tasks = db.get_tasks_by_user_id(user_id)
    task = next((t for t in tasks if t.task_id == task_id), None)
    
    if not task:
        bot.send_message(query.from_user.id, "Задача не найдена.")
        bot.answer_callback_query(query.id)
        return
    
    bot.send_message(query.from_user.id, f"Ссылка для добавления задачи '{task.name}':\n"
                                         f"<code>t.me/tasks_lab_bot?start=task_{task_id}_{user_id}</code>\n"
                                         f"<i>(нажмите, чтобы скопировать)</i>")
    bot.answer_callback_query(query.id)

@bot.message_handler(commands=['start'], func=lambda message: True)
def process_invite(message):
    data = message.text[7:].split('_')
    print(data)
    user_id = str(message.from_user.id)
    
    if data[0] == 'lab':
        lab_id = int(data[1])
        creator_id = data[2]
        if lab_id not in db.get_available_labs(creator_id):
            bot.send_message(user_id, "К сожалению, ссылка на доступ к лаборатории недействительна.")
        else:
            status = db.create_connection_user_to_lab(user_id, lab_id)
            if status:
                bot.send_message(user_id, "Вы успешно добавлены в лабораторию!")
            else:
                bot.send_message(user_id, "Ошибка при добавлении в лабораторию.")
    
    elif data[0] == 'task':
        task_id = int(data[1])
        from_user_id = data[2]
        tasks = db.get_tasks_by_user_id(from_user_id)
        task = next((t for t in tasks if t.task_id == task_id), None)
        
        if not task:
            bot.send_message(user_id, "К сожалению, ссылка на задачу недействительна.")
        else:
            template_id = db.add_template(task.name, task.description, task.stages)
            status = db.assign_task_to_user(template_id, user_id)
            if status:
                bot.send_message(user_id, f"Задача '{task.name}' от пользователя {from_user_id} добавлена в ваш список задач!")
                bot.send_message(from_user_id, f"Пользователь {user_id} добавил вашу задачу '{task.name}' через ссылку.")
            else:
                bot.send_message(user_id, "Ошибка при добавлении задачи.")
    
    else:
        bot.send_message(user_id, "Неверный формат ссылки.")


@bot.callback_query_handler(func=lambda query: query.data.startswith("task_"))
def task_details(query):
    user_id = str(query.from_user.id)
    task_index = int(query.data.split("_")[1])
    
    tasks = db.get_tasks_by_user_id(user_id=user_id)
    
    if task_index < 0 or task_index >= len(tasks):
        bot.send_message(query.from_user.id, "Задача не найдена.")
        bot.answer_callback_query(query.id)
        return
    
    task = tasks[task_index]
    lab_id = db.user_get_selected_lab_id(user_id)
    
    if not lab_id:
        bot.send_message(query.from_user.id, "Сначала выберите лабораторию!")
        bot.answer_callback_query(query.id)
        return
    
    # Показываем выбор дня (сегодня + 3 дня вперед)
    now = datetime.now(tz=timezone(timedelta(hours=10))).replace(second=0, microsecond=0)
    buttons = {}
    for i in range(4):
        day = now + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        buttons[f"{day_str}"] = {
            "callback_data": f"select_day_{task_index}_{day_str}"
        }
    markup = telebot.util.quick_markup(buttons)
    bot.send_message(query.from_user.id, f"Задача: {task.name}\nВыберите день для бронирования:", reply_markup=markup)
    bot.answer_callback_query(query.id)
    


@bot.callback_query_handler(func=lambda query: query.data.startswith("select_day_"))
def select_day(query):
    user_id = str(query.from_user.id)
    print(f"Select_day called for user {user_id}, query.data: {query.data}")  # Отладка
    
    parts = query.data.split("_")
    print(f"Parts: {parts}")  # Отладка
    
    if len(parts) < 4:  # Проверяем, что есть хотя бы 4 части: select, day, task_index, YYYY-MM-DD
        bot.send_message(user_id, "Ошибка в формате данных бронирования.")
        bot.answer_callback_query(query.id)
        return
    
    task_index = int(parts[2])
    day_str = "-".join(parts[3:])  # Собираем дату обратно с дефисами
    
    print(f"Task index: {task_index}, Day: {day_str}")  # Отладка
    
    tasks = db.get_tasks_by_user_id(user_id=user_id)
    if task_index < 0 or task_index >= len(tasks):
        bot.send_message(query.from_user.id, "Задача не найдена.")
        bot.answer_callback_query(query.id)
        return
    
    task = tasks[task_index]
    lab_id = db.user_get_selected_lab_id(user_id)
    
    try:
        selected_date = datetime.strptime(day_str, "%Y-%m-%d")
    except ValueError as e:
        print(f"Error parsing date {day_str}: {e}")  # Отладка
        bot.send_message(query.from_user.id, "Ошибка в формате даты.")
        bot.answer_callback_query(query.id)
        return
    
    print(f"Calling find_available_slots for date {selected_date}")  # Отладка
    available_slots = db.find_available_slots(task, lab_id, selected_date)
    
    print(f"Available slots: {available_slots}")  # Отладка
    if not available_slots:
        bot.send_message(query.from_user.id, f"Нет доступных временных окон для задачи на {day_str} с 8:00 до 17:00.")
        bot.answer_callback_query(query.id)
        return
    
    buttons = {
        f"{slot[0].strftime('%H:%M')} - {slot[1].strftime('%H:%M')}": 
        {"callback_data": f"reserve_{task_index}_{slot[0].strftime('%Y%m%d%H%M')}_{slot[1].strftime('%Y%m%d%H%M')}"}
        for slot in available_slots
    }
    markup = telebot.util.quick_markup(buttons)
    bot.send_message(query.from_user.id, f"Задача: {task.name}\nВыберите время для выполнения на {day_str} (8:00–17:00):", reply_markup=markup)
    bot.answer_callback_query(query.id)

@bot.callback_query_handler(func=lambda query: query.data.startswith("reserve_"))
def reserve_task(query):
    user_id = str(query.from_user.id)
    parts = query.data.split("_")
    
    if len(parts) != 4:
        bot.send_message(query.from_user.id, "Ошибка в данных бронирования.")
        bot.answer_callback_query(query.id)
        return
    
    task_index = int(parts[1])
    start_time_str = parts[2]
    end_time_str = parts[3]
    
    try:
        start_time = datetime.strptime(start_time_str, "%Y%m%d%H%M")
        end_time = datetime.strptime(end_time_str, "%Y%m%d%H%M")
    except ValueError:
        bot.send_message(query.from_user.id, "Ошибка формата времени.")
        bot.answer_callback_query(query.id)
        return
    
    tasks = db.get_tasks_by_user_id(user_id=user_id)
    if task_index < 0 or task_index >= len(tasks):
        bot.send_message(query.from_user.id, "Задача не найдена.")
        bot.answer_callback_query(query.id)
        return
    
    task = tasks[task_index]
    lab_id = db.user_get_selected_lab_id(user_id)
    
    if db.reserve_task_equipment(user_id, task, lab_id, start_time, end_time):
        bot.send_message(query.from_user.id, f"Задача '{task.name}' успешно забронирована на {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}.")
    else:
        bot.send_message(query.from_user.id, "Ошибка при бронировании. Попробуйте другое время.")
    
    bot.answer_callback_query(query.id)

@bot.message_handler(commands=['start'], func=lambda message: True)
def process_invite(message):
    data = message.text[7:].split('_')
    print(data)
    if data[0] == 'lab':
        if int(data[1]) not in db.get_available_labs(data[2]):
            print(data[2])
            print(db.get_available_labs(data[2]))
            bot.send_message(message.from_user.id, "К сожалению, ссылка на доступ к лаборатории недействительна.")
        else:
            status = db.create_connection_user_to_lab(str(message.from_user.id), int(data[1]))
            bot.send_message(message.from_user.id, "Удачно добавлен")

@bot.callback_query_handler(func=lambda query: query.data == "create_lab"
                            and db.user_is_admin(str(query.from_user.id)))
def create_lab(query):
    bot.send_message(query.from_user.id, "Пожалуйста, введите название лаборатории <b>ответом</b> на сообщение <i>(макс.длина = 100симв.)</i>:")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите название лаборатории" in message.reply_to_message.text
                     and 8127922870 == message.reply_to_message.from_user.id
                     and db.user_is_admin(str(message.from_user.id)))
def apply_lab_name(message):
    if len(message.text) > 100:
        bot.send_message(message.from_user.id, f"Ошибка! {len(message.text)}/100 симв..\n"
                    f"Пожалуйста, введите название лаборатории <b>ответом</b> на сообщение:")
    else:
        user_id = str(message.from_user.id)
        status = db.create_lab(telebot.util.escape(message.text), user_id)
        if status != 'error':
            lab_id = status
            db.user_select_lab(user_id, lab_id)
            bot.send_message(message.from_user.id, f"Лаборатория создана успешно! Выбрана лаборатория [id{lab_id}] '{db.get_labname_by_id(lab_id)}'.")
            showMainMenu(message)
        else:
            bot.send_message(message.from_user.id, "Ошибка при создании лаборатории. Обратитесь к администратору системы или повторите попытку.")

@bot.message_handler(func=lambda message: db.user_is_admin(message.from_user.id) and 'admin' == message.text)
def admin_menu(message):
    lab_id = db.user_get_selected_lab_id(str(message.from_user.id))
    print(lab_id)
    markup = telebot.util.quick_markup({
        "Создать лабораторию": {"callback_data": f"create_lab"},
        "Добавить оборудование": {"callback_data": f"add_equipment?{lab_id}"},
        "Изменить оборудование": {"callback_data": f"edit_equipment?{lab_id}"},
        "Удалить оборудование": {"callback_data": f"delete_equipment?{lab_id}"},
        "Список оборудования": {"callback_data": f"equipment_list?{lab_id}"}
    })
    bot.send_message(message.from_user.id, f"Добро пожаловать в админ-панель, {message.from_user.full_name}!\n"
                                           f"Выбранная лаборатория: [id{lab_id}] <b>'{db.get_labname_by_id(lab_id)}'</b>\n"
                                           f"Пожалуйста, выберите действие:",
                     reply_markup=markup)

@bot.callback_query_handler(func=lambda query: "add_equipment" in query.data)
def add_equipment_to_lab(query):
    print(db.user_get_selected_lab_id(str(query.from_user.id)))
    print(db.is_user_admin_of_lab(query.from_user.id, int(query.data.split('?')[1])))
    lab_id = int(query.data.split('?')[1])
    bot.send_message(query.from_user.id, "Пожалуйста, <b>ответом</b> введите список оборудования в следующем формате: [<i>название кол-во</i>], пример:\n\n"
                                         f"Название 12\nНазвание_2 8\nНазвание_3 1\n...{lab_id}")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите список оборудования в следующем формате" in message.reply_to_message.text
                     and 8127922870 == message.reply_to_message.from_user.id
                     and db.user_is_admin(str(message.from_user.id)))
def add_equipment_list(message):
    user_id = str(message.from_user.id)
    lab_id = db.user_get_selected_lab_id(user_id)
    
    if not lab_id:
        bot.send_message(user_id, "Ошибка: Сначала выберите лабораторию.")
        return
    
    if not db.is_user_admin_of_lab(user_id, lab_id):
        bot.send_message(user_id, "У вас нет прав для добавления оборудования в эту лабораторию.")
        return
    
    lines = message.text.split('\n')
    errors = []
    for line in lines:
        if len(line.split(' ')) != 2:
            errors.append(line)
            continue
        try:
            count = int(line.split(' ')[1])
            if count <= 0:
                errors.append(f"{line} (количество должно быть положительным)")
                continue
        except ValueError:
            errors.append(line)
            continue
        for i in range(count):
            status = db.add_equipment(telebot.util.escape(line.split(' ')[0]), True, lab_id)
            if status == 'error':
                errors.append(line)
                continue
    bot.send_message(message.from_user.id, f"Операция выполнена. Количество ошибок при выполнении: <b>{len(errors)}</b>:\n"
                                           f"{'\n'.join(errors) if errors else 'Нет ошибок'}")
    
@bot.callback_query_handler(func=lambda query: query.data.startswith("equipment_list"))
def equipment_list(query):
    user_id = str(query.from_user.id)
    lab_id = int(query.data.split('?')[1])
    
    if not db.is_user_admin_of_lab(user_id, lab_id):
        bot.send_message(query.from_user.id, "У вас нет прав для просмотра оборудования этой лаборатории.")
        bot.answer_callback_query(query.id)
        return
    
    equipment_summary = db.get_equipment_summary_by_lab(lab_id)
    
    if not equipment_summary:
        bot.send_message(query.from_user.id, "В лаборатории [id{}] нет активного оборудования.".format(lab_id))
    else:
        response = f"Список оборудования в лаборатории [id{lab_id}] '{db.get_labname_by_id(lab_id)}':\n\n"
        for name, count in equipment_summary.items():
            response += f"{name}: {count}\n"
        buttons = {
            "Удалить оборудование": {"callback_data": f"remove_equipment?{lab_id}"}
        }
        markup = telebot.util.quick_markup(buttons)
        bot.send_message(query.from_user.id, response, reply_markup=markup)
    
    bot.answer_callback_query(query.id)

@bot.callback_query_handler(func=lambda query: query.data.startswith("my_tasks"))
def my_tasks(query):
    user_id = str(query.from_user.id)
    lab_id = int(query.data.split('?')[1])
    reserved_steps = db.get_user_reservations(user_id)

    if not reserved_steps:
        bot.send_message(query.from_user.id, "У вас нет забронированных шагов.")
    else:
        # Группируем шаги по времени и оборудованию
        time_equipment_groups = {}
        for step in reserved_steps:
            key = (step["start_time"], step["end_time"], step["equipment"])
            if key not in time_equipment_groups:
                time_equipment_groups[key] = []
            time_equipment_groups[key].append(step)

        # Группируем шаги по task_id
        tasks_dict = {}
        for key, steps in time_equipment_groups.items():
            # Берем первый шаг из группы (остальные дублируются)
            step = steps[0]
            task_id = step["task_id"]
            if task_id not in tasks_dict:
                task = next((t for t in db.get_tasks_by_user_id(user_id) if t.task_id == task_id), None)
                if task:
                    tasks_dict[task_id] = {"name": task.name, "steps": []}
            if task_id in tasks_dict:
                # Добавляем шаг с информацией о количестве повторений
                step_with_count = step.copy()
                step_with_count["repeat_count"] = len(steps)
                tasks_dict[task_id]["steps"].append(step_with_count)

        if not tasks_dict:
            bot.send_message(query.from_user.id, "У вас нет активных бронирований для задач.")
        else:
            now = datetime.now(tz=tz).replace(tzinfo=None)
            response = "<b>Ваши забронированные задачи (в порядке выполнения):</b>\n\n"

            for task_id, task_info in tasks_dict.items():
                response += f"Задача {task_info['name']} (id{task_id}):\nШаги:\n"
                for step in task_info["steps"]:
                    start_str = step["start_time"].strftime('%H:%M')
                    end_str = step["end_time"].strftime('%H:%M')
                    time_to_start = (step["start_time"] - now).total_seconds() / 60
                    time_to_end = (step["end_time"] - now).total_seconds() / 60
                    if time_to_start > 0:
                        time_str = f"{int(time_to_start)} мин до начала"
                    elif time_to_end > 0:
                        time_str = "уже началось"
                    else:
                        time_str = "закончилось"

                    # Добавляем информацию о количестве повторений
                    repeat_info = f" ({step['repeat_count']}x)" if step['repeat_count'] > 1 else ""
                    response += f"{step['step_name']} ({step['equipment']}): {start_str} – {end_str} ({time_str}){repeat_info}\n"
                response += "\n"

            # Создаем кнопки для отмены задач
            buttons = {
                f"Отменить задачу {task_info['name']} (id{task_id})": {"callback_data": f"cancel_task_{task_id}"}
                for task_id, task_info in tasks_dict.items()
            }
            markup = telebot.util.quick_markup(buttons)

            bot.send_message(query.from_user.id, response.rstrip(), reply_markup=markup, parse_mode="HTML")

    bot.answer_callback_query(query.id)

@bot.callback_query_handler(func=lambda query: query.data.startswith("cancel_task_"))
def cancel_task(query):
    user_id = str(query.from_user.id)
    task_id = int(query.data.split("_")[2])
    
    if db.delete_reservations_by_task(user_id, task_id):
        task = next((t for t in db.get_tasks_by_user_id(user_id) if t.task_id == task_id), None)
        bot.send_message(query.from_user.id, f"Брони для задачи '{task.name}' (id{task_id}) успешно отменены.")
    else:
        bot.send_message(query.from_user.id, "Ошибка при отмене брони или задача не найдена.")
    
    bot.answer_callback_query(query.id)

def check_reservations():
    """Проверяет время до начала шагов и отправляет уведомления за 3 минуты."""
    while True:
        now = datetime.now(tz=tz).replace(tzinfo=None)
        for user_id in db.get_all_users():
            reserved_steps = db.get_user_reservations(user_id)
            for step in reserved_steps:
                time_to_start = (step["start_time"] - now).total_seconds() / 60
                if 3 <= time_to_start <= 4:
                    bot.send_message(user_id, f"Напоминание: Шаг '{step['step_name']}' ({step['equipment']}) начнётся через 3 минуты в {step['start_time'].strftime('%H:%M')}!")
        time.sleep(59)

@bot.callback_query_handler(func=lambda query: query.data.startswith("remove_equipment"))
def remove_equipment(query):
    user_id = str(query.from_user.id)
    lab_id = int(query.data.split('?')[1])
    
    if not db.is_user_admin_of_lab(user_id, lab_id):
        bot.send_message(query.from_user.id, "У вас нет прав для удаления оборудования из этой лаборатории.")
        bot.answer_callback_query(query.id)
        return
    
    bot.send_message(query.from_user.id, f"Пожалуйста, <b>ответом</b> введите список оборудования для удаления из лаборатории [id{lab_id}] в формате: [<i>название кол-во</i>], пример:\n\n"
                                         f"Микроскоп 2\nЦентрифуга 1\n...")
    bot.answer_callback_query(query.id)



@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите список оборудования для удаления" in message.reply_to_message.text
                     and 8127922870 == message.reply_to_message.from_user.id
                     and db.user_is_admin(str(message.from_user.id)))
def remove_equipment_list(message):
    user_id = str(message.from_user.id)
    lab_id = db.user_get_selected_lab_id(user_id)
    
    if not lab_id:
        bot.send_message(user_id, "Ошибка: Сначала выберите лабораторию.")
        return
    
    if not db.is_user_admin_of_lab(user_id, lab_id):
        bot.send_message(user_id, "У вас нет прав для удаления оборудования из этой лаборатории.")
        return

    lines = message.text.split('\n')
    errors = db.remove_equipments(lab_id, lines)
    
    bot.send_message(message.from_user.id, f"Операция выполнена. Количество ошибок: <b>{len(errors)}</b>:\n"
                                          f"{'\n'.join(errors) if errors else 'Нет ошибок'}")


tz = timezone(timedelta(hours=10))

notification_thread = threading.Thread(target=check_reservations, daemon=True)
notification_thread.start()

db.init_db()
db.user_set_admin("1007994831", True)
bot.set_my_commands([BotCommand('main_menu', "Показать доступные вам лаборатории")])
print('Bot initialized')
bot.infinity_polling()