import telebot
import sqlite3
from bs4 import BeautifulSoup
import requests
import random
import string
from datetime import datetime
import re

TOKEN = "5906905240:AAGSH8itptIwVd4NgAiQuMa-lDic2ZRE2kM"  # Inserisci qui il token del tuo bot ottenuto da BotFather

bot = telebot.TeleBot(TOKEN)

connection = sqlite3.connect('database_tg.db', check_same_thread=False)
cursor = connection.cursor()

# Get the current date
current_date = datetime.now()
formatted_date = current_date.strftime("%Y-%m-%d")

# Construct the URL with the current date
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

# Funzione per creare un record nel database con la matricola e la password associate
def create_freshman(matricola, password):
    try:
        cursor.execute("INSERT INTO freshman (matricole, passwords) VALUES (?, ?)", (matricola, password))
        connection.commit()
    except sqlite3.IntegrityError:
        # Se la matricola è già presente nel database, esegui solo il rollback
        connection.rollback()

# Funzione per controllare la matricola e la password nel database
def check_credentials(matricola, password):
    cursor.execute("SELECT matricole, passwords FROM freshman WHERE matricole = ?", (matricola,))
    result = cursor.fetchone()
    if result and result[1] == password:
        return True
    return False

# Creazione della tabella se non esiste
cursor.execute("CREATE TABLE IF NOT EXISTS freshman (matricole TEXT PRIMARY KEY, passwords TEXT)")


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
        # Se la prenotazione è già presente nel database, esegui solo il rollback
        connection.rollback()

# Creazione della tabella delle prenotazioni se non esiste
cursor.execute("CREATE TABLE IF NOT EXISTS prenotazioni (matricola TEXT, lezione TEXT, PRIMARY KEY (matricola, lezione))")



# Initialize dictionaries to store room capacities and booked seats for each lesson
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


posti_prenotati = {
    lesson: 0 for lesson in lezioni_array
}


# La logica per richiedere la matricola
@bot.message_handler(commands=['start'])
@bot.message_handler(commands=['start'])
def handle_start(message):
    utenti_matricole[message.from_user.id] = None  # Inizializziamo la matricola come None
    bot.reply_to(message, f"👋 Benvenuto in ExamBot, {message.from_user.first_name}!\n\n"
                          f"Per iniziare, inserisci la tua matricola:")
    bot.register_next_step_handler(message, check_matricola)

def check_matricola(message):
    matricola_numero = message.text.strip()

    if matricola_numero == "/start":
        handle_start(message)

    if (not matricola_numero.isdigit() or len(matricola_numero) != 6) and (matricola_numero != "/start"):
        bot.reply_to(message, "⚠️ La matricola deve essere composta da 6 cifre numeriche."
                              "\nInserisci nuovamente la matricola o usa /start per riavviare il processo:")
        bot.register_next_step_handler(message, check_matricola)
        return

    # Memorizza la matricola nell'elenco degli utenti
    utenti_matricole[message.from_user.id] = matricola_numero

    # Controlla se la matricola è già presente nel database
    cursor.execute("SELECT passwords FROM freshman WHERE matricole = ?", (matricola_numero,))
    result = cursor.fetchone()

    if result:
        # La matricola è già presente, quindi chiediamo direttamente la password
        bot.reply_to(message, f"Se la tua matricola dovesse essere già occupata contatta un amministratore")
        bot.reply_to(message, "Inserisci la tua password:")
        bot.register_next_step_handler(message, check_password, matricola_numero)
    elif(matricola_numero != "/start"):

          # La matricola è nuova, genera una password randomica e assegnala al database
          password = generate_password()
          create_freshman(matricola_numero, password)

          bot.reply_to(message, f"✅ La tua matricola è stata registrata correttamente.\n\n"
                              f"La tua matricola: {matricola_numero}\n"
                              f"La tua password: {password}\n\n"
                              f"Ora puoi utilizzare la tua matricola e password per accedere alle funzionalità del bot, premi /start per iniziare.")
          bot.register_next_step_handler(message, handle_start)

