virtualenv -p python3 env
pip install -r requirements.txt
python manage.py migrate

source env/bin/activate
python manage.py runserver --settings=financials.settings.dev

heroku create financial-forecast-ui --buildpack heroku/python
python manage.py migrate
heroku run python manage.py createsuperuser

Make sure to add env var FINANCIALS_ENDPOINT with API endpoint.
DJANGO_SETTINGS_MODULE env var should be set to financials.settings.prod