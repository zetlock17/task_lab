from types import NoneType
import telebot, json
from telebot import types
import db
import os
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get('TELEGRAM_BOT_TOKEN')

if not token:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
    exit(1)

bot = telebot.TeleBot(token, parse_mode="HTML")


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
    #db.user_select_lab(str(message.from_user.id), None)
    if available_labs:
        lab_buttons = {}
        for lab_id in available_labs:

            prefix = "👑 " if db.is_user_admin_of_lab(str(message.from_user.id), lab_id) else "🔬 "
            lab_buttons[f'{prefix}[id{lab_id}] {db.get_labname_by_id(lab_id)}'] = {"callback_data": f"lab_menu?{lab_id}"}

        markup = telebot.util.quick_markup(lab_buttons)

        bot.send_message(message.from_user.id, 
                       "Список доступных вам лабораторий. Выберите подходящую:",
                       reply_markup=markup)
    else:

        bot.send_message(message.from_user.id, 
                       "К сожалению, у вас пока нет доступных лабораторий. Получите ссылку-приглашение от администратора или участника!")

@bot.callback_query_handler(func=lambda query: "lab_menu" in query.data
                            and int(query.data.split('?')[1]) in db.get_available_labs(str(query.from_user.id)))
def lab_menu(query):
    lab_id = query.data.split('?')[1]
    markup = telebot.util.quick_markup({
        "Ссылка - приглашение": {"callback_data":f"link_to?{lab_id}"},
        "Создать задачу": {"callback_data": "create_task"}
    })
    #db.user_select_lab(str(query.from_user.id), lab_id)
    bot.send_message(query.from_user.id, f"Вы в меню лаборатории [id{lab_id}] <b>'{db.get_labname_by_id(lab_id)}'</b>. Что вы хотите сделать?",
                     reply_markup=markup)
    bot.answer_callback_query(query.id)

@bot.callback_query_handler(func=lambda query: "link_to" in query.data
                            and int(query.data.split('?')[1]) in db.get_available_labs(str(query.from_user.id)))
def get_link_to_lab(query):
    lab_id = query.data.split('?')[1]
    bot.send_message(query.from_user.id, "Ссылка на присоединение к текущей лаборатории:\n"
                                         f"<code>t.me/task_lab_bot?start=lab_{lab_id}_{query.from_user.id}</code>\n"
                                         f"<i> (нажмите, что бы скопировать) </i>")

@bot.callback_query_handler(func=lambda query: query.data == "create_task")
def create_task(query):
    bot.send_message(query.from_user.id, "Пожалуйста, введите название и описание <b>ответом</b> на сообщение в следующем формате:\nНазвание\nОписаниеОписаниеОписание...")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите название и описание" in message.reply_to_message.text
                     and 8076896158 == message.reply_to_message.from_user.id)
                     
def apply_task_name_and_description(message):
    def msg():
        bot.send_message(message.from_user.id,
        "Пожалуйста, введите название и описание <b>ответом</b> на сообщение в следующем формате:\nНазвание\nОписаниеОписаниеОписание...")
    lines = message.text.split("\n")

    title = lines[0]
    title_length = len(title)

    description = lines[1]
    description_length = len(description)

    if len(lines) < 2:
        bot.send_message(message.from_user.id, "Ошибка: Отсутсвует название или описание\n")
        msg()
    elif title_length > 100:
        bot.send_message(message.from_user.id, f"Ошибка! название {title_length}/100 симв..\n")
        msg()
    elif description_length > 1500:
        bot.send_message(message.from_user.id, f"Ошибка! описание {description_length}/1500 симв..\n")
        msg()
    else:
        markup = telebot.util.quick_markup({
        "Добавить шаги": {"callback_data":{"title": title, "description": description}},
        "Завершить создание": {"callback_data": "create_task"}
        })
        bot.send_message(message.from_user.id, f"Название и описание сохранены, туперь введите шаги", reply_markup=markup)
        

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
                                           f"Выбранная лаборатория: {db.get_labname_by_id(lab_id)}\n"
                                           f"Пожалуйста, выберите действие:",
                     reply_markup=markup)

@bot.callback_query_handler(func=lambda query: "add_equipment" in query.data
                            and db.is_user_admin_of_lab(query.from_user.id,int(query.data.split('?')[1]))
                            and db.user_get_selected_lab_id(str(query.from_user.id)) is not None)
def add_equipment_to_lab(query):
    lab_id = int(query.data.split('?')[1])
    bot.send_message(query.from_user.id, "Пожалуйста, <b>ответом</b> введите список оборудования в следующем формате: <i>название кол-во</i>, пример:\n\n"
                                         f"Название 12\nНазвание_2 8\nНазвание_3 1\n...{lab_id}")
    bot.answer_callback_query(query.id)

@bot.message_handler(func=lambda message: type(message.reply_to_message) != NoneType
                     and "введите список оборудования" in message.reply_to_message.text
                     and 8076896158 == message.reply_to_message.from_user.id
                     and db.user_is_admin(str(message.from_user.id))
                     and db.is_user_admin_of_lab(message.from_user.id ,int(message.reply_to_message.text[message.reply_to_message.text.rfind(".")+1:])))
def add_equipment_list(message):
    print(message.text.split('\n'))

db.user_set_admin("877702484", True)
db.init_db()
print('Bot initialized')
bot.infinity_polling()