import os
from .base import *

DEBUG=bool(os.environ.get('DEBUG', 'False'))
FINANCIALS_ENDPOINT=os.environ.get('FINANCIALS_ENDPOINT')
USER_ID=os.environ.get('USER_ID')