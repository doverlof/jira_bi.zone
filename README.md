# JIRA Task Monitor

🤖 Автоматическая система мониторинга выполненных задач в JIRA с отправкой email уведомлений о релизах.

## Возможности

- ✅ Автоматический мониторинг задач в статусе "Готово" 
- 📧 Отправка email уведомлений в стиле релизных писем
- 🔄 Запуск по расписанию (настраивается в crontab)
- 📊 Группировка задач по типам:
  - **Ошибка** → "Исправление ошибок"
  - **История** → "Обновление существующей функциональности"  
  - **Задача** → "Прочие изменения"
- 🚀 Автоматическое получение версии из релизов JIRA
- 💾 Сохранение состояния для избежания дублирования
- 🐳 Полная поддержка Docker

## Требования

- Docker и Docker Compose
- Доступ к JIRA (логин/пароль)
- SMTP сервер для отправки email (Gmail, Яндекс)
- JIRA должна быть доступна по сети

## Быстрый старт

### 1. Клонируйте репозиторий

```bash
git clone <repository-url>
cd jira-task-monitor
```

### 2. Создайте .env файл

```bash
cp .env.example .env
```

Отредактируйте `.env` файл с вашими данными:

```bash
# JIRA настройки
JIRA_URL=http://host.docker.internal:8080    # Для Docker на Mac/Windows
# JIRA_URL=http://172.17.0.1:8080           # Для Docker на Linux
JIRA_USER=your-jira-username
JIRA_PASSWORD=your-jira-password
JIRA_PROJECT_KEY=YOUR_PROJECT_KEY

# Email настройки (Яндекс)
SMTP_SERVER=smtp.yandex.ru
SMTP_PORT=587
EMAIL_USER=your-email@yandex.ru
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com

# Для Gmail
# SMTP_SERVER=smtp.gmail.com
# EMAIL_USER=your-email@gmail.com
# EMAIL_PASSWORD=your-app-password
```

### 3. Настройте расписание

Отредактируйте `celery_app.py` и измените расписание:

```python
'schedule': crontab(day_of_month=1, hour=9, minute=0),  # 1-го числа в 9:00
```

### 4. Запустите систему

```bash
docker-compose up -d
```

### 5. Проверьте работу

```bash
# Логи системы
docker-compose logs -f jira-monitor

# Статус
docker-compose exec jira-monitor python management.py status
```

## Настройка JIRA

### Статус задач

Система ищет задачи в статусе с ID `10001`. Убедитесь что:
- Статус "Готово" в вашей JIRA имеет правильный ID
- Или измените JQL запрос в коде на нужный статус

### Версии релизов  

Система автоматически получает последнюю версию из раздела "Релизы" JIRA проекта:
1. Зайдите в ваш проект JIRA
2. Перейдите в Releases (Релизы)
3. Создайте версию (например "1.0.0.0")
4. Отметьте её как "Выпущенная"

### Типы задач

Поддерживаются русские названия типов:
- **Ошибка** → Исправление ошибок
- **История** → Обновление существующей функциональности
- **Задача** → Прочие изменения

Если у вас другие названия типов, измените в `tasks.py`:

```python
type_mapping = {
    'Bug': 'Исправление ошибок',
    'Story': 'Обновление существующей функциональности',
    'Ваш_Тип': 'Ваша_Категория'
}
```

## Настройка Email

### Для Яндекс почты

1. Включите IMAP/SMTP в настройках Яндекс почты
2. Создайте пароль приложения:
   - Зайдите в настройки аккаунта
   - Безопасность → Пароли приложений
   - Создайте новый пароль
   - Используйте его в `EMAIL_PASSWORD`

### Для Gmail

1. Включите двухфакторную аутентификацию
2. Создайте App Password:
   - Google Account → Security → App passwords
   - Создайте новый пароль для приложения
   - Используйте его в `EMAIL_PASSWORD`

## Управление системой