def check_password(message, matricola_numero):
    password = message.text.strip()

    if password == "/start":
        handle_start(message)

    # Controlla la matricola e la password nel database
    if check_credentials(matricola_numero, password):
        bot.reply_to(message, f"✅ La matricola e la password sono corrette, {message.from_user.first_name}!")
        bot.send_message(message.chat.id, "Ora puoi utilizzare i seguenti comandi:")
        bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
        bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
        bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
        bot.send_message(message.chat.id, "/cancella_prenotazione - Cancella la prenotazione di una lezione")
    elif(password != "/start"):
        bot.reply_to(message, "❌ La matricola o la password non sono corrette."
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

    else:
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
            bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))  # Pass the matricola_numero argument
        else:
            # Check if the matricola has already booked the same lesson
            if has_already_booked(matricola_numero, lezione):
                bot.send_message(message.chat.id, f"❌ Hai già prenotato la lezione {lezione}.")
                bot.send_message(message.chat.id, "Quale lezione vuoi prenotare?")
                bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))  # Pass the matricola_numero argument
            else:
                bot.send_message(message.chat.id, f"✅ La lezione {lezione} è prenotabile nell'aula {room_of_lezione}!")
                bot.send_message(message.chat.id, "Vuoi prenotarla? (Rispondi con 'Si' o 'No')")
                bot.register_next_step_handler(message, lambda msg: conferma_prenotazione(msg, matricola_numero, lezione, room_of_lezione))

def conferma_prenotazione(message, matricola_numero, lezione, room_of_lezione):
    risposta = message.text.lower()

    if risposta == 'si':
        # Get the capacity from the room name
        max_capacity = get_room_capacity(room_of_lezione)

        if posti_prenotati[lezione] < max_capacity:
            # Room has available seats, proceed with booking
            posti_prenotati[lezione] += 1
            bot.send_message(message.chat.id, "Prenotazione effettuata con successo!")
            # Save the booking in the database
            save_booking(matricola_numero, lezione)
            print(matricola_numero)

            bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
            bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
            bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
            bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
            bot.send_message(message.chat.id, "/cancella_prenotazione - Cancella la prenotazione di una lezione")
        else:
            bot.send_message(message.chat.id, "Prenotazione fallita, l'aula è piena!")
            bot.send_message(message.chat.id, "Quale lezione vuoi prenotare?")
            bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg, matricola_numero))
    elif risposta != 'no':
        bot.send_message(message.chat.id, "Risposta non valida. Rispondi con 'Si' o 'No'.")
        bot.register_next_step_handler(message, lambda msg: conferma_prenotazione(msg, matricola_numero, lezione, room_of_lezione))
    elif risposta == 'no':
        bot.send_message(message.chat.id, "Quale lezione vuoi prenotare?")
        bot.register_next_step_handler(message, lambda msg: check_prenotazione(msg,matricola_numero))


@bot.message_handler(commands=['cancella_prenotazione'])
def handle_cancella_prenotazione(message):
    matricola_numero = utenti_matricole.get(message.from_user.id)
    if matricola_numero is None:
        # L'utente non ha inserito la matricola all'inizio del programma
        bot.reply_to(message, "Inserisci la tua matricola prima di procedere.")
        bot.send_message(message.chat.id, "Puoi inserire la matricola utilizzando il comando /start.")
    else:
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
    else:
        # Verifica se l'utente ha prenotato la lezione
        if has_already_booked(matricola_numero, lezione):
            cursor.execute("DELETE FROM prenotazioni WHERE matricola = ? AND lezione = ?", (matricola_numero, lezione))
            connection.commit()
            posti_prenotati[lezione] -= 1
            bot.send_message(message.chat.id, f"✅ Prenotazione per la lezione {lezione} cancellata con successo!")

            bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
            bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
            bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
            bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
            bot.send_message(message.chat.id, "/cancella_prenotazione - Cancella la prenotazione di una lezione")


        else:
            bot.send_message(message.chat.id, f"❌ Non hai prenotato la lezione {lezione}.")
            bot.register_next_step_handler(message, lambda msg: handle_cancella_prenotazione(msg, matricola_numero))




bot.polling()
