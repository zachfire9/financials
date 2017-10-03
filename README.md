virtualenv -p python3 env
pip install -r requirements.txt

source env/bin/activate
python manage.py runserver --settings=financials.settings.dev