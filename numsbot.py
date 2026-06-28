"""
Bot de Telegram para numeros virtuales usando 5sim.net API
Version simple sin caracteres especiales
"""

import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest

TOKEN = "8993583441:AAHeu6EFIZBgv_4w-Um5h0wzxwSulbtaFvU"
SIM_TOKEN = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MTQyMDgwOTMsImlhdCI6MTc4MjY3MjA5MywicmF5IjoiMWJhNTU1ZTJhNDU3N2MzNDczZTYzN2I5NGQxOTVhNzAiLCJzdWIiOjQyNjY1Mjl9.LORe_1dgja8MYeLo9i-F0-HP7jXqp1KTB-Oi7HgndtP1S6ptAL5N-z2nLQqXTFuZX2Pqt6Mw5_t8c67IkcnBMg3u7pKMiBwccYDAj7QFQzg1AQFOkELgOkmkN7sIAPUGbRvxz5SPd6MyYLZhI7RrAfZzBLs4UKZ7SVk5OpqCjp68fTb9IH1ae2WDfwxtquUbPvdj9UWM786HIZJ0ZFbUzzZm1gULexvEEW9EsviV54Ye5EoE2s27rYSAzwzJl8bc47sRp6GNFezCQ4lq2XX4gUn2kDKPO3hQ8WxstA04YNVj0z4zsMJReRN1p6sTEjcO39fBBJ2D6GDSU3uc8-1hdg"

BASE_URL = "https://5sim.net/v1"
HEADERS = {
    "Authorization": "Bearer " + SIM_TOKEN,
    "Accept": "application/json"
}

