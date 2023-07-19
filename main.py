import telebot
import sqlite3
from bs4 import BeautifulSoup
import requests

TOKEN = "5906905240:AAGSH8itptIwVd4NgAiQuMa-lDic2ZRE2kM"  # Inserisci qui il token del tuo bot ottenuto da BotFather

bot = telebot.TeleBot(TOKEN)

connection = sqlite3.connect('database_tg.db', check_same_thread=False)
cursor = connection.cursor()

url = "https://servizi.dmi.unipg.it/mrbs/day.php?year=2023&month=05&day=17&area=1&room=3"
response = requests.get(url)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")
    div = soup.find("div", id="dwm").get_text(strip=True)
    table = soup.find("table", class_="dwm_main")
    rows = table.find_all("tr")

    header_row = rows[0]
    headers = []
    for header in header_row.find_all("th"):
        header_text = header.get_text(strip=True)
        headers.append(header_text)

    values = []
    for row in rows[1:]:
        row_values = [value.get_text(strip=True) for value in row.find_all("td")]
        if any(row_values):
            values.append(row_values)

    values = [row for row in values if any(row[1:])]

    table_string = f"📅 Data: {div}\n\n"
    for row in values:
        row_string = "\n".join([f"🔹 {header}: {value}" for header, value in zip(headers, row)])
        table_string += f"{row_string}\n\n"
else:
    print("Errore nella richiesta HTTP:", response.status_code)


@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, f"👋 Benvenuto in ExamBot, {message.from_user.first_name}!\n\nPer iniziare, inserisci la tua matricola:")
    bot.register_next_step_handler(message, check_matricola)


def check_matricola(message):
    matricola_numero = message.text

    if matricola_numero == "/start":
        handle_start(message)

    if (not matricola_numero.isdigit() or len(matricola_numero) != 6) and (matricola_numero != "/start"):
        bot.reply_to(message, "⚠️ La matricola deve essere composta da 6 cifre numeriche."
                              "\nInserisci nuovamente la matricola o usa /start per riavviare il processo:")
        bot.register_next_step_handler(message, check_matricola)
        return

    cursor.execute("SELECT matricole FROM freshman")
    matricole_db = cursor.fetchone()[0].split(",")

    if matricola_numero in matricole_db:
        bot.reply_to(message, f"✅ La matricola è corretta, {message.from_user.first_name}!")
        bot.send_message(message.chat.id, "Ora puoi utilizzare i seguenti comandi:")
        bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
        bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
        bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
    elif matricola_numero != "/start":
        bot.reply_to(message,
                     "❌ La matricola è incorretta."
                     "\nInserisci nuovamente la matricola o usa /start per riavviare il processo:")
        bot.register_next_step_handler(message, check_matricola)


@bot.message_handler(commands=['lista_lezioni'])
def handle_table(message):
    bot.send_message(message.chat.id, table_string)
    bot.reply_to(message, "✅ Lista delle lezioni stampata correttamente!")
    bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
    bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
    bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
    bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")


@bot.message_handler(commands=['prenotazione_lezioni'])
def handle_prenotazioni(message):
    bot.send_message(message.chat.id, "Quale lezione vorresti prenotare?")


@bot.message_handler(func=lambda message: True)
def check_prenotazione(message):
    lezione = message.text

    # Controlla se il messaggio corrisponde a una delle lezioni presenti nella tabella
    for row in values:
        if lezione.lower() == row[0].lower():

            posti_disponibili = 1
            if posti_disponibili > 0:
                bot.send_message(message.chat.id, f"✅ La lezione {lezione} è prenotabile!")
            else:
                bot.send_message(message.chat.id,
                                 f"Mi dispiace, non ci sono posti disponibili per la lezione {lezione}.")
            return

    bot.send_message(message.chat.id, f"❌ La lezione {lezione} non è presente nella lista delle lezioni prenotabili.")


bot.polling()
