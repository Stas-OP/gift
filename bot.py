import logging
import json
import ssl
import certifi
import urllib3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from cat import Cat
from datetime import datetime
import pytz

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
                    cat.walk_time = cat_data.get('walk_time')
                    cat.last_walk_notification = cat_data.get('last_walk_notification')
                    cat.last_love_message = cat_data.get('last_love_message')
                    cat.love_message_time = cat_data.get('love_message_time')
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
            'created_at': cat.created_at,
            'walk_time': cat.walk_time,
            'last_walk_notification': cat.last_walk_notification,
            'last_love_message': cat.last_love_message,
            'love_message_time': cat.love_message_time
        }
    with open('cats_data.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4, default=str)

# Загружаем данные при запуске
cats = load_cats()

# Добавляем состояния для диалога создания котика
CHOOSING_NAME, CHOOSING_COLOR, SETTING_WALK_TIME = range(3)

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
            "Давайте соз��адим котика! Как вы хотите его назвать?",
            reply_markup=ReplyKeyboardRemove()
        )
        return CHOOSING_NAME
    else:
        await update.message.reply_text("У вас уже есть котик! 🐱")
        await show_main_menu(update, context)
        return ConversationHandler.END

async def choose_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cat_name'] = update.message.text
    
    # Создаем инлайн клавиатуру с цветами и квадратиками
    keyboard = [
        [
            InlineKeyboardButton("Серый ⬜️", callback_data='color_серый'),
            InlineKeyboardButton("Белый ⬜️", callback_data='color_белый')
        ],
        [
            InlineKeyboardButton("Рыжий 🟧", callback_data='color_рыжий'),
            InlineKeyboardButton("Чёрный ⬛️", callback_data='color_чёрный')
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
    
    # Обработка удаления времени прогулки
    if query.data == 'remove_walk_time':
        if user_id not in cats:
            await query.message.edit_text("У вас пока нет котика! Используйте /start чтобы завести котика.")
            return
        
        cat = cats[user_id]
        if cat.remove_walk_time():
            save_cats()
            await query.message.delete()
            
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
            await context.bot.send_message(
                chat_id=user_id,
                text="Время прогулки удалено!"
            )
            await context.bot.send_photo(
                chat_id=user_id,
                photo=open(image_path, 'rb'),
                caption="Что будем делать с котиком?",
                reply_markup=inline_markup
            )
            return ConversationHandler.END
    
    # Обработка кнопки "Вернуться назад"
    if query.data == 'back_to_menu':
        # Удаляем сообщение с вводом времени
        await query.message.delete()
        
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
        cat = cats[user_id]
        image_path = cat.get_status_image()
        
        # Отправляем сообщение с фото и меню
        await query.message.reply_photo(
            photo=open(image_path, 'rb'),
            caption="Что будем делать с котиком?",
            reply_markup=inline_markup
        )
        return ConversationHandler.END
    
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
    inline_markup = InlineKeyboardMarkup(keyboard)
    
    # Создаем клавиатурную кнопку
    keyboard_button = ReplyKeyboardMarkup(
        [
            ["🐱 Управление котиком", "⏰ Установить время прогулки"]
        ], 
        resize_keyboard=True
    )
    
    # Обработка установки времени прогулки
    if query.data == 'set_walk_time':
        await query.message.edit_text(
            "Введите время прогулки в формате ЧЧ:ММ (например, 14:30):"
        )
        return SETTING_WALK_TIME

    # Обработка выбора цвета
    if query.data.startswith('color_'):
        if 'cat_name' not in context.user_data:
            await query.message.edit_text(
                "Что-то пошло не так. Попробуйте начать сначала с /start",
                reply_markup=InlineKeyboardMarkup([[]])
            )
            return ConversationHandler.END
            
        color = query.data.replace('color_', '')
        cats[user_id] = Cat(context.user_data['cat_name'], color)
        save_cats()
        
        # Сначала отправляем сообщение с клавиатурной кнопкой
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Поздравляем! {color.capitalize()} котик {context.user_data['cat_name'].capitalize()} появился у вас! 🐱",
            reply_markup=keyboard_button
        )
        
        # Удаляем сообщение с в��бором цвета
        await query.message.delete()
        
        # Показываем основное меню
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
    
    # Гнерируем изображение со статусом
    image_path = cat.get_status_image()
    
    # Отправляем новое сообщение с фото
    await query.message.reply_photo(
        photo=open(image_path, 'rb'),
        caption=f"{message}\nЧто будем делать дальше?",
        reply_markup=inline_markup
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
            InlineKeyboardButton("Покормить 🍽", callback_data='feed'),
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
        [
            ["🐱 Управление котиком", "⏰ Установить время прогулки"]
        ], 
        resize_keyboard=True
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text="Что будем делать с котиком?",
            reply_markup=inline_markup
        )
        # Д��бавляем клавиатурную кнопку без дополнительного сообщения
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
        
        # Создаем клавиа��уру
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
    elif update.message.text == "⏰ Установить время прогулки":
        user_id = update.effective_user.id
        if user_id not in cats:
            await update.message.reply_text("У вас пока нет котика! Используйте /start чтобы завести котика.")
            return
        
        cat = cats[user_id]
        keyboard = []
        
        # Если время прогулки уже установлено, показываем кнопку удаления
        if cat.walk_time:
            keyboard.append([InlineKeyboardButton("❌ Удалить время прогулки", callback_data='remove_walk_time')])
        
        keyboard.append([InlineKeyboardButton("↩️ Вернуться назад", callback_data='back_to_menu')])
        inline_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем текущее время
        current_time = datetime.now(pytz.timezone('Asia/Novosibirsk')).strftime("%H:%M")
        message_text = f"Текущее время: {current_time}\n\n"
        
        if cat.walk_time:
            message_text += f"Текущее время прогулки: {cat.walk_time}\n\n"
            
        message_text += ("Введите время прогулки в любом удобном формате:\n"
            "• ЧЧ:ММ (например, 14:30)\n"
            "• ЧЧ.ММ (например, 14.30)\n"
            "• ЧЧ или Ч (например, 14 или 9 - будет установлено начало часа)")
        
        await update.message.reply_text(
            message_text,
            reply_markup=inline_markup
        )
        return SETTING_WALK_TIME

async def set_walk_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in cats:
        await update.message.reply_text("У вас пока нет котика!")
        return ConversationHandler.END

    time_str = update.message.text
    cat = cats[user_id]
    
    if cat.set_walk_time(time_str):
        save_cats()  # Сохраняем изменения
        # Получаем текущее время
        current_time = datetime.now(pytz.timezone('Asia/Novosibirsk')).strftime("%H:%M")
        # Отправляем сообщение о создании напоминания
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Текущее время: {current_time}\n"
                 f"Время прогулки установлено на {cat.walk_time}! Я напомню за час и за полчаса до прогулки."
        )
        
        # Генерируем изображение со статусом
        image_path = cat.get_status_image()
        
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
        
        # Отправляем сообщение с фото и меню
        await update.message.reply_photo(
            photo=open(image_path, 'rb'),
            caption="Что будем делать с котиком?",
            reply_markup=inline_markup
        )
        return ConversationHandler.END
    else:
        # Получаем текущее время
        current_time = datetime.now(pytz.timezone('Asia/Novosibirsk')).strftime("%H:%M")
        await update.message.reply_text(
            f"Текущее время: {current_time}\n\n"
            "Пожалуйста, введите время в одном из форматов:\n"
            "• ЧЧ:ММ (например, 14:30)\n"
            "• ЧЧ.ММ (например, 14.30)\n"
            "• ЧЧ или Ч (например, 14 или 9 - будет установлено начало часа)"
        )
        return SETTING_WALK_TIME