user_orders = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def api_get(endpoint, params=None, auth=True):
    url = BASE_URL + endpoint
    headers = HEADERS if auth else {"Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error("API Error: " + str(e))
        return None


def get_profile():
    return api_get("/user/profile")


def get_countries():
    return api_get("/guest/countries", auth=False)


def get_products(country, operator="any"):
    return api_get("/guest/products/" + country + "/" + operator, auth=False)


def buy_number(country, operator, product):
    return api_get("/user/buy/activation/" + country + "/" + operator + "/" + product)


def check_order(order_id):
    return api_get("/user/check/" + str(order_id))


def finish_order(order_id):
    return api_get("/user/finish/" + str(order_id))


def cancel_order(order_id):
    return api_get("/user/cancel/" + str(order_id))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Ver Balance", callback_data="balance")],
        [InlineKeyboardButton("Comprar Numero", callback_data="buy")],
        [InlineKeyboardButton("Mis Ordenes", callback_data="orders")],
        [InlineKeyboardButton("Ayuda", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Bienvenido al Bot de Numeros Virtuales\n"
        "Powered by 5sim.net\n\n"
        "Selecciona una opcion:",
        reply_markup=reply_markup
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = get_profile()
    if profile:
        text = (
            "Tu Balance\n\n"
            "Balance: " + str(profile.get('balance', 0)) + " rub\n"
            "Congelado: " + str(profile.get('frozen_balance', 0)) + " rub\n"
            "Rating: " + str(profile.get('rating', 0)) + "\n"
            "Pais default: " + str(profile.get('default_country', {}).get('name', 'N/A'))
        )
    else:
        text = "Error al obtener el balance"
    
    keyboard = [[InlineKeyboardButton("Volver", callback_data="menu")]]
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    countries = get_countries()
    if not countries:
        await query.edit_message_text("Error al cargar paises")
        return
    
    popular = ["usa", "england", "germany", "france", "canada", "brazil", "peru", "mexico"]
    buttons = []
    
    for code in popular:
        if code in countries:
            name = countries[code].get("text_en", code)
            prefix = list(countries[code].get("prefix", {}).keys())[0] if countries[code].get("prefix") else ""
            buttons.append([InlineKeyboardButton(
                name + " (" + prefix + ")", callback_data="country:" + code
            )])
    
    buttons.append([InlineKeyboardButton("Ver todos los paises", callback_data="all_countries")])
    buttons.append([InlineKeyboardButton("Volver", callback_data="menu")])
    
    await query.edit_message_text(
        "Selecciona un pais:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_all_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    countries = get_countries()
    if not countries:
        await query.edit_message_text("Error al cargar paises")
        return
    
    buttons = []
    row = []
    for code, data in sorted(countries.items(), key=lambda x: x[1].get("text_en", x[0])):
        name = data.get("text_en", code)
        if len(name) > 20:
            name = name[:17] + "..."
        row.append(InlineKeyboardButton(name, callback_data="country:" + code))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("Volver", callback_data="buy")])
    
    await query.edit_message_text(
        "Todos los paises disponibles:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    country = query.data.split(":")[1]
    context.user_data["selected_country"] = country
    
    products = get_products(country)
    if not products:
        await query.edit_message_text("Error al cargar productos")
        return
    
    activation_products = {k: v for k, v in products.items() if v.get("Category") == "activation"}
    
    if not activation_products:
        await query.edit_message_text(
            "No hay productos de activacion disponibles para este pais",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="buy")]])
        )
        return
    
    buttons = []
    row = []
    for product_name, data in sorted(activation_products.items()):
        price = data.get("Price", "?")
        display_name = product_name.capitalize()
        btn_text = display_name + " (" + str(price) + "rub)"
        row.append(InlineKeyboardButton(btn_text, callback_data="product:" + product_name))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("Volver", callback_data="buy")])
    
    await query.edit_message_text(
        "Selecciona un servicio para " + country + ":",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def buy_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product = query.data.split(":")[1]
    country = context.user_data.get("selected_country", "any")
    
    await query.edit_message_text("Comprando numero...")
    
    result = buy_number(country, "any", product)
    
    if not result:
        await query.edit_message_text(
            "Error al comprar el numero. Posibles causas: sin saldo, sin stock, o error del servidor",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="buy")]])
        )
        return
    
    user_id = update.effective_user.id
    order_id = result["id"]
    user_orders[user_id] = {
        "order_id": order_id,
        "phone": result["phone"],
        "product": result["product"],
        "price": result["price"],
        "status": result["status"],
        "country": result["country"]
    }
    
    keyboard = [
        [InlineKeyboardButton("Verificar SMS", callback_data="check:" + str(order_id))],
        [InlineKeyboardButton("Finalizar", callback_data="finish:" + str(order_id))],
        [InlineKeyboardButton("Cancelar", callback_data="cancel:" + str(order_id))],
    ]
    
    await query.edit_message_text(
        "Numero comprado exitosamente!\n\n"
        "Numero: " + result['phone'] + "\n"
        "Servicio: " + result['product'].capitalize() + "\n"
        "Precio: " + str(result['price']) + " rub\n"
        "Estado: " + result['status'] + "\n\n"
        "La orden expira en 15 minutos\n"
        "Presiona Verificar SMS para revisar mensajes",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def check_sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split(":")[1])
    
    await query.edit_message_text("Verificando SMS...")
    
    result = check_order(order_id)
    
    if not result:
        await query.edit_message_text("Error al verificar")
        return
    
    sms_list = result.get("sms", []) or []
    status = result.get("status", "UNKNOWN")
    
    if sms_list:
        sms_text = ""
        for i, sms in enumerate(sms_list):
            sms_text += "SMS #" + str(i+1) + "\n"
            sms_text += "De: " + str(sms.get('sender', 'Unknown')) + "\n"
            sms_text += "Mensaje: " + str(sms.get('text', 'N/A')) + "\n"
            sms_text += "Codigo: " + str(sms.get('code', 'N/A')) + "\n\n"
        
        keyboard = [
            [InlineKeyboardButton("Actualizar", callback_data="check:" + str(order_id))],
            [InlineKeyboardButton("Finalizar", callback_data="finish:" + str(order_id))],
        ]
        
        await query.edit_message_text(
            "SMS Recibidos!\n\n" + sms_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Reintentar", callback_data="check:" + str(order_id))],
            [InlineKeyboardButton("Cancelar", callback_data="cancel:" + str(order_id))],
        ]
        
        await query.edit_message_text(
            "Esperando SMS...\n\n"
            "Numero: " + str(result.get('phone', 'N/A')) + "\n"
            "Estado: " + status + "\n\n"
            "Aun no hay SMS. Presiona Reintentar en unos segundos.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def finish_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split(":")[1])
    result = finish_order(order_id)
    
    if result:
        user_id = update.effective_user.id
        if user_id in user_orders:
            del user_orders[user_id]
        
        await query.edit_message_text(
            "Orden finalizada exitosamente!\n\n"
            "Gracias por usar el bot.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="menu")]])
        )
    else:
        await query.edit_message_text("Error al finalizar la orden")


async def cancel_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split(":")[1])
    result = cancel_order(order_id)
    
    if result:
        user_id = update.effective_user.id
        if user_id in user_orders:
            del user_orders[user_id]
        
        await query.edit_message_text(
            "Orden cancelada\n\n"
            "El saldo ha sido reembolsado (si aplica).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="menu")]])
        )
    else:
        await query.edit_message_text("Error al cancelar la orden")


