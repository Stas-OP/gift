import time
from datetime import datetime, timedelta
import pytz
from image_generator import ImageGenerator
import logging

class Cat:
    def __init__(self, name, color="серый", owner_m="Стас", owner_f="Маша", created_at=None):
        self.name = name
        self.color = color
        self.owner_m = owner_m
        self.owner_f = owner_f
        self.hunger = 4  # 0-4 делений
        self.happiness = 4  # 0-4 делений
        self.energy = 4  # 0-4 делений
        self.last_update = datetime.now(pytz.timezone('Asia/Novosibirsk')).isoformat()
        self.created_at = created_at or datetime.now(pytz.timezone('Asia/Novosibirsk')).isoformat()
        self.image_generator = ImageGenerator()
        self.walk_time = None  # Время прогулки в формате HH:MM
        self.last_walk_notification = None  # Время последнего напоминания

    def set_walk_time(self, time_str):
        """Установить время прогулки"""
        try:
            # Пробуем разные форматы времени
            if '.' in time_str:
                # Формат XX.XX
                hour, minute = map(int, time_str.split('.'))
            elif ':' in time_str:
                # Формат XX:XX
                hour, minute = map(int, time_str.split(':'))
            else:
                # Формат XX или X (только час)
                hour = int(time_str)
                minute = 0
            
            # Проверяем корректность времени
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return False
            
            # Форматируем время в стандартный формат
            self.walk_time = f"{hour:02d}:{minute:02d}"
            self.last_walk_notification = None
            return True
        except (ValueError, TypeError):
            return False

    def get_walk_time(self):
        """Получить время прогулки"""
        return self.walk_time

    def should_notify(self, current_time):
        """Проверить, нужно ли отправить напоминание о прогулке"""
        if not self.walk_time:
            return None

        # Парсим время прогулки и добавляем часовой пояс
        walk_time = datetime.strptime(self.walk_time, "%H:%M").time()
        tz = pytz.timezone('Asia/Novosibirsk')
        walk_datetime = tz.localize(datetime.combine(current_time.date(), walk_time))
        
        # Если время прогулки уже прошло сегодня, не отправляем напоминания
        if current_time.time() > walk_time:
            return None

        time_diff = walk_datetime - current_time
        minutes_until_walk = time_diff.total_seconds() / 60

        logging.info(f"Checking notifications for {self.name}:")
        logging.info(f"Current time: {current_time}")
        logging.info(f"Walk time: {walk_time}")
        logging.info(f"Minutes until walk: {minutes_until_walk}")
        logging.info(f"Last notification: {self.last_walk_notification}")

        # Проверяем, нужно ли отправить уведомление
        if -1 <= minutes_until_walk <= 1:  # Точно время (с погрешностью в 1 минуту)
            if not self.last_walk_notification or \
                (current_time - tz.localize(datetime.fromisoformat(self.last_walk_notification))).total_seconds() > 60:
                self.last_walk_notification = current_time.isoformat()
                logging.info("Sending time to go notification")
                return "time_to_go"
        elif 59 <= minutes_until_walk <= 61:  # За час
            if not self.last_walk_notification or \
                (current_time - tz.localize(datetime.fromisoformat(self.last_walk_notification))).total_seconds() > 3600:
                self.last_walk_notification = current_time.isoformat()
                logging.info("Sending hour notification")
                return "hour"
        elif 29 <= minutes_until_walk <= 31:  # За полчаса
            if not self.last_walk_notification or \
                (current_time - tz.localize(datetime.fromisoformat(self.last_walk_notification))).total_seconds() > 1800:
                self.last_walk_notification = current_time.isoformat()
                logging.info("Sending half hour notification")
                return "half_hour"
        elif 9 <= minutes_until_walk <= 11:  # За 10 минут
            if not self.last_walk_notification or \
                (current_time - tz.localize(datetime.fromisoformat(self.last_walk_notification))).total_seconds() > 600:
                self.last_walk_notification = current_time.isoformat()
                logging.info("Sending 10 minutes notification")
                return "ten_minutes"
        
        return None

    def update_stats(self):
        current_time = datetime.now(pytz.timezone('Asia/Novosibirsk'))
        if not self.last_update:
            self.last_update = current_time.isoformat()
            return

        time_diff = current_time - datetime.fromisoformat(self.last_update)
        hours_passed = time_diff.total_seconds() / 3600

        # Обновляем только если прошло 6 или более часов
        if hours_passed >= 6:
            # Не уменьшаем характеристики ночью (с 22:00 до 6:00)
            current_hour = current_time.hour
            if not (22 <= current_hour or current_hour < 6):
                periods_passed = int(hours_passed / 6)
                
                self.hunger = max(0, self.hunger - periods_passed)
                self.happiness = max(0, self.happiness - periods_passed)
                self.energy = max(0, self.energy - periods_passed)
            
            self.last_update = current_time.isoformat()

    def get_status(self):
        self.update_stats()
        return (
            f"{self.color.capitalize()} котик {self.name.capitalize()}:\n"
            f"🍽 Сытость: {self.hunger}/4\n"
            f"😊 Счастье: {self.happiness}/4\n"
            f"⚡ Энергия: {self.energy}/4"
        )

    def feed(self):
        if self.hunger >= 4:
            return f"Котик {self.name} не голоден!"
        self.hunger = min(4, self.hunger + 1)
        return f"Вы покормили котика {self.name}!"

    def play(self):
        if self.happiness >= 4:
            return f"Котик {self.name} не хочет играть!"
        if self.energy <= 1:
            return f"Котик {self.name} слишком устал для игр!"
        self.happiness = min(4, self.happiness + 1)
        self.energy = max(0, self.energy - 1)
        return f"Вы поиграли с котиком {self.name}!"

    def sleep(self):
        self.update_stats()
        if self.energy >= 4:
            return "Котик не хочет спать! 👀"
        self.energy = min(4, self.energy + 1)
        return f"Котик {self.name} поспал и восстановил силы!"

    def get_status_image(self):
        self.update_stats()
        return self.image_generator.generate_status_image(
            self.color,
            self.name,
            self.hunger,
            self.happiness,
            self.energy,
            self.owner_m,
            self.owner_f,
            self.get_age_days()
        )

    def get_age_days(self):
        created = datetime.fromisoformat(self.created_at)
        if not created.tzinfo:
            created = pytz.timezone('Asia/Novosibirsk').localize(created)
        now = datetime.now(pytz.timezone('Asia/Novosibirsk'))
        days = (now - created).days
        return max(1, days)  # Возвращаем минимум 1 день