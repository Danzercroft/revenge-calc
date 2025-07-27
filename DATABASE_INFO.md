# Информация о базе данных

## Конфигурация PostgreSQL

Проект настроен для подключения к PostgreSQL базе данных со следующими параметрами:

- **Host:** localhost
- **Port:** 5432
- **Database:** revenge
- **Username:** revenge_user
- **Password:** revenge_password

## Проверка подключения

Вы можете проверить статус подключения к базе данных через API endpoint:

```bash
curl http://localhost:8000/db-status
```

Ответ при успешном подключении:
```json
{
  "database": "connected",
  "status": "healthy"
}
```

## Изменение конфигурации

Для изменения параметров подключения к базе данных:

1. Создайте файл `.env` в корне проекта
2. Добавьте переменную окружения `DATABASE_URL`:

```env
DATABASE_URL=postgresql://username:password@host:port/database_name
```

Пример:
```env
DATABASE_URL=postgresql://my_user:my_password@localhost:5432/my_database
```

## Расширение функциональности

Для добавления моделей и CRUD операций:

1. Создайте файл `models.py` с SQLAlchemy моделями
2. Создайте файл `schemas.py` с Pydantic схемами  
3. Создайте файл `crud.py` с операциями базы данных
4. Импортируйте и используйте в `main.py`

Текущая конфигурация предоставляет только базовое подключение к базе данных без создания таблиц или CRUD операций.
