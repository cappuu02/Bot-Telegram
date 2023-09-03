import telebot
import sqlite3
import random
import string
import re
from bs4 import BeautifulSoup
import requests
from datetime import datetime

TOKEN = "5906905240:AAGSH8itptIwVd4NgAiQuMa-lDic2ZRE2kM"  # Inserisci qui il token del tuo bot ottenuto da BotFather

bot = telebot.TeleBot(TOKEN)

# Connessione al database
connection = sqlite3.connect('database_tg.db', check_same_thread=False)
cursor = connection.cursor()

# URL per ottenere le lezioni dal sito
current_date = datetime.now()
formatted_date = current_date.strftime("%Y-%m-%d")
url = f"https://servizi.dmi.unipg.it/mrbs/day.php?year={current_date.year}&month={current_date.month}&day={current_date.day}&area=1&room=3"
response = requests.get(url)

# Dizionario per memorizzare la matricola degli utenti
utenti_matricole = {}

if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")
    div = soup.find("div", id="dwm").get_text(strip=True)
    table = soup.find("table", class_="dwm_main")
    rows = table.find_all("tr")

    header_row = rows[0]
    headers = [header.get_text(strip=True) for header in header_row.find_all("th")]

    values = []
    for row in rows[1:]:
        row_values = [value.get_text(strip=True) for value in row.find_all("td")]
        if any(row_values):
            values.append(row_values)

    values = [row for row in values if any(row[1:])]
    lezioni_array = []

    for row in values:
        for value in row[1:]:
            lezioni_array.append(value)

    table_string = f"📅 Data: {div}\n\n"
    for row in values:
        row_string = "\n".join([f"🔹 {header}: {value}" for header, value in zip(headers, row)])
        table_string += f"{row_string}\n\n"

else:
    print("Errore nella richiesta HTTP:", response.status_code)

# Funzione per generare una password randomica
def generate_password():
    length = 2
    characters = string.ascii_letters
    password = ''.join(random.choice(characters) for i in range(length))
    return password

# Lista delle matricole desiderate con password
matricole_desiderate = {
    "342244": "ed",
    "347711": "lu"
}

# Inserisci le matricole desiderate nell'elenco delle matricole disponibili
available_matricole = []
for matricola, password in matricole_desiderate.items():
    available_matricole.append(matricola)
    try:
        cursor.execute("INSERT INTO freshman (matricole, passwords) VALUES (?, ?)", (matricola, password))
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()

# Genera e inserisci matricole casuali per i rimanenti slot
remaining_slots = 100 - len(matricole_desiderate)
for _ in range(remaining_slots):
    matricola = ''.join(random.choice(string.digits) for _ in range(6))
    password = generate_password()
    try:
        cursor.execute("INSERT INTO freshman (matricole, passwords) VALUES (?, ?)", (matricola, password))
        connection.commit()
        available_matricole.append(matricola)
    except sqlite3.IntegrityError:
        connection.rollback()

# Funzione per controllare la matricola e la password nel database
def check_credentials(matricola, password):
    cursor.execute("SELECT matricole, passwords FROM freshman WHERE matricole = ?", (matricola,))
    result = cursor.fetchone()
    if result and result[1] == password:
        return True
    return False

# Funzione per controllare se una matricola ha già prenotato una lezione nel database
def has_already_booked(matricola, lezione):
    cursor.execute("SELECT lezione FROM prenotazioni WHERE matricola = ? AND lezione = ?", (matricola, lezione))
    result = cursor.fetchone()
    return bool(result)

# Funzione per salvare la prenotazione nel database
def save_booking(matricola, lezione):
    try:
        cursor.execute("INSERT INTO prenotazioni (matricola, lezione) VALUES (?, ?)", (matricola, lezione))
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()

    # Incrementa il numero di posti prenotati per la lezione nel database dei posti prenotati
    cursor.execute("UPDATE posti_prenotati SET posti = posti + 1 WHERE lezione = ?", (lezione,))
    connection.commit()