async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    order = user_orders.get(user_id)
    
    if not order:
        await query.edit_message_text(
            "No tienes ordenes activas",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="menu")]])
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("Verificar SMS", callback_data="check:" + str(order['order_id']))],
        [InlineKeyboardButton("Finalizar", callback_data="finish:" + str(order['order_id']))],
        [InlineKeyboardButton("Cancelar", callback_data="cancel:" + str(order['order_id']))],
        [InlineKeyboardButton("Menu", callback_data="menu")],
    ]
    
    await query.edit_message_text(
        "Tu Orden Activa\n\n"
        "Numero: " + order['phone'] + "\n"
        "Servicio: " + order['product'].capitalize() + "\n"
        "Precio: " + str(order['price']) + " rub\n"
        "Pais: " + order['country'],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "Ayuda del Bot\n\n"
        "Comandos disponibles:\n"
        "/start - Menu principal\n"
        "/balance - Ver tu saldo\n"
        "/buy - Comprar un numero\n"
        "/orders - Ver ordenes activas\n\n"
        "Como usar:\n"
        "1. Presiona Comprar Numero\n"
        "2. Selecciona un pais\n"
        "3. Selecciona un servicio (WhatsApp, Telegram, etc.)\n"
        "4. Espera a recibir el numero\n"
        "5. Presiona Verificar SMS para ver el codigo\n\n"
        "Notas:\n"
        "- Las ordenes expiran en 15 minutos\n"
        "- Si no recibes SMS, cancela para reembolso\n"
        "- Necesitas saldo en 5sim.net"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="menu")]])
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Ver Balance", callback_data="balance")],
        [InlineKeyboardButton("Comprar Numero", callback_data="buy")],
        [InlineKeyboardButton("Mis Ordenes", callback_data="orders")],
        [InlineKeyboardButton("Ayuda", callback_data="help")],
    ]
    
    await query.edit_message_text(
        "Bot de Numeros Virtuales\n"
        "Powered by 5sim.net\n\n"
        "Selecciona una opcion:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = get_profile()
    if profile:
        text = (
            "Tu Balance\n\n"
            "Balance: " + str(profile.get('balance', 0)) + " rub\n"
            "Congelado: " + str(profile.get('frozen_balance', 0)) + " rub\n"
            "Rating: " + str(profile.get('rating', 0))
        )
    else:
        text = "Error al obtener el balance"
    await update.message.reply_text(text)


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_countries(update, context)


async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    order = user_orders.get(user_id)
    
    if not order:
        await update.message.reply_text("No tienes ordenes activas")
        return
    
    text = (
        "Orden Activa\n\n"
        "Numero: " + order['phone'] + "\n"
        "Servicio: " + order['product'] + "\n"
        "Precio: " + str(order['price']) + " rub"
    )
    await update.message.reply_text(text)


def main():
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=60.0,
    )
    
    application = Application.builder().token(TOKEN).request(request).build()
    
    application.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    application.add_handler(CallbackQueryHandler(show_countries, pattern="^buy$"))
    application.add_handler(CallbackQueryHandler(show_all_countries, pattern="^all_countries$"))
    application.add_handler(CallbackQueryHandler(show_products, pattern="^country:"))
    application.add_handler(CallbackQueryHandler(buy_number_handler, pattern="^product:"))
    application.add_handler(CallbackQueryHandler(check_sms, pattern="^check:"))
    application.add_handler(CallbackQueryHandler(finish_order_handler, pattern="^finish:"))
    application.add_handler(CallbackQueryHandler(cancel_order_handler, pattern="^cancel:"))
    application.add_handler(CallbackQueryHandler(show_orders, pattern="^orders$"))
    application.add_handler(CallbackQueryHandler(help_handler, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(menu_handler, pattern="^menu$"))
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", cmd_balance))
    application.add_handler(CommandHandler("buy", cmd_buy))
    application.add_handler(CommandHandler("orders", cmd_orders))
    
    print("Bot iniciado! Presiona Ctrl+C para detener.")
    print("Timeouts configurados: 60 segundos")
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=2.0,
        timeout=30,
    )


if __name__ == "__main__":
    main()
