import os
import logging
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = '8993583441:AAHeu6EFIZBgv_4w-Um5h0wzxwSulbtaFvU'
BASE_URL = 'https://instantnum.com'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def get_countries():
    try:
        resp = requests.get(BASE_URL + '/countries', headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        countries = {}
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/countries/' in href and href != '/countries':
                text = link.get_text(strip=True)
                match = re.match(r'([A-Za-z ]+)', text)
                if match:
                    name = match.group(1).strip()
                    code = href.split('/countries/')[1]
                    countries[code] = name
        return countries
    except Exception as e:
        logger.error('Error countries: ' + str(e))
        return None


def get_numbers(country_code):
    try:
        resp = requests.get(BASE_URL + '/countries/' + country_code, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        numbers = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/countries/' + country_code + '/' in href:
                number = href.split('/')[-1]
                if number.startswith('%2B'):
                    number = number.replace('%2B', '+')
                numbers.append({'number': number, 'url': href})
        return numbers
    except Exception as e:
        logger.error('Error numbers: ' + str(e))
        return None


def get_messages(number_url):
    try:
        resp = requests.get(BASE_URL + number_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        messages = []
        for div in soup.find_all('div', class_=lambda x: x and 'rounded-2xl' in x and 'border-2' in x if x else False):
            text = div.get_text(strip=True)
            if text and len(text) > 10:
                lines = text.splitlines()
                if len(lines) >= 2:
                    sender = 'Unknown'
                    time_ago = ''
                    message_text = ''
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if 'ago' in line.lower():
                            time_match = re.search(r'(\d+\s+(?:minute|hour|day|second)s?\s+ago)', line, re.IGNORECASE)
                            if time_match:
                                time_ago = time_match.group(1)
                            msg_part = re.sub(r'\d+\s+(?:minute|hour|day|second)s?\s+ago', '', line, flags=re.IGNORECASE).strip()
                            if msg_part:
                                message_text = msg_part
                        elif not time_ago and not message_text:
                            sender = line
                        else:
                            message_text = line
                    if message_text:
                        messages.append({'sender': sender[:50], 'time': time_ago or 'Unknown', 'text': message_text[:500]})
        return messages
    except Exception as e:
        logger.error('Error messages: ' + str(e))
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton('Ver Paises', callback_data='countries')],
        [InlineKeyboardButton('Buscar por Servicio', callback_data='services')],
        [InlineKeyboardButton('Ayuda', callback_data='help')],
    ]
    user = update.effective_user
    welcome = (
        'Hola ' + user.first_name + '!\n\n'
        'Bot de Numeros Virtuales Gratis\n'
        'Numeros publicos para recibir SMS\n\n'
        'Aviso: Estos numeros son PUBLICOS\n'
        'Cualquiera puede leer los SMS\n\n'
        'Selecciona una opcion:'
    )
    await update.message.reply_text('\n'.join(welcome), reply_markup=InlineKeyboardMarkup(keyboard))


async def show_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('Cargando paises...')
    countries = get_countries()
    if not countries:
        await query.edit_message_text('Error al cargar paises. Intenta mas tarde.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Volver', callback_data='menu')]]))
        return
    buttons = []
    row = []
    for code, name in sorted(countries.items(), key=lambda x: x[1]):
        row.append(InlineKeyboardButton(name, callback_data='country:' + code))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton('Volver', callback_data='menu')])
    await query.edit_message_text('Selecciona un pais:', reply_markup=InlineKeyboardMarkup(buttons))


async def show_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    country_code = query.data.split(':', 1)[1]
    context.user_data['selected_country'] = country_code
    await query.edit_message_text('Cargando numeros...')
    numbers = get_numbers(country_code)
    if not numbers:
        await query.edit_message_text('Error al cargar numeros.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Volver', callback_data='countries')]]))
        return
    buttons = []
    for num_data in numbers[:20]:
        number = num_data['number']
        display = number[:20] if len(number) > 20 else number
        buttons.append([InlineKeyboardButton(display, callback_data='number:' + num_data['url'])])
    buttons.append([InlineKeyboardButton('Volver', callback_data='countries')])
    await query.edit_message_text('Numeros disponibles (' + str(len(numbers)) + ' total):\nToca un numero para ver sus SMS', reply_markup=InlineKeyboardMarkup(buttons))