# Creazione della tabella delle prenotazioni se non esiste
cursor.execute("CREATE TABLE IF NOT EXISTS prenotazioni (matricola TEXT, lezione TEXT, PRIMARY KEY (matricola, lezione))")

# Creazione della tabella dei posti prenotati se non esiste
cursor.execute("CREATE TABLE IF NOT EXISTS posti_prenotati (lezione TEXT PRIMARY KEY, posti INTEGER)")

# Recupera i dati dal database per riempire il dizionario posti_prenotati
cursor.execute("SELECT lezione, posti FROM posti_prenotati")
posti_prenotati = {row[0]: row[1] for row in cursor.fetchall()}

# Inizializza il dizionario dei posti prenotati con le lezioni disponibili e 0 posti prenotati
for lezione in lezioni_array:
    if lezione not in posti_prenotati:
        cursor.execute("INSERT INTO posti_prenotati (lezione, posti) VALUES (?, ?)", (lezione, 0))
        posti_prenotati[lezione] = 0

# Inizializza dizionari per le capacità delle aule e i posti prenotati per ciascuna lezione
capacita_aule = {
    "A0": 180,
    "A2": 180,
    "A3": 70,
    "B1": 30,
    "B3": 35,
    "C2": 20,
    "I1": 215,
    "I2": 90,
    "Riunioni": 40,
    "C3": 25,
    "Gialla": 17,
    "Verde": 18,
}

def get_room_capacity(room_name):
    capacity_match = re.search(r'\((\d+)\)', room_name)
    if capacity_match:
        capacity = int(capacity_match.group(1))
        return capacity
    return 0


@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, f"👋 Benvenuto in ExamBot, {message.from_user.first_name}!\n\n"
                          f"Per iniziare, inserisci la tua matricola:")

    bot.register_next_step_handler(message, check_matricola)

def check_matricola(message):
    matricola_numero = message.text.strip()

    if matricola_numero == "/start":
        handle_start(message)
    if(matricola_numero != "/start" and matricola_numero.startswith('/')):
        bot.reply_to(message, "⚠️ Il comando inserito non è valida, inserisci un comando valido o una matricola esistente.")

        bot.register_next_step_handler(message, check_matricola)

    if (not matricola_numero.isnumeric() or len(matricola_numero) != 6) and matricola_numero.startswith('/') == False:
        bot.reply_to(message, "⚠️ La matricola inserita non è valida, inserisci una matricola di 6 cifre."
                              "\nInserisci una matricola valida o usa /start per riavviare il processo:")
        bot.register_next_step_handler(message, check_matricola)
    elif (matricola_numero not in available_matricole) and matricola_numero.startswith('/') == False:
        bot.reply_to(message, "❌ La matricola inserita non esiste."
                              "\nInserisci una matricola esistente o usa /start per riavviare il processo:")
        bot.register_next_step_handler(message, check_matricola)
    elif matricola_numero in available_matricole:
        # Memorizza la matricola nell'elenco degli utenti
        utenti_matricole[message.from_user.id] = matricola_numero

        # La matricola è già presente, quindi chiediamo direttamente la password
        bot.reply_to(message, "Inserisci la tua password:")
        bot.register_next_step_handler(message, check_password, matricola_numero)

def check_password(message, matricola_numero):
    password = message.text.strip()

    if password == "/start":
        handle_start(message)

    if (password != "/start" and password.startswith('/')):
        bot.reply_to(message,
                     "⚠️ Il comando inserito non è valido, inserisci un comando valido o una password corretta.")

        bot.register_next_step_handler(message, lambda msg: check_password(msg, matricola_numero))
        return

    # Controlla la matricola e la password nel database
    if check_credentials(matricola_numero, password) and not password.startswith('/'):
        bot.reply_to(message, f"✅ La matricola e la password sono corrette, {message.from_user.first_name}!")
        bot.send_message(message.chat.id, "Ora puoi utilizzare i seguenti comandi:")
        bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
        bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
        bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
        bot.send_message(message.chat.id, "/cancella_prenotazione - Cancella la prenotazione di una lezione")
    elif not password.startswith('/'):
        bot.reply_to(message, "❌ La password non è corretta."
                              "\nInserisci nuovamente la password o usa /start per riavviare il processo:")
        bot.register_next_step_handler(message, lambda msg: check_password(msg, matricola_numero))


