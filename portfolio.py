import pandas as pd


class Portfolio:
    """
    The object aims to capture the essence of a stock market portfolio through a list of historical transactions.
    """

    transaction_columns = [
        "date",
        "action",
        "ticker",
        "qunatity",
        "pice",
        "fees",
        "amount",
    ]

    def __init__(self, transactions: pd.DataFrame):
        self.transactions = transactions
