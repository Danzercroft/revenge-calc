# Revenge Calculator FastAPI

Стандартный проект FastAPI с подключением к PostgreSQL базе данных.

## ✨ Функции

- ✅ FastAPI с автоматической документацией (Swagger UI / ReDoc)
- ✅ CORS middleware для кросс-доменных запросов
- ✅ Подключение к PostgreSQL базе данных
- ✅ Health check endpoint
- ✅ Database status endpoint для проверки соединения с БД
- ✅ Автоматические тесты с pytest
- ✅ Конфигурация VS Code (задачи, отладка, настройки)
- ✅ Docker поддержка
- ✅ Готов к разработке и продакшену

## 🚀 Быстрый старт

## 🚀 Быстрый старт

### Локальная разработка

1. **Создайте виртуальное окружение:**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
pip install -r dev-requirements.txt  # для разработки
```

3. **Запустите приложение:**
```bash
uvicorn main:app --reload
# или
python main.py
```

### Использование VS Code

Если вы используете VS Code, вы можете:
- Нажать `Ctrl+Shift+P` → "Tasks: Run Task" → "Start FastAPI Server"
- Или нажать `F5` для запуска в режиме отладки

### Docker

```bash
# Сборка образа
docker build -t revenge-calc-api .

# Запуск контейнера
docker run -p 8000:8000 revenge-calc-api
```

## 📖 API Документация

После запуска приложение будет доступно по адресу: **http://localhost:8000**

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## 🛠 Разработка

## 🛠 Разработка

### Запуск в режиме разработки
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Тестирование
```bash
# Запуск всех тестов
pytest

# Запуск с подробным выводом
pytest -v

# Запуск конкретного теста
pytest test_main.py::test_read_root -v
```

### Структура проекта
```
revenge-calc/
├── main.py              # Основное приложение FastAPI
├── database.py          # Конфигурация подключения к PostgreSQL
├── test_main.py         # Тесты
├── requirements.txt     # Зависимости продакшена
├── dev-requirements.txt # Зависимости для разработки
├── Dockerfile          # Docker конфигурация
├── .dockerignore        # Исключения для Docker
├── .gitignore          # Git исключения
├── .env.example        # Пример переменных окружения
├── .vscode/            # Конфигурация VS Code
│   ├── launch.json     # Конфигурация отладки
│   ├── settings.json   # Настройки проекта
│   └── tasks.json      # Задачи автоматизации
└── README.md           # Документация
```

## 🗄 База данных

Проект настроен для работы с PostgreSQL базой данных:
- **Host:** localhost:5432
- **User:** revenge_user
- **Password:** revenge_password
- **Database:** revenge

Убедитесь, что PostgreSQL сервер запущен и база данных создана с указанными учетными данными.

## 🔗 Endpoints

- `GET /` - Корневой endpoint (приветствие)
- `GET /health` - Health check
- `GET /db-status` - Проверка статуса подключения к базе данных

## 🤝 Вклад в проект

1. Сделайте форк проекта
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add some amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.
