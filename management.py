import sys
import os
from pathlib import Path

# Добавляем текущий каталог в Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

from celery_app import app

os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379/0')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')


def main():
    if len(sys.argv) < 2:
        print("""
Использование: python management.py <команда>
Доступные команды:
  worker    - Запустить Celery worker
  beat      - Запустить Celery beat (планировщик)
  monitor   - Запустить мониторинг Celery
  reset     - Сбросить все уведомления
  status    - Показать статус системы
  both      - Запустить и worker и beat одновременно
  чтобы все было збс
        """)
        return

    command = sys.argv[1]

    if command == "worker":
        print("Запуск Celery Worker...")
        app.worker_main(['worker', '--loglevel=info', '--concurrency=1'])

    elif command == "beat":
        print("Запуск Celery Beat (планировщик)...")
        app.control.purge()
        app.start(['beat', '--loglevel=info'])

    elif command == "monitor":
        print("Запуск мониторинга Celery...")
        app.start(['events', '--camera=flower'])

    elif command == "reset":
        print("Сброс уведомлений...")
        from tasks import reset_notifications
        result = reset_notifications.delay()
        print(result.get())

    elif command == "status":
        print("Получение статуса...")
        from tasks import get_status
        result = get_status.delay()
        status = result.get()
        print(f"""
Статус системы:
   - Отправлено уведомлений: {status.get('sent_notifications', 'N/A')}
   - Обработано задач: {status.get('processed_issues', 'N/A')}
   - Время: {status.get('timestamp', 'N/A')}
        """)

    elif command == "both":
        print("Запуск Worker и Beat одновременно...")
        import subprocess
        import threading

        def run_worker():
            subprocess.run([sys.executable, "management.py", "worker"])

        def run_beat():
            subprocess.run([sys.executable, "management.py", "beat"])

        worker_thread = threading.Thread(target=run_worker)
        beat_thread = threading.Thread(target=run_beat)

        worker_thread.start()
        beat_thread.start()

        try:
            worker_thread.join()
            beat_thread.join()
        except KeyboardInterrupt:
            print("\n⏹️ Остановка сервисов...")

    else:
        print(f"Неизвестная команда: {command}")


if __name__ == "__main__":
    main()