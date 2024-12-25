import time
from datetime import datetime, timedelta
import pytz
from image_generator import ImageGenerator

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

    def update_stats(self):
        current_time = datetime.now(pytz.timezone('Asia/Novosibirsk'))
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
            f"⚡️ Энергия: {self.energy}/4"
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