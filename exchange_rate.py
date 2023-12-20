'''
Напишіть консольну утиліту, яка повертає курс EUR та USD ПриватБанку протягом останніх кількох днів
'''
import platform
import asyncio
import sys
import logging
import json
from datetime import datetime, timedelta

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

async def main() -> list[dict]:
    rate_data = []
    # process entered arguments
    currencies, days_to_check = arg_parse()
    # open session
    async with aiohttp.ClientSession() as session:
        for days_offset in range(days_to_check):
            start_date = datetime.now() - timedelta(days=days_offset)
            start_date_str = start_date.strftime("%d.%m.%Y")
            response = await request(session, url=BASE_URL, params={'date': start_date_str})
            # filter out unneeded data
            # NB: there is no data - response["exchangeRate"] is empty for "today" before 9:00
            filtered_data = filter_data(response, currencies)
            rate_data.append(filtered_data)
    return rate_data
        

if __name__ == "__main__":
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    result = asyncio.run(main())
    print(json.dumps(result, indent=4))
