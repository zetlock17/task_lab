from types import NoneType
import telebot, json
from telebot import types
import db
import os
from dotenv import load_dotenv

load_dotenv()

# Класс Task
class Task:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.stages = []

token = os.environ.get('TELEGRAM_BOT_TOKEN')

if not token:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
    exit(1)

bot = telebot.TeleBot(token, parse_mode="HTML")

# Временное хранилище задач и шагов
user_tasks = {}  # {user_id: Task}
user_steps = {}  # {user_id: [{"name": str, "equipment": str, "timing": list}, ...]}

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
        "Создать задачу": {"callback_data": "create_task"}
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
                                         f"<code>t.me/task_lab_bot?start=lab_{lab_id}_{query.from_user.id}</code>\n"
                                         f"<i> (нажмите, чтобы скопировать) </i>")

@bot.callback_query_handler(func=lambda query: query.data == "create_task")
def create_task(query):
    user_id = str(query.from_user.id)
    user_tasks[user_id] = None  # Инициализируем задачу как None
    bot.send_message(query.from_user.id, "Пожалуйста, введите название и описание <b>ответом</b> на сообщение в следующем формате:\nНазвание...\nОписание...")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите название и описание" in message.reply_to_message.text
                     and 8076896158 == message.reply_to_message.from_user.id)
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
    
    # Создаём объект Task и сохраняем его
    user_tasks[user_id] = Task(title, description)
    markup = telebot.util.quick_markup({"Добавить шаги": {"callback_data": "хз"}})
    bot.send_message(message.from_user.id, f"Название и описание сохранены в задачу '{title}'. Теперь введите шаги.", reply_markup=markup)

@bot.callback_query_handler(func=lambda query: query.data == "хз")
def add_step(query):
    user_id = str(query.from_user.id)
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
                     and 8076896158 == message.reply_to_message.from_user.id)
def apply_step_data(message):
    user_id = str(message.from_user.id)
    lines = message.text.split("\n")

    # Проверяем, что введено 5 строк
    if len(lines) != 5:
        bot.send_message(message.from_user.id, "Ошибка: Нужно ввести 5 строк (Название, Прибор, Активное время, Время ожидания, Время обработки).")
        add_step_helper(user_id)
        return
    
    name, equipment, active_time_str, passive_time_str, processing_time_str = lines

    if len(name) > 100:
        bot.send_message(message.from_user.id, f"Ошибка: Название слишком длинное ({len(name)}/100 символов).")
        add_step_helper(user_id)
        return
    
    # Извлечение активного времени
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

    # Извлечение времени ожидания
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

    # Извлечение времени обработки
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

    # Формируем список timing в формате [Xa, Yp, Za]
    timing = [f"{active_time}a", f"{passive_time}p", f"{processing_time}a"]
    step = {"name": name, "equipment": equipment, "timing": timing}
    user_steps[user_id].append(step)
    
    markup = telebot.util.quick_markup({
        "Добавить ещё шаг": {"callback_data": "add_another_step"},
        "Завершить": {"callback_data": "finish_steps"}
    })
    bot.send_message(message.from_user.id, f"Шаг '{name}' успешно добавлен. Что дальше?", reply_markup=markup)

    print(user_steps)

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
    if not user_steps.get(user_id):
        bot.send_message(user_id, "Вы не добавили ни одного шага.")
        return
    
    # Показываем шаги пользователю с номерами
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
                     and 8076896158 == message.reply_to_message.from_user.id)
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

    total_steps = len(user_steps[user_id])
    
    if len(all_indices) != total_steps or max(all_indices, default=-1) >= total_steps or min(all_indices, default=0) < 0:
        bot.send_message(user_id, "Ошибка: Указаны неверные, пропущенные или повторяющиеся номера шагов.")
        return

    task = user_tasks[user_id]
    task.stages = [[user_steps[user_id][i] for i in branch] for branch in branches]

    # Сохраняем задачу в БД 
    
    template_id = db.add_template(task.name, task.description, task.stages)
    db.assing_task_to_user(templates_id=template_id, user_id=user_id)


    print(user_tasks[user_id].stages)

    del user_steps[user_id]
    del user_tasks[user_id]

    confirmation = f"Задача '{task.name}' успешно сохранена со стадиями:\n"
    for i, branch in enumerate(branches, 1):
        branch_str = " ".join(str(idx + 1) for idx in branch)
        confirmation += f"Ветка {i}: {branch_str}\n"
    
    bot.send_message(user_id, confirmation)
    showMainMenu(message)

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



