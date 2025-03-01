import telebot
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

    db.add_user(str(message.from_user.id))
    
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

@bot.message_handler(commands=['start', 'menu'])
def showMainMenu(message):
    available_labs = db.get_available_labs(str(message.from_user.id))

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)

    btn_add_lab = types.KeyboardButton('➕ Создать лабораторию')
    markup.add(btn_add_lab)

    if available_labs:
        lab_buttons = []
        for lab_id, lab_name, is_admin in available_labs:

            prefix = "👑 " if is_admin else "🔬 "
            lab_buttons.append(types.KeyboardButton(f"{prefix}{lab_name}"))
        
        markup.add(*lab_buttons)
        
        bot.send_message(message.from_user.id, 
                       "Выберите лабораторию или создайте новую:", 
                       reply_markup=markup)
    else:

        bot.send_message(message.from_user.id, 
                       "У вас пока нет доступных лабораторий. Создайте свою первую лабораторию:", 
                       reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '➕ Создать лабораторию')
def add_laboratory(message):
    msg = bot.send_message(message.from_user.id, 
                         "Введите название для новой лаборатории:")
    bot.register_next_step_handler(msg, process_lab_name)

def process_lab_name(message):
    lab_name = message.text

    if db.create_lab(lab_name, str(message.from_user.id)):
        bot.send_message(message.from_user.id, 
                       f"Лаборатория '{lab_name}' успешно создана!")
    else:
        bot.send_message(message.from_user.id, 
                       "Не удалось создать лабораторию. Попробуйте позже.")

    showMainMenu(message)

@bot.message_handler(func=lambda message: message.text and (message.text.startswith('👑 ') or message.text.startswith('🔬 ')))
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
    )

db.init_db()
print('Bot initialized')
bot.infinity_polling()