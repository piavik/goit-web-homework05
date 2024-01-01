'''
Напишіть консольну утиліту, яка повертає курс EUR та USD ПриватБанку протягом останніх кількох днів
'''
import platform
import asyncio
import sys
import logging
import json
from datetime import datetime, timedelta
from time import time
import aiohttp


DAYS_TO_CHECK = 2
DAYS_TO_CHECK_HARD_LIMIT = 10
BASE_URL='https://api.privatbank.ua/p24api/exchange_rates'
DEFAULT_CURRENCIES = ['USD', 'EUR']

async def request(session, url=BASE_URL, params=None):
    try:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                result = await response.json()
                return result
            logging.error(f'Response error: {response.status}')
    except aiohttp.ClientConnectionError as err:
        logging.error(f'Connection error: {err}')
    return None

# it does not need to be async
def filter_data(response, currencies):
    exchange_result = {}
    if not response["exchangeRate"]:
        logging.error("No exchange rate data")
        return {response["date"]: {}}
    for entry in response["exchangeRate"]:
        if entry["currency"] in currencies:
            if len(entry) == 6:
                bank=""
            elif len(entry) == 4:
                logging.error(f'No PB rate, suing NB rate')
                bank="NB"
            else:
                logging.error(f'incorrect data from server: {entry}')
                continue
            exchange_result[entry["currency"]] = {
                'sale': entry[f"saleRate{bank}"], 
                'purchase': entry[f"purchaseRate{bank}"]
                }
    result = {response["date"]: exchange_result}
    return result

def arg_parse():
    if not sys.argv[1:]:
        return DEFAULT_CURRENCIES, DAYS_TO_CHECK
    additional_currencies = []
    days_to_check = DAYS_TO_CHECK
    for arg in sys.argv[1:]:

        #if digit - use as days parameter
        if str(arg).isdigit():
            entered_days = int(arg)
            # LAST numeric parameter used
            # must not exceed the limit "DAYS_TO_CHECK_HARD_LIMIT"
            if not entered_days > DAYS_TO_CHECK_HARD_LIMIT:
                days_to_check = entered_days
        # if letters - add to currencies list (no validation)
        elif str(arg).isalpha():
            additional_currencies.append(str(arg).upper())
    currencies = DEFAULT_CURRENCIES + additional_currencies
    return currencies, days_to_check

def get_dates(days_to_check):
    result = []
    for days_offset in range(days_to_check):
        start_date = datetime.now() - timedelta(days=days_offset)
        start_date_str = start_date.strftime("%d.%m.%Y")
        result.append(start_date_str)
    return result

async def main() -> list[dict]:
    # process entered arguments
    currencies, days_to_check = arg_parse()
    # generate dates strings list
    requested_dates = get_dates(days_to_check)
    # open session
    async with aiohttp.ClientSession() as session:
        responses = [request(session, url=BASE_URL, params={'date': date}) for date in requested_dates]
        results = await asyncio.gather(*responses)
    # filter out unneeded data
    # NB: there is no data - means response["exchangeRate"] is empty for "today" before 9:00
    filtered_data = [filter_data(response, currencies) for response in results]
    return filtered_data
        

if __name__ == "__main__":
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    now = time()
    results = asyncio.run(main())
    print(json.dumps(results, indent=4))
    print(time() - now)