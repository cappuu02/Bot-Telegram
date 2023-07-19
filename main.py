import telebot
import sqlite3
from bs4 import BeautifulSoup
import requests
import random

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
    # Creazione dell'array delle lezioni
    lezioni_array = []

    for row in values:
        lezione = row[1]
        lezioni_array.append(lezione)

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

        # Controlla se il messaggio corrisponde a una delle lezioni presenti nell'array delle lezioni
        lezione_presente = False
        for l in lezioni_array:
            if lezione.lower() == l.lower():
                lezione_presente = True
                break

        if lezione_presente:
            bot.send_message(message.chat.id, f"✅ La lezione {lezione} è prenotabile!")
            bot.send_message(message.chat.id, f"Vuoi prenotarla? (Rispondi con 'Si' o 'No')")

            @bot.message_handler(func=lambda message: message.text.lower() in ['si', 'no'])
            def conferma_prenotazione(message):
                risposta = message.text.lower()
                if risposta == 'si':
                    # Esegui la logica per la prenotazione della lezione
                    disponibile = random.choice([True, False])
                    if(disponibile == True):
                        bot.send_message(message.chat.id, "Prenotazione effettuata con successo!")
                        bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
                        bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
                        bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
                        bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")

                    else:
                        bot.send_message(message.chat.id, "Prenotazione fallita, l'aula è piena!")
                        bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
                        bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
                        bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
                        bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")


                elif risposta == 'no':
                    # Ripeti il processo di prenotazione o esegui altre azioni
                    bot.send_message(message.chat.id, "Va bene, ripeti il processo di prenotazione.")
                else:
                    # Risposta non valida, richiedi una risposta corretta
                    bot.send_message(message.chat.id, "Risposta non valida. Rispondi con 'Si' o 'No'.")
                    bot.register_next_step_handler(message, conferma_prenotazione)

            # Registra la funzione conferma_prenotazione come gestore dei messaggi successivi
            bot.register_next_step_handler(message, conferma_prenotazione)
        else:
            bot.send_message(message.chat.id, f"❌ La lezione {lezione} non è presente nella lista delle lezioni prenotabili.")
            bot.send_message(message.chat.id, "Puoi ripetere il processo di prenotazione con una lezione diversa.")

    # Registra la funzione check_prenotazione come gestore dei messaggi successivi
    bot.register_next_step_handler(message, check_prenotazione)


bot.polling()