### Основные команды

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Логи
docker-compose logs -f jira-monitor

# Пересборка после изменений
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Команды management.py

```bash
# Статус системы
docker-compose exec jira-monitor python management.py status

# Сброс уведомлений (для повторной отправки)
docker-compose exec jira-monitor python management.py reset

# Ручной запуск worker
docker-compose exec jira-monitor python management.py worker

# Ручной запуск планировщика
docker-compose exec jira-monitor python management.py beat
```

### Тестирование

```bash
# Сброс состояния и принудительная отправка
docker-compose exec jira-monitor python management.py reset

# Ручной запуск задачи
docker-compose exec jira-monitor python -c "
from tasks import check_jira_tasks
result = check_jira_tasks.delay()
print(result.get())
"
```

## Структура проекта

```
jira-task-monitor/
├── celery_app.py          # Конфигурация Celery и расписание
├── celeryconfig.py        # Настройки Celery (часовой пояс)
├── tasks.py              # Основная логика мониторинга
├── management.py         # Управление системой
├── requirements.txt      # Python зависимости
├── Dockerfile           # Docker образ
├── docker-compose.yml   # Docker Compose конфигурация
├── .env                # Переменные окружения (создать вручную)
├── .env.example        # Пример переменных
├── data/              # Файлы состояния (создается автоматически)
├── logs/             # Логи системы (создается автоматически)
└── README.md        # Этот файл
```

## Настройка расписания

### Примеры crontab

```python
# Каждое 1-е число месяца в 9:00
'schedule': crontab(day_of_month=1, hour=9, minute=0)

# Каждый понедельник в 10:00  
'schedule': crontab(day_of_week=1, hour=10, minute=0)

# Каждый день в 18:00
'schedule': crontab(hour=18, minute=0)

# Каждую пятницу в 17:00
'schedule': crontab(day_of_week=5, hour=17, minute=0)
```

## Решение проблем

### Проблемы с подключением к JIRA

1. **"JIRA недоступна"**
   - Проверьте `JIRA_URL` в .env
   - Для Docker на Mac/Windows: `http://host.docker.internal:8080`
   - Для Docker на Linux: `http://172.17.0.1:8080`
   - Проверьте логин/пароль

2. **"Ошибка получения версий"**
   - Убедитесь что у пользователя есть права на просмотр релизов
   - Проверьте что `JIRA_PROJECT_KEY` указан правильно

### Проблемы с email

1. **"Ошибка отправки email"**
   - Проверьте настройки SMTP сервера
   - Убедитесь что используете пароль приложения, а не основной пароль
   - Проверьте настройки безопасности почтового сервиса

### Проблемы с ссылками

1. **Ссылки не работают в письме**
   - По умолчанию используется `http://localhost:8080`
   - Если JIRA доступна по другому адресу, добавьте в .env:
   ```bash
   JIRA_EXTERNAL_URL=http://your-jira-domain.com
   ```

### Логи и отладка

```bash
# Подробные логи
docker-compose logs --tail=100 jira-monitor

# Ошибки
docker-compose logs jira-monitor | grep ERROR

# Проверка переменных окружения
docker-compose exec jira-monitor env | grep JIRA
```

## Файл письма

Система отправляет письма в формате:

```
Subject: Релиз BI.ZONE Continuous Penetration Testing 1.0.0.0. Внутренняя рассылка

Здравствуйте!

Вышла новая версия BI.ZONE Continuous Penetration Testing 1.0.0.0

1. Обновление существующей функциональности
   • История задача 1
   • История задача 2

2. Исправление ошибок  
   • Ошибка 1
   • Ошибка 2

3. Прочие изменения
   • Задача 1

С уважением,
Группа разработки EASM платформы, BI.ZONE
```

## Лицензия

MIT License

## Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs jira-monitor`
2. Убедитесь что все переменные в .env заполнены
3. Проверьте доступность JIRA из Docker контейнера
4. Протестируйте email настройки отдельно