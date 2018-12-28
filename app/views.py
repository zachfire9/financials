"""Views for the application."""
from django.conf import settings
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
import datetime
from dateutil.relativedelta import relativedelta
import copy
import json
import logging
import pytz
import random
import re
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# red, purple, teal, green, blue, pink, maroon, brownish, violet
colors = ['#F08080', '#6B33FF', '#25CCED', '#18bf45', '#131eb2', '#fc43f1', '#860240', '#964939', '#ab7cdd']
FINANCIALS_ENDPOINT = getattr(settings, "FINANCIALS_ENDPOINT", None)


def index(request):
    """The main method."""
    template = loader.get_template('index.html')
    return HttpResponse(template.render({}, request))


def generate(request):
    """Generate method."""
    logger.debug('---- Form Data ----')
    logger.debug(request.POST)

    investment_collection = dict()
    investment_key_regex = re.compile('^investment\d+')
    request_json = {
        'yearsBefore': request.POST['generalYearsBefore'],
        'annualSpending': request.POST['generalAnnualSpending'],
        'annualInflation': request.POST['generalAnnualInflation'],
        'returnRate': request.POST['generalReturnRate'],
    }

    for key in request.POST:
        if key == 'csrfmiddlewaretoken':
            continue

        if investment_key_regex.match(key) is None:
            continue

        # Get the beginning of the form field name
        key_match = investment_key_regex.match(key).group()
        # Get which number investment it is
        key_number = key_match.replace('investment', '')
        # Get the actual form field names without the investment stuff
        key_text = key.replace(key_match, '')
        # Lowercase to match what the API is expecting
        formatted_key_text = key_text[0].lower() + key_text[1:]

        # Check to see if the index has is not yet created when storing the value
        if investment_collection.get(key_number) is None:
            investment_collection[key_number] = {formatted_key_text: request.POST[key]}
        else:
            investment_collection[key_number][formatted_key_text] = request.POST[key]

    request_json['investments'] = []
    context = {
        'investing': dict(),
        'retirement': []
    }

    colors = ['#F08080', '#6B33FF', '#25CCED']

    for key in investment_collection:
        request_json['investments'].append(investment_collection[key])
        context['investing'][key] = dict(color=colors[int(key)], results=[])

    logger.debug('---- Request Message ----')
    logger.debug(request_json)

    response = requests.post(FINANCIALS_ENDPOINT, data=json.dumps(request_json), headers={'Content-Type': 'application/json'})
    logger.debug('---- Response Message ----')
    logger.debug(response.json())

    now = datetime.datetime.now()
    total_year_count = 0
    year_record = now.year
    for yearData in response.json()['years']:
        investment_count = 1
        if total_year_count < int(request.POST['generalYearsBefore']):
            for investment in yearData['investments']:
                context['investing'][str(investment_count)]['results'].append({'amount': investment['amount'], 'year': year_record})
                investment_count += 1
        else:
            context['retirement'].append({'amount': yearData['amount'], 'year': year_record})
        total_year_count += 1
        year_record += 1

    logger.debug('---- View Data ----')
    logger.debug(context)

    template = loader.get_template("graph.html")
    return HttpResponse(template.render(context))


def details_update(request):
    """Detail method."""
    user_key_regex = re.compile('^user')
    investment_key_regex = re.compile('^investment\d+')
    user_id = None
    user_request = {}
    investment_collection = {}
    for key in request.POST:
        print(key)
        if key == 'csrfmiddlewaretoken':
            continue

        if user_key_regex.match(key) is None and investment_key_regex.match(key) is None:
            continue

        if key == 'userId':
            user_id = request.POST[key]

        if user_key_regex.match(key):
            user_key_match = user_key_regex.match(key).group()
            # Get the actual form field names without the user stuff
            key_text = key.replace(user_key_match, '')
            # Lowercase to match what the API is expecting
            formatted_key_text = key_text[0].lower() + key_text[1:]
            user_request[formatted_key_text] = request.POST[key]

        if investment_key_regex.match(key):
            investment_key_match = investment_key_regex.match(key).group()
            # Get which number investment it is
            key_number = investment_key_match.replace('investment', '')
            # Get the actual form field names without the investment stuff
            key_text = key.replace(investment_key_match, '')
            # Lowercase to match what the API is expecting
            formatted_key_text = key_text[0].lower() + key_text[1:]

            # Check to see if the index has is not yet created when storing the value
            if investment_collection.get(key_number) is None:
                investment_collection[key_number] = {formatted_key_text: request.POST[key]}
            else:
                investment_collection[key_number][formatted_key_text] = request.POST[key]

    for key in investment_collection:
        investment_request = investment_collection[key]
        investment_request['userId'] = user_id
        investments_endpoint = '{}/{}/{}'.format(FINANCIALS_ENDPOINT, 'investments', investment_request['id'])
        requests.put(investments_endpoint, headers={'Content-Type': 'application/json'}, data=json.dumps(investment_request))

    users_endpoint = '{}/{}/{}'.format(FINANCIALS_ENDPOINT, 'users', user_id)
    requests.put(users_endpoint, headers={'Content-Type': 'application/json'}, data=json.dumps(user_request))

    return redirect('/details/')


def details(request):
    """Detail method."""
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

    investment_count = 1
    for investment in investments:
        investment_count += 1
        investment['count'] = investment_count

    context = {
        'user': user,
        'investments': investments,
    }

    template = loader.get_template("details.html")
    return HttpResponse(template.render(context, request))


def overview(request):
    """Overview method."""
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
    year_increment = now
    while year_increment < retirement_datetime:
        year_increment += relativedelta(months=1)
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
                    'monthlyBreakdown': [],
                    'yearlyBreakdown': [],
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
            investment['retirementSummary']['monthlyBreakdown'].append(monthly_breakdown)

            if ((month_count + 1) % 12) is 0:
                yearly_breakdown = {
                    'year': now.year + ((month_count + 1) / 12),
                    'totalAmount': total_amount,
                    'monthlyPayment': investment['paymentMonthly'],
                    'interestAmount': interest_amount
                }
                investment['retirementSummary']['yearlyBreakdown'].append(yearly_breakdown)

    total_retirement_amount = 0
    investment_colors = copy.copy(colors)
    for investment in investments:
        investment_color = random.choice(investment_colors)
        investment['color'] = investment_color
        investment_colors.remove(investment_color)
        total_retirement_amount += investment['finalAmount']
        investment['initialAmountFormatted'] = "{:,}".format(float(investment['currentAmount']), 2)
        investment['finalAmountFormatted'] = "{:,}".format(round(investment['finalAmount'], 2))

    user['totalRetirementAmount'] = "{:,}".format(round(total_retirement_amount, 2))

    context = {
        'user': user,
        'investments': investments,
    }

    template = loader.get_template("overview.html")
    return HttpResponse(template.render(context))
