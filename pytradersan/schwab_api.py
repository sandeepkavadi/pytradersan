import json
from collections import defaultdict

import numpy as np
import pandas as pd
import requests

from pytradersan import constants

SCHWAB_API_BASE_URL = "https://api.schwabapi.com/trader/v1/accounts"

SCHWAB_API_TRANSACTION_TYPES = [
    "TRADE",
    "RECEIVE_AND_DELIVER",
    "DIVIDEND_OR_INTEREST",
    "ACH_RECEIPT",
    "ACH_DISBURSEMENT",
    "CASH_RECEIPT",
    "CASH_DISBURSEMENT",
    "ELECTRONIC_FUND",
    "WIRE_OUT",
    "WIRE_IN",
    "JOURNAL",
    "MEMORANDUM",
    "MARGIN_CALL",
    "MONEY_MARKET",
    "SMA_ADJUSTMENT",
]

API_COLUMN_MAPPER = {
    "tradeDate": "date",
    "accountNumber": "account",
    "netAmount": "amount",
}


def get_account_numbers(base_url, token):
    headers = {
        "accept": "application/json",
        "Authorization": token,
    }
    url = f"{base_url}/accountNumbers"
    accounts = requests.get(url, headers=headers)
    accounts = json.loads(accounts.content)
    return accounts


def get_account_transactions(
    base_url, token, account_number, start_date, end_date, types="TRADE"
):
    """
    Get account transactions from Schwab API.
    Args:
        SCHWAB_BEARER_TOKEN (str): Schwab API bearer token.
        account_number (str): Account number.
        start_date (str): Start date in 'YYYY-MM-DD'
        end_date (str): End date in 'YYYY-MM-DD'
        types (str): Transaction types. Default is 'TRADE'
    """
    headers = {
        "accept": "application/json",
        "Authorization": token,
    }
    url = f"{base_url}/{account_number}/transactions"
    params = {
        "startDate": start_date,
        "endDate": end_date,
        "types": types,
    }
    transactions = requests.get(url, headers=headers, params=params)
    transactions = json.loads(transactions.content)
    transactions = pd.json_normalize(transactions)
    if isinstance(transactions, dict):
        transactions = pd.DataFrame(transactions)
    return transactions


def get_combined_transactions(base_url, token, start_date, end_date=pd.Timestamp.now()):
    """
    Get combined transactions from Schwab API.This would combine stated transactions from all
    accounts, authorized in the API. The provided dates will be converted to UTC
    Args:
        base_url (str): Schwab API base URL.
        token (str): Schwab API bearer token.
        start_date (str or datetime): Start date in 'YYYY-MM-DD'
        end_date (str or datetime): End date in 'YYYY-MM-DD'
    """
    start_date = pd.to_datetime(start_date).tz_localize("UTC")
    end_date = pd.to_datetime(end_date).tz_localize("UTC")
    steps = ((end_date - start_date) // pd.Timedelta(days=constants.DAYS_IN_A_YEAR)) + 1
    dates = [
        start_date + pd.DateOffset(years=i) for i in range(steps + 1)
    ]  # need all n years including the start date
    dates = [date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z" for date in dates]
    accounts = get_account_numbers(base_url, token)
    transactions = defaultdict(pd.DataFrame)
    for account in accounts:
        for transaction_type in SCHWAB_API_TRANSACTION_TYPES:
            # Get transactions for each account
            txns = pd.DataFrame()
            for start, end in zip(dates[:-1], dates[1:]):
                t = get_account_transactions(
                    base_url=base_url,
                    token=token,
                    account_number=account["hashValue"],
                    start_date=start,
                    end_date=end,
                    types=transaction_type,
                )
                txns = pd.concat([txns, t], ignore_index=True)
            # txns.drop_duplicates(inplace=True)
            # Combine transactions
            transactions[transaction_type] = pd.concat(
                [transactions[transaction_type], txns], ignore_index=True
            )
    return transactions


def parse_trades(transfer_items):
    """
    Parse transfer items from Schwab API.
    Args:
        transfer_items (list): List of transfer items.
    Returns:
        pd.DataFrame: DataFrame of transfer items.
    """
    instruments = [
        x for x in transfer_items if x["instrument"]["assetType"] != "CURRENCY"
    ]
    print(f"Number of instruments to process: {len(instruments)}")
    assert len(instruments) == 1
    instrument = instruments[0]
    parsed_txns = {
        "symbol": instrument["instrument"]["symbol"],
        "quantity": instrument["amount"],
        "price": instrument["price"],
        "asset": instrument["instrument"]["assetType"],
    }
    return parsed_txns


def process_raw_trades(raw_trades):
    trades = raw_trades.apply(lambda x: parse_trades(x["transferItems"]), axis=1).apply(
        pd.Series
    )
    trades["price"] = trades["price"].astype(float)
    trades["quantity"] = trades["quantity"].astype(float)
    trades["action"] = np.where(trades["quantity"] > 0, "BUY", "SELL")
    trades = trades.join(raw_trades.copy(deep=True).drop(columns=["transferItems"]))
    trades = trades.rename(columns=API_COLUMN_MAPPER)
    trades = trades[API_COLUMN_MAPPER.values()]
    trades["date"] = pd.to_datetime(trades["date"]).dt.date
    trades = trades.drop_duplicates()
    return trades