async def check_walk_notifications(context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.now(pytz.timezone('Asia/Novosibirsk'))
    logging.info(f"Checking notifications at {current_time}")
    
    for user_id, cat in cats.items():
        try:
            logging.info(f"Checking cat {cat.name} for user {user_id}")
            
            # Проверяем напоминания о прогулке
            notification = cat.should_notify(current_time)
            if notification == "time_to_go":
                logging.info(f"Sending time to go notification to user {user_id}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🚶‍♀️ Пора выходить на прогулку!"
                )
                save_cats()
            elif notification == "hour":
                logging.info(f"Sending hour notification to user {user_id}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🚶‍♂️ Через час пора на прогулку! (в {cat.walk_time})"
                )
                save_cats()
            elif notification == "half_hour":
                logging.info(f"Sending half hour notification to user {user_id}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🚶‍♂️ Через полчаса пора на прогулку! (в {cat.walk_time})"
                )
                save_cats()
            elif notification == "ten_minutes":
                logging.info(f"Sending 10 minutes notification to user {user_id}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🚶‍♂️ Через 10 минут пора на прогулку! (в {cat.walk_time})"
                )
                save_cats()
            
            # Проверяем, не пора ли отправить сообщение о любви
            if cat.should_send_love(current_time):
                logging.info(f"Sending love message to user {user_id}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=cat.get_love_message()
                )
                
        except Exception as e:
            logging.error(f"Ошибка при отправке напоминания: {str(e)}")
            logging.exception("Полная информация об ошибке:")

def main():
    # Создаем приложение
    application = Application.builder()\
        .token('7817658003:AAEnIHuifYCCoV7oXiSU-1tneodSh6EzNDU')\
        .build()

    # Создаем обработчик диалога создания котика
    create_cat_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_name)],
            CHOOSING_COLOR: [CallbackQueryHandler(button_handler, pattern='^color_')],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Создаем отдельный обработчик для установки времени прогулки
    walk_time_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^⏰ Установить время прогулки$"), handle_keyboard_button)],
        states={
            SETTING_WALK_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_walk_time),
                CallbackQueryHandler(button_handler, pattern='^back_to_menu$'),
                CallbackQueryHandler(button_handler, pattern='^remove_walk_time$')
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Добавляем обработчики
    application.add_handler(create_cat_handler)
    application.add_handler(walk_time_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🐱 Управление котиком$"), handle_keyboard_button))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^⏰ Установить время прогулки$"), handle_keyboard_button))

    # Добавляем задачу проверки напоминаний каждую минуту
    job_queue = application.job_queue
    job_queue.run_repeating(check_walk_notifications, interval=60)

    # Запускаем бота
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()