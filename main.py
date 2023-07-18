import telebot
import sqlite3

# Inserisci qui il token del tuo bot ottenuto da BotFather
TOKEN = "5906905240:AAGSH8itptIwVd4NgAiQuMa-lDic2ZRE2kM"


bot = telebot.TeleBot(TOKEN)

#CREAZIONE DATABASE
connection = sqlite3.connect('database_tg.db' ,check_same_thread=False)
print(connection.total_changes)
cursor = connection.cursor()
#cursor.execute("CREATE TABLE freshman (name TEXT, surname TEXT, matricola )")
cursor.execute("INSERT INTO freshman VALUES ('Luca', 'Capuccini', 347711)")
cursor.execute("INSERT INTO freshman VALUES ('Chiara', 'Lombardo', 330350)")
cursor.execute("INSERT INTO freshman VALUES ('Edoardo', 'Tommasi', 342244)")
cursor.execute("INSERT INTO freshman VALUES ('Eduard', 'Brahas', 342600)")
cursor.execute("INSERT INTO freshman VALUES ('Daniel', 'Chionne', 344785)")


@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, 'inserisci la matricola:')


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    matricola_numero = int(message.text)
    bot.reply_to(message, f"La tua matricola è {matricola_numero}.")
    query = f"SELECT matricola FROM freshman WHERE matricola = {matricola_numero}"
    cursor.execute(query)
    risultato = cursor.fetchone
    connection.commit()

    if risultato:
        print("Il valore è presente nel database DIO CANE.")
    else:
        print("Il valore non è presente nel database.")


bot.polling()

