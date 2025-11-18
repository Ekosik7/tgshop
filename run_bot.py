import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tgshop.settings')
django.setup()

from botapp.telegram_bot import run_bot


if __name__ == '__main__':
    run_bot()
