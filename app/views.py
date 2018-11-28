from django.conf import settings
from django.http import HttpResponse
from django.template import loader
import datetime
# import dateutil
from dateutil.relativedelta import relativedelta
import json
import logging
import pytz
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

def overview(request):
    # Get user object
    logger.debug('---- User Request ----')
    users_endpoint = '{}/{}'.format(FINANCIALS_ENDPOINT, 'users/5bfafabf696bf66e8d87713f')
    user_response = requests.get(users_endpoint, headers={'Content-Type': 'application/json'})
    user = user_response.json()

    # Get all investment objects for user id
    logger.debug('---- Investments Request ----')
    investments_endpoint = '{}/{}'.format(FINANCIALS_ENDPOINT, 'investments')
    investments_response = requests.get(investments_endpoint, headers={'Content-Type': 'application/json'})
    investments = investments_response.json()

    # Get month delta between today and retirementDate (if present)
    now = datetime.datetime.utcnow()
    utc = pytz.UTC
    now = utc.localize(now)

    retirement_date = user['retirementDate']
    if ":" == retirement_date[-3:-2]:
        retirement_date = retirement_date[:-3] + retirement_date[-2:]
    retirement_datetime = datetime.datetime.strptime(retirement_date, '%Y-%m-%dT%H:%M:%S%z')

    retirement_delta = 0
    while now < retirement_datetime:
        now += relativedelta(months=1)
        retirement_delta += 1

    user['retirementDeltaMonths'] = retirement_delta
    user['retirementDeltaYears'] = retirement_delta // 12

    # Loop through the number of months in the delta
    month_count = 0
    while month_count < retirement_delta:
        month_count += 1
        # Loop through each investment object and divide interestAnnualExpected by 12 and enrich the investment object with
        for investment in investments:
            if 'retirementSummary' not in investment:
                investment['retirementSummary'] = {
                    'montlyBreakdown': [],
                    'totalAmount': float(investment['currentAmount']),
                    'interestMonthlyExpected': float(investment['interestAnnualExpected']) / 12
                }
            # Set the total amount to another variable that's less verbose
            total_amount = investment['retirementSummary']['totalAmount']
            # Add the monthly payment
            total_amount += float(investment['paymentMonthly'])
            # Calculate the monthly interest payment
            interest_amount = total_amount * investment['retirementSummary']['interestMonthlyExpected']
            # Add the monthly interest payment
            total_amount += interest_amount
            # Set the total amount to the new amount to be used moving forward
            investment['retirementSummary']['totalAmount'] = total_amount
            investment['finalAmount'] = total_amount
            monthly_breakdown = {
                'totalAmount': total_amount,
                'monthlyPayment': investment['paymentMonthly'],
                'interestAmount': interest_amount
            }
            investment['retirementSummary']['montlyBreakdown'].append(monthly_breakdown)

    total_retirement_amount = 0
    for investment in investments:
        total_retirement_amount += investment['finalAmount']

    user['totalRetirementAmount'] = total_retirement_amount

    context = {
        'user': user,
        'investments': investments,
    }

    template = loader.get_template("overview.html")
    return HttpResponse(template.render(context))
