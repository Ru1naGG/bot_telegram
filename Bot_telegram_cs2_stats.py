import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

# === Настройки ===
FACEIT_API_KEY = '17fce2fa-3338-48de-a6d8-b2c99f4afb04'
TELEGRAM_BOT_TOKEN = '7823250492:AAEqzS75f4ppllinfx0hppdOIly8VWnbhkM'

# === Состояния ===
SELECT_LANGUAGE, MAIN_MENU, ENTER_NICKNAME = range(3)


HEADERS = {'Authorization': f'Bearer {FACEIT_API_KEY}'}

# Память для хранения языка пользователя
user_language = {}

# === Тексты интерфейса ===
TEXTS = {
    'start': {
        'ru': "👋 Привет! Выберите язык:",
        'en': "👋 Hello! Choose your language:"
    },
    'main_menu': {
        'ru': "📋 Что вы хотите сделать?",
        'en': "📋 What would you like to do?"
    },
    'menu_buttons': {
        'ru': [
            ("📊 Статистика игрока", 'stats'),
            ("🌍 Регион", 'region'),
            ("🏆 Турниры", 'tournaments'),
            ("🧑‍💻 Топ 200", 'top'),
            ("💸 Донат", 'donate')
        ],
        'en': [
            ("📊 Player Stats", 'stats'),
            ("🌍 Region", 'region'),
            ("🏆 Tournaments", 'tournaments'),
            ("🧑‍💻 Top 200", 'top'),
            ("💸 Donate", 'donate')
        ]
    },
    'enter_nickname': {
        'ru': "🔎 Введите никнейм игрока FACEIT для CS2:",
        'en': "🔎 Enter the FACEIT nickname for CS2:"
    },
    'donate': {
        'ru': "💸 Поддержать проект можно здесь:\nhttps://www.donationalerts.com/r/ru1na__",
        'en': "💸 You can support the project here:\nhttps://www.donationalerts.com/r/ru1na__"
    },
    'feature_coming': {
        'ru': "🚧 Функция скоро будет доступна.",
        'en': "🚧 Feature coming soon."
    },
    'back': {
        'ru': "↩ Назад в меню",
        'en': "↩ Back to menu"
    }
}

# === Обработка команды /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(TEXTS['start']['ru'], reply_markup=reply_markup)
    return SELECT_LANGUAGE

# === Обработка выбора языка ===
async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    user_language[query.from_user.id] = lang
    await send_main_menu(query.from_user.id, context, edit=True, query=query)
    return MAIN_MENU

# === Главное меню ===
async def send_main_menu(user_id, context: ContextTypes.DEFAULT_TYPE, edit=False, query=None):
    lang = user_language.get(user_id, 'en')
    text = TEXTS['main_menu'][lang]
    buttons = TEXTS['menu_buttons'][lang]
    keyboard = [[InlineKeyboardButton(txt, callback_data=data)] for txt, data in buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit and query:
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)

# === Обработка кнопок меню ===
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_language.get(user_id, 'en')

    if query.data == 'stats':
        await query.edit_message_text(TEXTS['enter_nickname'][lang], reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(TEXTS['back'][lang], callback_data='back_to_menu')]
        ]))
        return ENTER_NICKNAME

    elif query.data == 'donate':
        await query.edit_message_text(TEXTS['donate'][lang], reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(TEXTS['back'][lang], callback_data='back_to_menu')]
        ]))
        return MAIN_MENU

    else:
        await query.edit_message_text(TEXTS['feature_coming'][lang], reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(TEXTS['back'][lang], callback_data='back_to_menu')]
        ]))
        return MAIN_MENU

# === Обработка кнопки "Назад в меню" ===
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_main_menu(query.from_user.id, context, edit=True, query=query)
    return MAIN_MENU

# === Ввод никнейма и вывод статистики ===
async def handle_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_language.get(user_id, 'en')
    nickname = update.message.text.strip()

    avatar_url, stats_text = get_faceit_player_data(nickname, lang)

    if avatar_url:
        await update.message.reply_photo(avatar_url)

    await update.message.reply_text(stats_text)

    await send_main_menu(user_id, context)
    return MAIN_MENU

# === Получение статистики с FACEIT API ===
def get_faceit_player_data(nickname, lang='en', game='cs2'):
    try:
        player_url = f'https://open.faceit.com/data/v4/players?nickname={nickname}'
        player_resp = requests.get(player_url, headers=HEADERS)
        if player_resp.status_code != 200:
            msg = "❌ Player not found." if lang == 'en' else "❌ Игрок не найден."
            return None, msg

        player_data = player_resp.json()
        player_id = player_data['player_id']

        stats_url = f'https://open.faceit.com/data/v4/players/{player_id}/stats/{game}'
        stats_resp = requests.get(stats_url, headers=HEADERS)
        if stats_resp.status_code != 200:
            msg = "⚠️ Could not retrieve stats." if lang == 'en' else "⚠️ Не удалось получить статистику."
            return None, msg

        stats_data = stats_resp.json()
        lifetime = stats_data.get('lifetime', {})

        if lang == 'ru':
            text = (
                f"📊 Статистика игрока: {player_data['nickname']} ({game.upper()})\n"
                f"🌍 Страна: {player_data.get('country')}\n"
                f"📈 Уровень FACEIT: {player_data['games'][game]['skill_level']}\n"
                f"⭐️ ELO: {player_data['games'][game]['faceit_elo']}\n"
                f"🎮 Матчей сыграно: {lifetime.get('Matches')}\n"
                f"✅ Побед: {lifetime.get('Wins')}\n"
                f"🏆 Win Rate: {lifetime.get('Win Rate %')}%\n"
                f"🔫 K/D: {lifetime.get('Average K/D Ratio')}\n"
                f"🎯 HS %: {lifetime.get('Average Headshots %')}\n"
                f"🔥 Серия побед: {lifetime.get('Longest Win Streak')}\n"
                f"🔗 Профиль: https://www.faceit.com/ru/players/{player_data['nickname']}"
            )
        else:
            text = (
                f"📊 Player Stats: {player_data['nickname']} ({game.upper()})\n"
                f"🌍 Country: {player_data.get('country')}\n"
                f"📈 FACEIT Level: {player_data['games'][game]['skill_level']}\n"
                f"⭐️ ELO: {player_data['games'][game]['faceit_elo']}\n"
                f"🎮 Matches played: {lifetime.get('Matches')}\n"
                f"✅ Wins: {lifetime.get('Wins')}\n"
                f"🏆 Win Rate: {lifetime.get('Win Rate %')}%\n"
                f"🔫 K/D: {lifetime.get('Average K/D Ratio')}\n"
                f"🎯 HS %: {lifetime.get('Average Headshots %')}\n"
                f"🔥 Win Streak: {lifetime.get('Longest Win Streak')}\n"
                f"🔗 Profile: https://www.faceit.com/en/players/{player_data['nickname']}"
            )

        avatar = player_data.get('avatar')
        return avatar, text

    except Exception as e:
        return None, f"❗ Error: {e}" if lang == 'en' else f"❗ Ошибка: {e}"

# === Запуск бота ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_LANGUAGE: [CallbackQueryHandler(select_language)],
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_handler, pattern='^(stats|region|tournaments|top|donate)$'),
                CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$')
            ],
            ENTER_NICKNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nickname),
                CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$')
            ],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    print("🤖 Бот запущен.")
    app.run_polling()

if __name__ == '__main__':
    main()
