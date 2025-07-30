# Тестирование проекта Revenge Calculator

Этот проект содержит комплексный набор тестов для всех компонентов системы сбора данных о криптовалютных рынках.

## Структура тестов

### Типы тестов

1. **Unit тесты** - тестируют отдельные компоненты в изоляции
2. **Integration тесты** - тестируют взаимодействие между компонентами  
3. **API тесты** - тестируют HTTP endpoints
4. **Database тесты** - тестируют модели данных и взаимодействие с БД

### Тестовые файлы

- `test_main.py` - тесты для FastAPI приложения и API endpoints
- `test_models.py` - тесты для моделей базы данных SQLAlchemy
- `test_data_collection_service.py` - тесты для сервиса сбора данных
- `test_exchange_service.py` - тесты для сервиса работы с биржами
- `conftest.py` - общие фикстуры для всех тестов
- `pytest.ini` - конфигурация pytest

## Установка зависимостей

```bash
# Установка зависимостей для разработки
pip install -r dev-requirements.txt

# Или через Makefile
make install-dev
```

## Запуск тестов

### Основные команды

```bash
# Запустить все тесты
pytest

# Запустить все тесты с подробным выводом
pytest -v

# Запустить тесты с покрытием кода
pytest --cov=. --cov-report=html

# Запустить быстрые тесты (исключая медленные)
pytest -m "not slow"
```

### Запуск через Makefile

```bash
# Все тесты
make test

# Только unit тесты
make test-unit

# Только интеграционные тесты  
make test-integration

# Только API тесты
make test-api

# Только тесты базы данных
make test-db

# Тесты с покрытием кода
make test-coverage

# Быстрые тесты
make test-fast

# Медленные тесты
make test-slow
```

### Запуск конкретных тестовых файлов

```bash
# Тесты API
make test-main
pytest test_main.py -v

# Тесты моделей
make test-models
pytest test_models.py -v

# Тесты сервиса сбора данных
make test-data-collection
pytest test_data_collection_service.py -v

# Тесты сервиса бирж
make test-exchange
pytest test_exchange_service.py -v
```

### Запуск через VS Code задачи

В VS Code доступны предустановленные задачи:

1. **Run Tests** - запускает все тесты
2. **Start FastAPI Server** - запускает сервер
3. **Install Dependencies** - устанавливает зависимости

Для запуска задач:
- `Ctrl+Shift+P` → "Tasks: Run Task"
- Или используйте команду: `make run-task-tests`

## Маркеры тестов

Тесты помечены специальными маркерами для гибкого запуска:

- `@pytest.mark.unit` - unit тесты
- `@pytest.mark.integration` - интеграционные тесты
- `@pytest.mark.api` - API тесты
- `@pytest.mark.database` - тесты базы данных
- `@pytest.mark.slow` - медленные тесты
- `@pytest.mark.asyncio` - асинхронные тесты

```bash
# Запуск по маркерам
pytest -m unit           # только unit тесты
pytest -m "api or database"  # API или database тесты
pytest -m "not slow"     # все кроме медленных
```

## Покрытие кода

Генерация отчета о покрытии кода:

```bash
# HTML отчет (откроется в браузере)
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Отчет в терминале
pytest --cov=. --cov-report=term-missing

# Через Makefile
make test-coverage
```

## Мокирование

Тесты используют обширное мокирование для изоляции компонентов:

- **CCXT биржи** - мокируются для избежания реальных API вызовов
- **База данных** - используется SQLite в памяти для тестов
- **Планировщик задач** - мокируется для контроля выполнения
- **Внешние API** - все внешние зависимости изолированы

## Фикстуры

Общие фикстуры в `conftest.py`:

- `test_db_session` - сессия тестовой БД
- `sample_exchange` - образец биржи
- `sample_symbols` - образцы символов (BTC, USDT, ETH)
- `sample_currency_pair` - образец валютной пары
- `sample_time_periods` - образцы периодов времени
- `sample_candle_data` - образец данных свечи
- `populated_test_db` - полностью заполненная тестовая БД

## Отладка тестов

### Запуск одного теста

```bash
# Конкретный тест
pytest test_main.py::test_health_check -v

# Конкретный класс тестов
pytest test_models.py::TestCandleModel -v

# С отладочным выводом
pytest test_main.py::test_health_check -v -s
```

### Остановка на первой ошибке

```bash
pytest -x  # остановить на первой ошибке
pytest --maxfail=3  # остановить после 3 ошибок
```

### Повторный запуск только упавших тестов

```bash
pytest --lf  # last failed
pytest --ff  # failed first
```

## Производительность тестов

### Параллельный запуск

```bash
# Запуск в нескольких процессах
pytest -n auto  # автоматическое определение количества процессов
pytest -n 4     # 4 процесса
```

### Таймауты

Тесты имеют таймауты для предотвращения зависания:

```bash
# Общий таймаут для всех тестов
pytest --timeout=300  # 5 минут

# Таймаут для конкретного теста
@pytest.mark.timeout(60)
def test_slow_operation():
    pass
```

## Continuous Integration

Конфигурация для CI/CD пайплайнов:

```bash
# Полная проверка (для CI)
make full-check

# Быстрая проверка (для pre-commit hooks)
make pre-commit
```

## Решение проблем

### Часто встречающиеся проблемы

1. **Ошибки импорта**
   ```bash
   # Убедитесь что PYTHONPATH настроен правильно
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Проблемы с async тестами**
   ```bash
   # Убедитесь что pytest-asyncio установлен
   pip install pytest-asyncio
   ```

3. **Конфликты с базой данных**
   ```bash
   # Тесты используют SQLite в памяти, не должно быть конфликтов
   # Если проблемы, проверьте что тестовые фикстуры правильно изолированы
   ```

4. **Медленные тесты**
   ```bash
   # Используйте маркер slow для медленных тестов
   pytest -m "not slow"
   ```

### Очистка окружения

```bash
# Очистка временных файлов
make clean

# Полная переустановка зависимостей
pip uninstall -r dev-requirements.txt -y
pip install -r dev-requirements.txt
```

## Добавление новых тестов

### Структура теста

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestNewFeature:
    
    def test_basic_functionality(self):
        """Тестирует базовую функциональность"""
        # Arrange
        # Act  
        # Assert
        pass
    
    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Тестирует асинхронную функциональность"""
        # Arrange
        # Act
        # Assert
        pass
    
    @pytest.mark.slow
    def test_performance(self):
        """Медленный тест производительности"""
        pass
```

### Именование тестов

- Начинайте с `test_`
- Используйте описательные имена
- Группируйте связанные тесты в классы
- Используйте маркеры для категоризации

### Документирование тестов

- Добавляйте docstring для сложных тестов
- Комментируйте неочевидную логику
- Объясняйте зачем нужен конкретный мок

## Статистика

Просмотр статистики проекта:

```bash
make stats
```

Покажет:
- Количество строк кода
- Количество тестовых файлов
- Количество тестовых функций
