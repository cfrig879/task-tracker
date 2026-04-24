# Cadence

Cadence is a Django web application for tracking tasks, comparing estimated vs actual time, and reflecting on patterns.

## What you need (Windows)
- Python 3.x
- This repo (including `requirements.txt`)

## Run Cadence (Windows)

```bat
:: 1) Create a virtual environment
py -m venv .venv

:: 2) Activate it
.\.venv\Scripts\activate

:: 3) Install dependencies
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

:: 4) Setup database + create admin user
py manage.py migrate
py manage.py createsuperuser

:: 5) Start the server
py manage.py runserver