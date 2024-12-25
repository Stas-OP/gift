import logging
import json
import ssl
import certifi
import urllib3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from cat import Cat

# Отключаем предупреждения SSL
urllib3.disable_warnings()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Функции для работы с данными
def load_cats():
    try:
        with open('cats_data.json', 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
                loaded_cats = {}
                for user_id, cat_data in data.items():
                    cat = Cat(
                        cat_data['name'],
                        cat_data.get('color', 'серый'),
                        cat_data.get('owner_m', 'Стас'),
                        cat_data.get('owner_f', 'Маша'),
                        cat_data.get('created_at')
                    )
                    cat.hunger = cat_data['hunger']
                    cat.happiness = cat_data['happiness']
                    cat.energy = cat_data['energy']
                    cat.last_update = cat_data['last_update']
                    loaded_cats[int(user_id)] = cat
                return loaded_cats
            except json.JSONDecodeError:
                return {}
    except FileNotFoundError:
        with open('cats_data.json', 'w', encoding='utf-8') as file:
            json.dump({}, file)
        return {}

def save_cats():
    data = {}
    for user_id, cat in cats.items():
        data[user_id] = {
            'name': cat.name,
            'color': cat.color,
            'owner_m': cat.owner_m,
            'owner_f': cat.owner_f,
            'hunger': cat.hunger,
            'happiness': cat.happiness,
            'energy': cat.energy,
            'last_update': cat.last_update,
            'created_at': cat.created_at
        }
    with open('cats_data.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4, default=str)

# Загружаем данные при запуске
cats = load_cats()

# Добавляем состояния для диалога создания котика
CHOOSING_NAME, CHOOSING_COLOR = range(2)

# Изменяем список цветов на более компактный
CAT_COLORS = {
    "Серый": "серый",
    "Белый": "белый",
    "Рыжий": "рыжий",
    "Чёрный": "чёрный"
}

# Добавим словарь склонений цветов
COLOR_CASES = {
    "серый": "серого",
    "белый": "белого",
    "рыжий": "рыжего",
    "чёрный": "чёрного"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in cats:
        await update.message.reply_text(
            "Давайте создадим котика! Как вы хотите его назвать?",
            reply_markup=ReplyKeyboardRemove()
        )
        return CHOOSING_NAME
    else:
        await update.message.reply_text("У вас уже есть котик! 🐱")
        await show_main_menu(update, context)
        return ConversationHandler.END

async def choose_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cat_name'] = update.message.text
    
    # Создаем инлайн клавиатуру с цветами и сердечками
    keyboard = [
        [
            InlineKeyboardButton("Серый 🤍", callback_data='color_серый'),
            InlineKeyboardButton("Белый 🤍", callback_data='color_белый')
        ],
        [
            InlineKeyboardButton("Рыжий 🤍", callback_data='color_рыжий'),
            InlineKeyboardButton("Чёрный 🖤", callback_data='color_чёрный')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Отличное имя! Выберите цвет вашего котика:",
        reply_markup=reply_markup
    )
    return CHOOSING_COLOR

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Создаем клавиатуру один раз в начале функции
    keyboard = [
        [
            InlineKeyboardButton("Покормить 🍽", callback_data='feed'),
            InlineKeyboardButton("Поиграть 🎮", callback_data='play')
        ],
        [
            InlineKeyboardButton("Уложить спать 😴", callback_data='sleep'),
            InlineKeyboardButton("Статус 📊", callback_data='status')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Создаем клавиатурную кнопку
    keyboard_button = ReplyKeyboardMarkup(
        [["🐱 Управление котиком"]], 
        resize_keyboard=True
    )
    
    # Обработка выбора цвета
    if query.data.startswith('color_'):
        if 'cat_name' not in context.user_data:
            await query.message.edit_text("Что-то пошло не так. Попробуйте начать сначала с /start")
            return ConversationHandler.END
            
        color = query.data.replace('color_', '')
        cats[user_id] = Cat(context.user_data['cat_name'], color)
        save_cats()
        
        await query.message.edit_text(
            f"Поздравляем! {color.capitalize()} котик {context.user_data['cat_name'].capitalize()} появился у вас! 🐱",
            reply_markup=keyboard_button
        )
        await show_main_menu(update, context)
        return ConversationHandler.END
    
    if user_id not in cats:
        await query.message.edit_text("У вас пока нет котика! Используйте /start чтобы завести котика.")
        return

    cat = cats[user_id]
    cat.update_stats()  # Обновляем статистику
    
    # Удаляем предыдущее сообщение
    try:
        await query.message.delete()
    except:
        pass

    # Обрабатываем действия
    message = ""
    if query.data == 'feed':
        message = cat.feed()
    elif query.data == 'play':
        message = cat.play()
    elif query.data == 'sleep':
        message = cat.sleep()
    elif query.data == 'status':
        message = "Статус вашего котика:"
    
    # Генерируем изображение со статусом
    image_path = cat.get_status_image()
    
    # Отправляем новое сообщение с фото
    await query.message.reply_photo(
        photo=open(image_path, 'rb'),
        caption=f"{message}\nЧто будем делать дальше?",
        reply_markup=reply_markup
    )
    
    save_cats()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Создание котика отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("��окормить 🍽", callback_data='feed'),
            InlineKeyboardButton("Поиграть 🎮", callback_data='play')
        ],
        [
            InlineKeyboardButton("Уложить спать 😴", callback_data='sleep'),
            InlineKeyboardButton("Статус 📊", callback_data='status')
        ]
    ]
    inline_markup = InlineKeyboardMarkup(keyboard)
    
    # Создаем клавиатурную кнопку
    keyboard_button = ReplyKeyboardMarkup(
        [["🐱 Управление котиком"]], 
        resize_keyboard=True
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text="Что будем делать с котиком?",
            reply_markup=inline_markup
        )
        # Добавляем клавиатурную кнопку без дополнительного сообщения
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="",
            reply_markup=keyboard_button
        )
    else:
        # Отправляем одно сообщение с инлайн кнопками и добавляем клавиатурную кнопку
        await update.message.reply_text(
            text="Что будем делать с котиком?",
            reply_markup=inline_markup
        )
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="",
            reply_markup=keyboard_button
        )

# Добавляем обработчик для клавиатурной кнопки
async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🐱 Управление котиком":
        user_id = update.effective_user.id
        if user_id not in cats:
            await update.message.reply_text("У вас пока нет котика! Используйте /start чтобы завести котика.")
            return

        cat = cats[user_id]
        cat.update_stats()
        
        # Создаем клавиатуру
        keyboard = [
            [
                InlineKeyboardButton("Покормить 🍽", callback_data='feed'),
                InlineKeyboardButton("Поиграть 🎮", callback_data='play')
            ],
            [
                InlineKeyboardButton("Уложить спать 😴", callback_data='sleep'),
                InlineKeyboardButton("Статус 📊", callback_data='status')
            ]
        ]
        inline_markup = InlineKeyboardMarkup(keyboard)
        
        # Генерируем изображение со статусом
        image_path = cat.get_status_image()
        
        # Отправляем сообщение с фото и меню
        await update.message.reply_photo(
            photo=open(image_path, 'rb'),
            caption="Что будем делать с котиком?",
            reply_markup=inline_markup
        )

def main():
    # Создаем приложение
    application = Application.builder()\
        .token('7817658003:AAEnIHuifYCCoV7oXiSU-1tneodSh6EzNDU')\
        .build()

    # Создаем обработчик диалога создания котика
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_name)],
            CHOOSING_COLOR: [CallbackQueryHandler(button_handler, pattern='^color_')],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_button))

    # Запускаем бота
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()