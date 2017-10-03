from django.conf import settings
from django.http import HttpResponse
from django.template import loader
import datetime
import json
import logging
import re
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

FINANCIALS_ENDPOINT = getattr(settings, "FINANCIALS_ENDPOINT", None)

def index(request):
    template = loader.get_template('index.html')
    return HttpResponse(template.render({}, request))

def generate(request):
    logger.debug('---- Form Data ----')
    logger.debug(request.POST)

    investmentCollection = dict()
    investmentKeyRegex = re.compile('^investment\d+')
    requestJSON = {
        'yearsBefore': request.POST['generalYearsBefore'],
        'annualSpending': request.POST['generalAnnualSpending'],
        'annualInflation': request.POST['generalAnnualInflation'],
        'returnRate': request.POST['generalReturnRate'],
    }
    
    for key in request.POST:
        if key == 'csrfmiddlewaretoken':
            continue

        if investmentKeyRegex.match(key) == None:
            continue

        # Get the beginning of the form field name
        keyMatch = investmentKeyRegex.match(key).group()
        # Get which number investment it is
        keyNumber = keyMatch.replace('investment', '')
        # Get the actual form field names without the investment stuff
        keyText = key.replace(keyMatch, '')
        # Lowercase to match what the API is expecting
        formattedKeyText = keyText[0].lower() + keyText[1:]

        # Check to see if the index has is not yet created when storing the value
        if investmentCollection.get(keyNumber) == None:
            investmentCollection[keyNumber] = { formattedKeyText: request.POST[key] }
        else:
            investmentCollection[keyNumber][formattedKeyText] = request.POST[key]

    requestJSON['investments'] = []
    context = {
        'investing': dict(),
        'retirement': []
    }

    colors = ['#F08080', '#6B33FF', '#25CCED']

    for key in investmentCollection:
        requestJSON['investments'].append(investmentCollection[key])
        context['investing'][key] = dict(color=colors[int(key)], results=[])

    logger.debug('---- Request Message ----')
    logger.debug(requestJSON)

    response = requests.post(FINANCIALS_ENDPOINT, data=json.dumps(requestJSON), headers={'Content-Type': 'application/json'})
    logger.debug('---- Response Message ----')
    logger.debug(response.json())

    now = datetime.datetime.now()
    totalYearCount = 0
    yearRecord = now.year
    for yearData in response.json()['years']:
        investmentCount = 1
        if totalYearCount < int(request.POST['generalYearsBefore']):
            for investment in yearData['investments']:
                context['investing'][str(investmentCount)]['results'].append({ 'amount': investment['amount'], 'year': yearRecord })
                investmentCount += 1
        else:
            context['retirement'].append({ 'amount': yearData['amount'], 'year': yearRecord })
        totalYearCount += 1
        yearRecord += 1

    logger.debug('---- View Data ----')
    logger.debug(context)

    template = loader.get_template("graph.html")
    return HttpResponse(template.render(context))
