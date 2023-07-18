import telebot
import sqlite3
import string
import random

# Inserisci qui il token del tuo bot ottenuto da BotFather
TOKEN = "5906905240:AAGSH8itptIwVd4NgAiQuMa-lDic2ZRE2kM"

bot = telebot.TeleBot(TOKEN)

# Funzione per generare numeri casuali composti da 6 cifre
def generate_random_number():
    return ''.join(random.choices(string.digits, k=6))

#CREAZIONE DATABASE
connection = sqlite3.connect('database_tg.db' ,check_same_thread=False)
cursor = connection.cursor()

# Genera 300000 numeri casuali
matricole = [generate_random_number() for _ in range(300000)]

# Salva le matricole nel database come una lista di valori separati da virgola
cursor.execute("CREATE TABLE IF NOT EXISTS freshman (matricole TEXT)")
cursor.execute("INSERT INTO freshman (matricole) VALUES (?)", (",".join(matricole),))
connection.commit()

def check_matricola(message):
    matricola_numero = message.text

    if not matricola_numero.isdigit() or len(matricola_numero) != 6:
        bot.reply_to(message, "⚠️ La matricola deve essere composta da 6 cifre numeriche. \nInserisci nuovamente la matricola:")
        bot.register_next_step_handler(message, check_matricola)
        return

    cursor.execute("SELECT matricole FROM freshman")
    matricole = cursor.fetchone()[0].split(",")

    if matricola_numero in matricole:
        bot.reply_to(message, f"✅ La matricola è corretta {message.from_user.first_name}!")
        bot.send_message(message.chat.id, "Ora puoi utilizzare i seguenti comandi:")
        bot.send_message(message.chat.id, "/start - Per reinserire la matricola")
        bot.send_message(message.chat.id, "/lista_esami - Per vedere lista degli esami prenotabili")
        bot.send_message(message.chat.id, "/prenotazione_esami - Per prenotare esami")
    else:
        bot.reply_to(message, "❌ La matricola è incorretta. \nInserisci nuovamente la matricola:")
        bot.register_next_step_handler(message, check_matricola)

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, f"👋 Benvenuto in ExamBot {message.from_user.first_name}!\n Per iniziare, inserisci la tua matricola:")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Avvia la funzione di controllo della matricola
    check_matricola(message)


bot.polling()
