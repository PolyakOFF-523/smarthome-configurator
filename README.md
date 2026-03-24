# SmartHome Конфигуратор

Веб-сервис для проектирования и подбора комплектующих систем «умного дома».

## 🚀 Функционал

- Подбор сборки под параметры квартиры (комнаты, площадь)
- 3 готовых сегмента: Эконом, Стандарт, Премиум + своя сборка
- Проверка совместимости устройств (протоколы, радиус, питание)
- Модерация пользовательских сборок
- Публичный каталог сборок с лайками и просмотрами
- Тёмная/светлая тема с сохранением выбора
- Теги устройств (для кухни, энергоэффективное, бюджетное)

## 🛠 Технологии

- Python 3.12
- Django 6.0
- SQLite
- Bootstrap 5

## 📦 Установка и запуск

```bash
git clone https://github.com/PolyakOFF-523/smarthome-configurator.git
cd smarthome-configurator
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata catalog/fixtures/initial_data.json
python manage.py createsuperuser
python manage.py runserver