@bot.message_handler(commands=['lista_lezioni'])
def handle_table(message):
    bot.send_message(message.chat.id, table_string)
    bot.reply_to(message, "✅ Lista delle lezioni stampata correttamente!")
    bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
    bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
    bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
    bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
    bot.send_message(message.chat.id, "/cancella_prenotazione - Cancella la prenotazione di una lezione")


@bot.message_handler(commands=['prenotazione_lezioni'])
def handle_prenotazioni(message):
    matricola_numero = utenti_matricole.get(message.from_user.id)
    bot.send_message(message.chat.id, "Quale lezione vorresti prenotare? Inserisci il nome esatto come nella lista")
    bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))

def check_prenotazione(message, matricola_numero):
    lezione = message.text

    if lezione == '/start':
        handle_start(message)
    elif lezione == '/prenotazione_lezioni':
        handle_prenotazioni(message)
    elif lezione == '/lista_lezioni':
        handle_table(message)
    elif lezione == '/cancella_prenotazione':
        handle_cancella_prenotazione(message)

    if ((lezione != "/start" and lezione != "/lista_lezioni" and lezione != "/prenotazione_lezioni" and lezione != "/cancella_prenotazione") and lezione.startswith('/')):
        bot.reply_to(message, "⚠️ Il comando inserito non è valido, inserisci un comando valido o una lezione corretta.")

        bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))
        return
    elif(not lezione.startswith('/')):
        room_of_lezione = None
        for row in values:
            for lesson_name in row[1:]:
                if lezione.lower() == lesson_name.lower():
                    room_of_lezione = row[0]
                    break
            if room_of_lezione is not None:
                break

        if room_of_lezione is None:
            bot.send_message(message.chat.id, f"❌ La lezione {lezione} non è presente nella lista delle lezioni prenotabili.")
            bot.send_message(message.chat.id, "Quale lezione vuoi prenotare?")
            bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))
        else:
            # Controllo se la matricola ha già prenotato la lezione
            if has_already_booked(matricola_numero, lezione):
                bot.send_message(message.chat.id, f"❌ Hai già prenotato la lezione {lezione}.")
                bot.send_message(message.chat.id, "Quale lezione vuoi prenotare?")
                bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))
            else:
                bot.send_message(message.chat.id, f"✅ La lezione {lezione} è prenotabile nell'aula {room_of_lezione}!")
                bot.send_message(message.chat.id, "Vuoi prenotarla? (Rispondi con 'Si' o 'No')")
                bot.register_next_step_handler(message, lambda msg: conferma_prenotazione(msg, matricola_numero, lezione, room_of_lezione))