'''@bot.message_handler(func=lambda message: message.text and (message.text.startswith('👑 ') or message.text.startswith('🔬 ')))
def select_lab(message):
    lab_name = message.text[2:]  

    available_labs = db.get_available_labs(str(message.from_user.id))
    selected_lab = None

    for lab_id, name, is_admin in available_labs:
        if name == lab_name:
            selected_lab = (lab_id, name, is_admin)
            break

    if not selected_lab:
        bot.send_message(message.from_user.id, "Лаборатория не найдена. Попробуйте снова.")
        showMainMenu(message)
        return

    lab_id, lab_name, is_admin = selected_lab

    markup = types.InlineKeyboardMarkup(row_width=2)

    btn_equipment = types.InlineKeyboardButton("🔧 Оборудование", callback_data=f"lab_equip_{lab_id}")
    btn_tasks = types.InlineKeyboardButton("📋 Задачи", callback_data=f"lab_tasks_{lab_id}")

    if is_admin:
        btn_members = types.InlineKeyboardButton("👥 Участники", callback_data=f"lab_members_{lab_id}")
        btn_delete = types.InlineKeyboardButton("❌ Удалить", callback_data=f"lab_delete_{lab_id}")
        markup.add(btn_equipment, btn_tasks, btn_members, btn_delete)
    else:
        markup.add(btn_equipment, btn_tasks)

    bot.send_message(
        message.from_user.id,
        f"<b>Лаборатория: {lab_name}</b>\n\nВыберите действие:",
        reply_markup=markup,
        parse_mode="HTML"
    )'''

@bot.callback_query_handler(func=lambda query: query.data == "create_lab"
                            and db.user_is_admin(str(query.from_user.id)))
def create_lab(query):
    bot.send_message(query.from_user.id, "Пожалуйста, введите название лаборатории <b>ответом</b> на сообщение <i>(макс.длина = 100симв.)</i>:")
    bot.answer_callback_query(query.id)
@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите название лаборатории" in message.reply_to_message.text
                     and 8076896158 == message.reply_to_message.from_user.id
                     and db.user_is_admin(str(message.from_user.id)))
def apply_lab_name(message):
    if len(message.text) > 100:
        bot.send_message(message.from_user.id, f"Ошибка! {len(message.text)}/100 симв..\n"
                    f"Пожалуйста, введите название лаборатории <b>ответом</b> на сообщение:")
    else:
        status = db.create_lab(telebot.util.escape(message.text), str(message.from_user.id))
        bot.send_message(message.from_user.id, f"Статус операции: <b>{"Успешно!" if status != 'error' else "Ошибка. Обратитесь к администратору системы или повторите попытку снова.."}</b>")

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
    print(db.is_user_admin_of_lab(query.from_user.id,int(query.data.split('?')[1])))
    lab_id = int(query.data.split('?')[1])
    bot.send_message(query.from_user.id, "Пожалуйста, <b>ответом</b> введите список оборудования в следующем формате: [<i>название кол-во</i>], пример:\n\n"
                                         f"Название 12\nНазвание_2 8\nНазвание_3 1\n...{lab_id}")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите список оборудования" in message.reply_to_message.text
                     and 8076896158 == message.reply_to_message.from_user.id
                     and db.user_is_admin(str(message.from_user.id))
                     and db.is_user_admin_of_lab(str(message.from_user.id) ,int(message.reply_to_message.text[message.reply_to_message.text.rfind(".")+1:])))
def add_equipment_list(message):
    lab_id = int(message.reply_to_message.text[message.reply_to_message.text.rfind(".")+1:])
    lines = message.text.split('\n')
    errors = []
    for line in lines:
        if len(line.split(' ')) != 2:
            errors.append(line)
            continue

        try:
            count = int(line.split(' ')[1])
        except:
            errors.append(line)
            continue

        for i in range(count):
            status = db.add_equipment(telebot.util.escape(line.split(' ')[0]), True, lab_id)
            if status == 'error':
                errors.append(line)
                continue

    bot.send_message(message.from_user.id, f"Операция выполнена. Количество ошибок при выполнении: <b>{len(errors)}</b>:\n"
                                           f"{'\n'.join(errors)}\n")

