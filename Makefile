# Makefile для проекта revenge-calc
# Команды для разработки, тестирования и развертывания

.PHONY: help install install-dev test test-unit test-integration test-api test-db test-coverage test-watch clean lint format run dev build docker-build docker-run

# Переменные
PYTHON = python3
PIP = pip3
PYTEST = pytest
UVICORN = uvicorn
DOCKER = docker

# Помощь
help:
	@echo "Доступные команды:"
	@echo ""
	@echo "Установка:"
	@echo "  install          - Установить продакшн зависимости"
	@echo "  install-dev      - Установить зависимости для разработки"
	@echo ""
	@echo "Тестирование:"
	@echo "  test             - Запустить все тесты"
	@echo "  test-unit        - Запустить только unit тесты"
	@echo "  test-integration - Запустить только интеграционные тесты"
	@echo "  test-api         - Запустить только API тесты"
	@echo "  test-db          - Запустить только тесты базы данных"
	@echo "  test-coverage    - Запустить тесты с покрытием кода"
	@echo "  test-watch       - Запустить тесты в режиме наблюдения"
	@echo ""
	@echo "Качество кода:"
	@echo "  lint             - Проверить код линтерами"
	@echo "  format           - Отформатировать код"
	@echo ""
	@echo "Запуск:"
	@echo "  run              - Запустить приложение"
	@echo "  dev              - Запустить приложение в режиме разработки"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     - Собрать Docker образ"
	@echo "  docker-run       - Запустить в Docker контейнере"
	@echo ""
	@echo "Утилиты:"
	@echo "  clean            - Очистить временные файлы"

# Установка зависимостей
install:
	$(PIP) install -r requirements.txt

install-dev: install
	$(PIP) install -r dev-requirements.txt

# Тестирование
test:
	$(PYTEST) -v --tb=short

test-unit:
	$(PYTEST) -v -m "unit" --tb=short

test-integration:
	$(PYTEST) -v -m "integration" --tb=short

test-api:
	$(PYTEST) -v -m "api" --tb=short

test-db:
	$(PYTEST) -v -m "database" --tb=short

test-coverage:
	$(PYTEST) --cov=. --cov-report=html --cov-report=term-missing --tb=short

test-watch:
	$(PYTEST) -f --tb=short

# Запуск конкретных тестовых файлов
test-main:
	$(PYTEST) test_main.py -v

test-models:
	$(PYTEST) test_models.py -v

test-data-collection:
	$(PYTEST) test_data_collection_service.py -v

test-exchange:
	$(PYTEST) test_exchange_service.py -v

# Тесты без медленных тестов
test-fast:
	$(PYTEST) -v -m "not slow" --tb=short

# Только медленные тесты
test-slow:
	$(PYTEST) -v -m "slow" --tb=short

# Качество кода
lint:
	@echo "Запуск flake8..."
	@flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true
	@echo "Запуск pylint..."
	@pylint *.py || true

format:
	@echo "Форматирование кода с помощью black..."
	@black . || echo "black не установлен, пропускаем форматирование"
	@echo "Сортировка импортов с помощью isort..."
	@isort . || echo "isort не установлен, пропускаем сортировку импортов"

# Запуск приложения
run:
	$(UVICORN) main:app --host 0.0.0.0 --port 8000

dev:
	$(UVICORN) main:app --reload --host 0.0.0.0 --port 8000

# Запуск с помощью VS Code задач
run-task-server:
	source venv/bin/activate && $(UVICORN) main:app --reload --host 0.0.0.0 --port 8000

run-task-tests:
	source venv/bin/activate && $(PYTEST) -v

run-task-install:
	source venv/bin/activate && $(PIP) install -r requirements.txt && $(PIP) install -r dev-requirements.txt

# Docker команды
docker-build:
	$(DOCKER) build -t revenge-calc:latest .

docker-run:
	$(DOCKER) run -p 8000:8000 revenge-calc:latest

docker-run-dev:
	$(DOCKER) run -it -p 8000:8000 -v $(PWD):/app revenge-calc:latest

# Очистка
clean:
	@echo "Очистка временных файлов..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "Очистка завершена"

# Создание виртуального окружения
venv:
	$(PYTHON) -m venv venv
	@echo "Виртуальное окружение создано. Активируйте его командой:"
	@echo "source venv/bin/activate"

# Активация виртуального окружения и установка зависимостей
setup: venv
	source venv/bin/activate && $(MAKE) install-dev
	@echo "Окружение настроено. Активируйте его командой:"
	@echo "source venv/bin/activate"

# Проверка окружения
check-env:
	@echo "Python: $(shell which python3)"
	@echo "Pip: $(shell which pip3)"
	@echo "Pytest: $(shell which pytest)"
	@echo "Uvicorn: $(shell which uvicorn)"

# Генерация отчета о зависимостях
deps-report:
	$(PIP) list --format=freeze > requirements-freeze.txt
	@echo "Отчет о зависимостях сохранен в requirements-freeze.txt"

# Обновление зависимостей
deps-update:
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -r requirements.txt
	$(PIP) install --upgrade -r dev-requirements.txt

# Создание миграций базы данных (если используется Alembic)
migration:
	@echo "Создание миграции базы данных..."
	# alembic revision --autogenerate -m "Migration message"

# Применение миграций
migrate:
	@echo "Применение миграций базы данных..."
	# alembic upgrade head

# Запуск всех проверок перед коммитом
pre-commit: clean lint test-fast
	@echo "Все проверки перед коммитом завершены успешно"

# Полная проверка (включая медленные тесты)
full-check: clean lint test test-coverage
	@echo "Полная проверка завершена успешно"

# Создание release билда
release: clean full-check
	@echo "Release готов к развертыванию"

# Показать статистику проекта
stats:
	@echo "Статистика проекта:"
	@echo "Строки кода Python:"
	@find . -name "*.py" -not -path "./venv/*" -not -path "./.pytest_cache/*" | xargs wc -l | tail -1
	@echo "Количество тестов:"
	@find . -name "test_*.py" -exec grep -l "def test_" {} \; | wc -l
	@echo "Тестовые функции:"
	@find . -name "test_*.py" -exec grep "def test_" {} \; | wc -l
