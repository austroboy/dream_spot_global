.PHONY: install run migrate seed test lint clean

install:
	pip install -r requirements.txt

migrate:
	python manage.py makemigrations && python manage.py migrate

seed:
	python manage.py seed_demo

run:
	python manage.py runserver

test:
	python manage.py test

reminders:
	python manage.py send_reminders

housekeeping:
	python manage.py lead_housekeeping && python manage.py expire_scholarships

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