'''@bot.message_handler(func=lambda message: message.text and (message.text.startswith('👑 ') or message.text.startswith('🔬 ')))
def select_lab(message):
    lab_name = message.text[2:]  

    available_labs = db.get_available_labs(str(message.from_user.id))
    selected_lab = None

    for lab_id, name, is_admin in available_labs:
        if name == lab_name:
            selected_lab = (lab_id, name, is_admin)
            break

    if not selected_lab:
        bot.send_message(message.from_user.id, "Лаборатория не найдена. Попробуйте снова.")
        showMainMenu(message)
        return

    lab_id, lab_name, is_admin = selected_lab

    markup = types.InlineKeyboardMarkup(row_width=2)

    btn_equipment = types.InlineKeyboardButton("🔧 Оборудование", callback_data=f"lab_equip_{lab_id}")
    btn_tasks = types.InlineKeyboardButton("📋 Задачи", callback_data=f"lab_tasks_{lab_id}")

    if is_admin:
        btn_members = types.InlineKeyboardButton("👥 Участники", callback_data=f"lab_members_{lab_id}")
        btn_delete = types.InlineKeyboardButton("❌ Удалить", callback_data=f"lab_delete_{lab_id}")
        markup.add(btn_equipment, btn_tasks, btn_members, btn_delete)
    else:
        markup.add(btn_equipment, btn_tasks)

    bot.send_message(
        message.from_user.id,
        f"<b>Лаборатория: {lab_name}</b>\n\nВыберите действие:",
        reply_markup=markup,
        parse_mode="HTML"
    )'''

@bot.callback_query_handler(func=lambda query: query.data == "create_lab"
                            and db.user_is_admin(str(query.from_user.id)))
def create_lab(query):
    bot.send_message(query.from_user.id, "Пожалуйста, введите название лаборатории <b>ответом</b> на сообщение <i>(макс.длина = 100симв.)</i>:")
    bot.answer_callback_query(query.id)
@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите название лаборатории" in message.reply_to_message.text
                     and 8076896158 == message.reply_to_message.from_user.id
                     and db.user_is_admin(str(message.from_user.id)))
def apply_lab_name(message):
    if len(message.text) > 100:
        bot.send_message(message.from_user.id, f"Ошибка! {len(message.text)}/100 симв..\n"
                    f"Пожалуйста, введите название лаборатории <b>ответом</b> на сообщение:")
    else:
        status = db.create_lab(telebot.util.escape(message.text), str(message.from_user.id))
        bot.send_message(message.from_user.id, f"Статус операции: <b>{"Успешно!" if status != 'error' else "Ошибка. Обратитесь к администратору системы или повторите попытку снова.."}</b>")

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
    print(db.is_user_admin_of_lab(query.from_user.id,int(query.data.split('?')[1])))
    lab_id = int(query.data.split('?')[1])
    bot.send_message(query.from_user.id, "Пожалуйста, <b>ответом</b> введите список оборудования в следующем формате: [<i>название кол-во</i>], пример:\n\n"
                                         f"Название 12\nНазвание_2 8\nНазвание_3 1\n...{lab_id}")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите список оборудования" in message.reply_to_message.text
                     and 8076896158 == message.reply_to_message.from_user.id
                     and db.user_is_admin(str(message.from_user.id))
                     and db.is_user_admin_of_lab(str(message.from_user.id) ,int(message.reply_to_message.text[message.reply_to_message.text.rfind(".")+1:])))
def add_equipment_list(message):
    lab_id = int(message.reply_to_message.text[message.reply_to_message.text.rfind(".")+1:])
    lines = message.text.split('\n')
    errors = []
    for line in lines:
        if len(line.split(' ')) != 2:
            errors.append(line)
            continue

        try:
            count = int(line.split(' ')[1])
        except:
            errors.append(line)
            continue

        for i in range(count):
            status = db.add_equipment(telebot.util.escape(line.split(' ')[0]), True, lab_id)
            if status == 'error':
                errors.append(line)
                continue

    bot.send_message(message.from_user.id, f"Операция выполнена. Количество ошибок при выполнении: <b>{len(errors)}</b>:\n"
                                           f"{'\n'.join(errors)}\n")




db.user_set_admin("877702484", True)
db.init_db()
print('Bot initialized')
bot.infinity_polling()