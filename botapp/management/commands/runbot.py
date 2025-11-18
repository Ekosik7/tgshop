from django.core.management.base import BaseCommand

from botapp.telegram_bot import run_bot


class Command(BaseCommand):
	help = 'Run Telegram bot (polling)'

	def handle(self, *args, **options):
		run_bot()
