import pandas as pd

from pytradersan.constants import ACTIONS_STANDARD, TRANSACTIONS_STANDARD_COLS


class Portfolio:
    """
    The object aims to capture the essence of a stock market portfolio through a list of historical transactions.
    """

    transaction_columns = TRANSACTIONS_STANDARD_COLS

    def __init__(self, transactions: pd.DataFrame):
        self.transactions = transactions
