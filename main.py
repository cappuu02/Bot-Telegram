import telebot
import sqlite3
#import string
#import random
from bs4 import BeautifulSoup
import requests

# Inserisci qui il token del tuo bot ottenuto da BotFather
TOKEN = "5906905240:AAGSH8itptIwVd4NgAiQuMa-lDic2ZRE2kM"

bot = telebot.TeleBot(TOKEN)

# Funzione per generare numeri casuali composti da 6 cifre
#def generate_random_number():
#   return ''.join(random.choices(string.digits, k=6))

# CREAZIONE DATABASE
connection = sqlite3.connect('database_tg.db', check_same_thread=False)
cursor = connection.cursor()

# Genera 300000 numeri casuali
#matricole = [generate_random_number() for _ in range(300000)]

# Salva le matricole nel database come una lista di valori separati da virgola
#cursor.execute("CREATE TABLE IF NOT EXISTS freshman (matricole TEXT)")
#cursor.execute("INSERT INTO Freshman VALUES (342244)")
#cursor.execute("INSERT INTO Freshman VALUES (347711)")
#cursor.execute("INSERT INTO freshman (matricole) VALUES (?)", (",".join(matricole),))
connection.commit()




@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, f"👋 Benvenuto in ExamBot {message.from_user.first_name}!\n Per iniziare, inserisci la tua matricola:")

    bot.register_next_step_handler(message, check_matricola)

def check_matricola(message):
        matricola_numero = message.text

        if matricola_numero == "/start": handle_start(message)

        if (not matricola_numero.isdigit() or len(matricola_numero) != 6) and (matricola_numero != "/start"):
            bot.reply_to(message, "⚠️ La matricola deve essere composta da 6 cifre numeriche."
                                  "\nInserisci nuovamente la matricola o usa /start per riavviare il processo:")
            bot.register_next_step_handler(message, check_matricola)
            return

        cursor.execute("SELECT matricole FROM freshman")
        matricole_db = cursor.fetchone()[0].split(",")

        if matricola_numero in matricole_db:
            bot.reply_to(message, f"✅ La matricola è corretta {message.from_user.first_name}!")
            bot.send_message(message.chat.id, "Ora puoi utilizzare i seguenti comandi:")
            bot.send_message(message.chat.id, "/start - Per reinserire la matricola")
            bot.send_message(message.chat.id, "/lista_esami - Per vedere lista degli esami prenotabili")
            bot.send_message(message.chat.id, "/prenotazione_esami - Per prenotare esami")
        if (matricola_numero not in matricole_db) and (matricola_numero != "/start"):
            bot.reply_to(message,
                         "❌ La matricola è incorretta."
                         "\nInserisci nuovamente la matricola o usa /start per riavviare il processo:")
            bot.register_next_step_handler(message, check_matricola)



@bot.message_handler(commands=['lista_esami'])
def handle_table(message):

    # Effettua una richiesta GET alla pagina web
    url = "https://servizi.dmi.unipg.it/mrbs/day.php?year=2023&month=05&day=17&area=1&room=3"  # Inserisci l'URL del sito web contenente la tabella
    response = requests.get(url)

    # Verifica lo stato della risposta
    if response.status_code == 200:
        # Parsing del contenuto HTML della pagina
        soup = BeautifulSoup(response.text, "html.parser")

        # Trova la tabella desiderata utilizzando un selettore CSS o un'etichetta specifica
        table = soup.find("table", class_="dwm_main")

        # Estrai le righe della tabella
        rows = table.find_all("tr")

        # Lista per raggruppare i valori della matrice
        values = []

        # Estrai e raggruppa i valori delle righe
        for row in rows:
            # Estrai le colonne della riga
            columns = row.find_all("td")

            # Estrai il valore di ogni colonna e aggiungilo alla lista values
            for column in columns:
                value = column.get_text(strip=True)
                if value:
                    values.append(value)

        # Stampa i valori raggruppati come stringa
        bot.reply_to(message, "\n".join(values))
        bot.reply_to(message, f"✅ Lista stampata correttamente!")
        bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
        bot.send_message(message.chat.id, "/start - Per reinserire la matricola")
        bot.send_message(message.chat.id, "/lista_esami - Per rivedere lista degli esami prenotabili")
        bot.send_message(message.chat.id, "/prenotazione_esami - Per prenotare esami")
    else:
         print(message, "Errore nella richiesta HTTP:", response.status_code)


# Avvia il bot
bot.polling()