def conferma_prenotazione(message, matricola_numero, lezione, room_of_lezione):
    risposta = message.text.lower()

    if risposta == '/start':
        handle_start(message)
    elif risposta == '/prenotazione_lezioni':
        handle_prenotazioni(message)
    elif risposta == '/lista_lezioni':
        handle_table(message)
    elif risposta == '/cancella_prenotazione':
        handle_cancella_prenotazione(message)

    if ((risposta != "/start" and risposta != "/lista_lezioni" and risposta != "/prenotazione_lezioni" and risposta != "/cancella_prenotazione") and risposta.startswith('/')):
        bot.reply_to(message,"⚠️ Il comando inserito non è valido, inserisci un comando valido o una risposta corretta.")

        bot.register_next_step_handler(message, lambda msg: conferma_prenotazione(msg, matricola_numero, lezione, room_of_lezione))
        return
    if risposta == 'si':
        # Prende la capacità dell'aula
        max_capacity = get_room_capacity(room_of_lezione)

        # Prende il numero di posti prenotati rispetto alla lezione nel database
        cursor.execute("SELECT posti FROM posti_prenotati WHERE lezione = ?", (lezione,))
        result = cursor.fetchone()

        if result:
            posti_disponibili = max_capacity - result[0]
        else:
            # Se non ci sono posti prenotati per la lezione, setta posti disponibili alla capacità massima
            posti_disponibili = max_capacity

        if posti_disponibili > 0:
            #L'aula ha posti disponibili, procedi con la prenotazione
            posti_prenotati[lezione] += 1
            bot.send_message(message.chat.id, "✅ Prenotazione effettuata con successo!")
            #Salva la prenotazione nel database
            save_booking(matricola_numero, lezione)

            #Aggiorna il numero di posti prenotati per la lezione nella tabella posti_prenotati
            cursor.execute("INSERT OR REPLACE INTO posti_prenotati (lezione, posti) VALUES (?, ?)", (lezione, posti_prenotati[lezione]))
            connection.commit()

            bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
            bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
            bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
            bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
            bot.send_message(message.chat.id, "/cancella_prenotazione - Cancella la prenotazione di una lezione")
        else:
            bot.send_message(message.chat.id, "❌ Prenotazione fallita, l'aula è piena!")
            bot.send_message(message.chat.id, "Quale lezione vuoi prenotare?")
            bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))
    elif risposta != 'no' and not risposta.startswith('/'):
        bot.send_message(message.chat.id, "⚠️ Risposta non valida. Rispondi con 'Si' o 'No'.")
        bot.register_next_step_handler(message, lambda msg: conferma_prenotazione(msg, matricola_numero, lezione, room_of_lezione))
    elif risposta == 'no':
        bot.send_message(message.chat.id, "Quale lezione vuoi prenotare?")
        bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))

@bot.message_handler(commands=['cancella_prenotazione'])
def handle_cancella_prenotazione(message):
    matricola_numero = utenti_matricole.get(message.from_user.id)

    bot.send_message(message.chat.id, "Quale lezione vuoi cancellare? Inserisci il nome esatto come nella lista")
    bot.register_next_step_handler(message, lambda msg: cancella_prenotazione(msg, matricola_numero))

def cancella_prenotazione(message, matricola_numero):
    lezione = message.text

    if lezione == '/start':
        handle_start(message)
    elif lezione == '/cancella_prenotazione':
        handle_cancella_prenotazione(message)
    elif lezione == '/lista_lezioni':
        handle_table(message)
    elif lezione == '/prenotazione_lezioni':
        handle_prenotazioni(message)

    if ((lezione != "/start" and lezione != "/lista_lezioni" and lezione != "/prenotazione_lezioni" and lezione != "/cancella_prenotazione") and lezione.startswith('/')):
        bot.reply_to(message,
                     "⚠️ Il comando inserito non è valido, inserisci un comando valido o una lezione corretta.")

        bot.register_next_step_handler(message, lambda msg: cancella_prenotazione(msg, matricola_numero))
        return

    elif(not lezione.startswith('/')):
        # Controlla che l'utente abbia prenotato la lezione
        if has_already_booked(matricola_numero, lezione):
            cursor.execute("DELETE FROM prenotazioni WHERE matricola = ? AND lezione = ?", (matricola_numero, lezione))
            connection.commit()
            posti_prenotati[lezione] -= 1

            #Aggiorna il numero di posti prenotati per la lezione nella tabella posti_prenotati
            cursor.execute("INSERT OR REPLACE INTO posti_prenotati (lezione, posti) VALUES (?, ?)",
                           (lezione, posti_prenotati[lezione]))
            connection.commit()

            bot.send_message(message.chat.id, f"✅ Prenotazione per la lezione {lezione} cancellata con successo!")

            bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
            bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
            bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
            bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
            bot.send_message(message.chat.id, "/cancella_prenotazione - Cancella la prenotazione di una lezione")
        else:
            bot.send_message(message.chat.id, f"❌ Non hai prenotato la lezione {lezione}.")
            bot.send_message(message.chat.id, "Quale lezione vuoi cancellare? Inserisci il nome esatto come nella lista")
            bot.register_next_step_handler(message, lambda msg: cancella_prenotazione(msg, matricola_numero))

bot.infinity_polling(timeout=10, long_polling_timeout=5)
