import telebot, sqlite3

with open("bot_token.txt", "r") as file:
    token = file.read()

bot = telebot.TeleBot(token, parse_mode="HTML")

# TODO: add logic1
def isFirstMessage(message):
    return True

# TODO: add user to db
@bot.message_handler(func=lambda message: isFirstMessage(message) == True)
def firstMessageHandler(message):
    with open("greeting_text.txt", 'r') as text:
        bot.send_message(message.from_user.id, text.read())

print('initialized')
bot.infinity_polling()