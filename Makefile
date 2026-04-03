.PHONY: all install run-bot run-site run clean

# ==============================================================================
# Project AM Muse Makefile
#
# Available commands:
#   make all        - Install dependencies and run all services (default).
#   make install    - Create virtual environment and install dependencies.
#   make run        - Run all services in parallel.
#   make run-bot    - Run the Telegram bot server.
#   make run-site   - Run the static site server.
#   make clean      - Remove virtual environment and temporary files.
# ==============================================================================

# Default target
all: install run

# Install python dependencies for the bot
install:
	@echo ">>> Creating Python virtual environment in bot/.venv..."
	python3 -m venv bot/.venv
	@echo ">>> Installing dependencies from bot/requirements.txt..."
	bot/.venv/bin/python -m pip install -r bot/requirements.txt
	@echo "✅ Installation complete."

# Run the telegram bot
run-bot:
	@echo "🤖 Starting Telegram bot server..."
	bot/.venv/bin/python3 -m dotenv -f bot/.env run bot/.venv/bin/python3 bot/bot.py

# Run the static site server
run-site:
	@echo "🌐 Starting static site server on http://localhost:8000..."
	python3 -m http.server --directory docs 8000

# Run both bot and site in parallel
run:
	@echo "🚀 Starting all services in parallel..."
	@bash -c ' \
		python3 -m http.server --directory docs 8000 & PIDS="$!"; \
		bot/.venv/bin/python3 -m dotenv -f bot/.env run bot/.venv/bin/python3 bot/bot.py & PIDS="$! $PIDS"; \
		\
		echo "Started PIDS: $PIDS" ; \
		trap "kill $PIDS" SIGINT ; \
		wait \
	'

# Clean up generated files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf bot/.venv
	@echo "✅ Cleanup complete."