async def show_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    number_url = query.data.split(':', 1)[1]
    context.user_data['selected_number'] = number_url
    await query.edit_message_text('Cargando mensajes SMS...')
    messages = get_messages(number_url)
    if messages is None:
        await query.edit_message_text('Error al cargar mensajes.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Reintentar', callback_data='number:' + number_url)], [InlineKeyboardButton('Volver', callback_data='countries')]]))
        return
    if not messages:
        await query.edit_message_text('No hay mensajes aun. Espera unos minutos.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Actualizar', callback_data='number:' + number_url)], [InlineKeyboardButton('Volver', callback_data='countries')]]))
        return
    text = 'MENSAJES SMS\n\n'
    for i, msg in enumerate(messages[:10], 1):
        text += '#' + str(i) + '\nDe: ' + msg['sender'] + '\nHace: ' + msg['time'] + '\nMensaje: ' + msg['text'][:200] + '\n' + ('-' * 30) + '\n'
    keyboard = [
        [InlineKeyboardButton('Actualizar', callback_data='number:' + number_url)],
        [InlineKeyboardButton('Copiar Numero', callback_data='copy:' + number_url)],
        [InlineKeyboardButton('Volver', callback_data='countries')],
    ]
    if len(text) > 4000:
        text = text[:3950] + '\n\n... (truncado)'
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def copy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    number_url = query.data.split(':', 1)[1]
    number = number_url.split('/')[-1].replace('%2B', '+')
    await query.edit_message_text(
        'Numero: `' + number + '`\n\nUsa este numero para verificar WhatsApp, Telegram, etc.\nLuego presiona Actualizar para ver el codigo SMS.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Actualizar SMS', callback_data='number:' + number_url)], [InlineKeyboardButton('Volver', callback_data='countries')]]),
        parse_mode='Markdown'
    )


async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    services = [('WhatsApp', 'whatsapp'), ('Telegram', 'telegram'), ('Instagram', 'instagram'), ('Facebook', 'facebook'), ('Google', 'google'), ('Twitter', 'twitter'), ('TikTok', 'tiktok'), ('Amazon', 'amazon'), ('Netflix', 'netflix'), ('Spotify', 'spotify')]
    buttons = []
    row = []
    for name, code in services:
        row.append(InlineKeyboardButton(name, callback_data='service:' + code))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton('Volver', callback_data='menu')])
    await query.edit_message_text('Selecciona un servicio:', reply_markup=InlineKeyboardMarkup(buttons))


async def search_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = query.data.split(':', 1)[1]
    await query.edit_message_text('Buscando numeros con SMS de ' + service.capitalize() + '...')
    countries = get_countries()
    if not countries:
        await query.edit_message_text('Error al buscar.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Volver', callback_data='services')]]))
        return
    found_numbers = []
    for code in list(countries.keys())[:5]:
        numbers = get_numbers(code)
        if numbers:
            for num in numbers[:3]:
                messages = get_messages(num['url'])
                if messages:
                    for msg in messages:
                        if service.lower() in msg['text'].lower() or service.lower() in msg['sender'].lower():
                            found_numbers.append({'number': num['number'], 'url': num['url'], 'message': msg['text'][:100], 'country': countries.get(code, code)})
                            break
    if not found_numbers:
        await query.edit_message_text('No se encontraron numeros con SMS de ' + service.capitalize() + '.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Volver', callback_data='services')]]))
        return
    text = 'Numeros con SMS de ' + service.capitalize() + ':\n\n'
    buttons = []
    for num in found_numbers[:10]:
        text += num['number'] + ' (' + num['country'] + ')\nUltimo SMS: ' + num['message'][:80] + '...\n\n'
        buttons.append([InlineKeyboardButton(num['number'][:25], callback_data='number:' + num['url'])])
    buttons.append([InlineKeyboardButton('Volver', callback_data='services')])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        'AYUDA\n\n'
        'Este bot obtiene numeros PUBLICOS de instantnum.com\n\n'
        'IMPORTANTE:\n'
        '- Los numeros son PUBLICOS\n'
        '- Cualquiera puede leer los SMS\n'
        '- NO uses para cuentas importantes\n\n'
        'COMO USAR:\n'
        '1. Presiona Ver Paises\n'
        '2. Selecciona un pais\n'
        '3. Toca un numero\n'
        '4. Copia el numero y usalo\n'
        '5. Presiona Actualizar para ver el SMS\n\n'
        'COMANDOS:\n'
        '/start - Iniciar\n'
        '/paises - Ver paises\n'
        '/buscar - Buscar por servicio\n'
        '/ayuda - Ayuda'
    )
    await query.edit_message_text('\n'.join(text), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Menu', callback_data='menu')]]))


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton('Ver Paises', callback_data='countries')],
        [InlineKeyboardButton('Buscar por Servicio', callback_data='services')],
        [InlineKeyboardButton('Ayuda', callback_data='help')],
    ]
    await query.edit_message_text('Bot de Numeros Virtuales Gratis\n\nSelecciona una opcion:', reply_markup=InlineKeyboardMarkup(keyboard))


async def cmd_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_countries(update, context)


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_services(update, context)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Comandos: /start /paises /buscar /ayuda')


def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CallbackQueryHandler(show_countries, pattern='^countries$'))
    application.add_handler(CallbackQueryHandler(show_numbers, pattern='^country:'))
    application.add_handler(CallbackQueryHandler(show_messages, pattern='^number:'))
    application.add_handler(CallbackQueryHandler(copy_number, pattern='^copy:'))
    application.add_handler(CallbackQueryHandler(show_services, pattern='^services$'))
    application.add_handler(CallbackQueryHandler(search_service, pattern='^service:'))
    application.add_handler(CallbackQueryHandler(help_handler, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(menu_handler, pattern='^menu$'))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('paises', cmd_countries))
    application.add_handler(CommandHandler('buscar', cmd_search))
    application.add_handler(CommandHandler('ayuda', cmd_help))
    print('Bot iniciado!')
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()
