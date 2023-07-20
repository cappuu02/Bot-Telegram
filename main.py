import telebot
import sqlite3
from bs4 import BeautifulSoup
import requests
import random
import string

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
    characters = string.ascii_letters + string.digits
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

# La logica per richiedere la matricola
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, f"👋 Benvenuto in ExamBot, {message.from_user.first_name}!\n\n"
                          f"Per iniziare, inserisci la tua matricola:")
    bot.register_next_step_handler(message, check_matricola)

def handle_matricola(message):
    matricola_numero = message.text.strip()

    if matricola_numero == "/start":
        handle_start(message)

    if (not matricola_numero.isdigit() or len(matricola_numero) != 6) and (matricola_numero != "/start"):
        bot.reply_to(message, "⚠️ La matricola deve essere composta da 6 cifre numeriche."
                              "\nInserisci nuovamente la matricola o usa /start per riavviare il processo:")
        bot.register_next_step_handler(message, check_matricola)
        return

    # Chiedi all'utente di inserire la password associata alla matricola
    bot.reply_to(message, "Inserisci la tua password:")
    bot.register_next_step_handler(message, check_password, matricola_numero)

def check_matricola(message):
    matricola_numero = message.text.strip()

    if matricola_numero == "/start":
        handle_start(message)

    if (not matricola_numero.isdigit() or len(matricola_numero) != 6) and (matricola_numero != "/start"):
        bot.reply_to(message, "⚠️ La matricola deve essere composta da 6 cifre numeriche."
                              "\nInserisci nuovamente la matricola o usa /start per riavviare il processo:")
        bot.register_next_step_handler(message, check_matricola)
        return

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




@bot.message_handler(commands=['prenotazione_lezioni'])
def handle_prenotazioni(message):
    bot.send_message(message.chat.id, "Quale lezione vorresti prenotare? Inserisci il nome esatto come nella lista")

    @bot.message_handler(func=lambda message: True)
    def check_prenotazione(message):
        lezione = message.text

        if (lezione == '/start'):
            handle_start(message)
        if (lezione == '/prenotazione_lezioni'):
            handle_prenotazioni(message)
        if (lezione == '/lista_lezioni'):
            handle_table(message)

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
                if (risposta == '/start'):
                    handle_start(message)
                if( risposta == '/prenotazione_lezioni'):
                    handle_prenotazioni(message)
                if( risposta == '/lista_lezioni'):
                    handle_table(message)

                if risposta == 'si':
                    # Esegui la logica per la prenotazione della lezione
                    disponibile = random.choices([True, False], weights=[10, 1])[0]
                    if(disponibile == True):
                        bot.send_message(message.chat.id, "Prenotazione effettuata con successo!")
                        bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
                        bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
                        bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
                        bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
                        bot.register_next_step_handler(message, check_prenotazione)

                    else:
                        bot.send_message(message.chat.id, "Prenotazione fallita, l'aula è piena!")
                        bot.send_message(message.chat.id, "Cosa vuoi fare ora?")
                        bot.send_message(message.chat.id, "/start - Reinserisci la matricola")
                        bot.send_message(message.chat.id, "/lista_lezioni - Visualizza la lista delle lezioni prenotabili")
                        bot.send_message(message.chat.id, "/prenotazione_lezioni - Prenota lezioni")
                        bot.register_next_step_handler(message, check_prenotazione)

                elif risposta == 'no':
                    # Ripeti il processo di prenotazione o esegui altre azioni
                    bot.send_message(message.chat.id, "Va bene, quale lezione vuoi prenotare?.")
                elif risposta != 'no' and risposta != 'si' and risposta != '/start' and risposta != '/prenotazione_lezioni' and risposta != '/lista_lezioni':
                    # Risposta non valida, richiedi una risposta corretta
                    bot.send_message(message.chat.id, "Risposta non valida. Rispondi con 'Si' o 'No'.")
                    bot.register_next_step_handler(message, conferma_prenotazione)

            # Registra la funzione conferma_prenotazione come gestore dei messaggi successivi
            bot.register_next_step_handler(message, conferma_prenotazione)
        elif not lezione_presente and lezione != '/start' and lezione != '/prenotazione_lezioni' and lezione != '/lista_lezioni':
            bot.send_message(message.chat.id, f"❌ La lezione {lezione} non è presente nella lista delle lezioni prenotabili.")
            bot.send_message(message.chat.id, "Quale lezione vuoi prenotare?.")

    # Registra la funzione check_prenotazione come gestore dei messaggi successivi
    bot.register_next_step_handler(message, check_prenotazione)


bot.polling()
