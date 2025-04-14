import pandas as pd

from pytradersan.constants import ACTIONS_STANDARD, TAX, TRANSACTIONS_STANDARD_COLS


def standardize_transactions(
    platform: str, account_name: str, transactions: pd.DataFrame
) -> pd.DataFrame:
    """
    Standardizes transactions to a common format.

    Args:
        platform (str): The trading platform (e.g., 'Schwab', 'Marcus').
        account_name (str): Nick name of the account, to identify and differentiate (e.g. 'marc8208', 'schb576').
        transactions (pd.DataFrame): The transactions DataFrame.

    Returns:
        pd.DataFrame: The standardized transactions DataFrame.
    """
    if platform.lower() == "schwab":
        # Standardize Schwab transactions
        schwab = transactions.copy(deep=True)
        schwab["account"] = account_name
        schwab_actions = {
            "Non-Qualified Div": "DIVIDEND",
            "Cash Dividend": "DIVIDEND",
            "Margin Interest": "INTEREST PAID",
            "Qualified Dividend": "DIVIDEND",
            "MoneyLink Transfer": "ACH",
            "Credit Interest": "INTEREST EARNED",
            "Buy": "BUY",
            "Journal": "TRANSFER",
            "Sell": "SELL",
            "Security Transfer": "TRANSFER",
        }
        schwab["date"] = pd.to_datetime(schwab["Date"].str[-10:], format="%m/%d/%Y")
        schwab["action"] = schwab["Action"].map(schwab_actions)
        schwab["symbol"] = schwab["Symbol"]
        schwab["quantity"] = schwab["Quantity"]
        schwab["price"] = (
            schwab["Price"].str.replace("$", "").str.replace(",", "").astype(float)
        )
        schwab["amount"] = (
            schwab["Amount"].str.replace("$", "").str.replace(",", "").astype(float)
        )
        standardized_transactions = schwab[TRANSACTIONS_STANDARD_COLS]
    elif platform.lower() == "marcus":
        # Standardize Marcus Invest transactions
        marcus = transactions.copy(deep=True)
        marcus["account"] = account_name
        marcus_actions = {
            "A": "ACH",
            "B": "BUY",
            "C": "CAP GAIN",
            "D": "DIVIDEND",
            "F": "FEE",
            "S": "SELL",
            "T": "TRANSFER",
        }
        marcus["action"] = marcus["Transaction"].map(marcus_actions)
        marcus["date"] = pd.to_datetime(marcus["Date"])
        marcus["symbol"] = marcus["Desc"]
        marcus["quantity"] = marcus["Quantity"]
        marcus["Credit"] = (
            marcus["Credit"].str.replace("$", "").str.replace(",", "").astype(float)
        )
        marcus["Debit"] = (
            marcus["Debit"].str.replace("$", "").str.replace(",", "").astype(float)
        )
        marcus["amount"] = marcus["Credit"] - marcus["Debit"]
        marcus["price"] = (
            marcus["Price"].str.replace("$", "").str.replace(",", "").astype(float)
        )
        standardized_transactions = marcus[TRANSACTIONS_STANDARD_COLS]
    else:
        raise ValueError(f"Unsupported platform: {platform}")

    return standardized_transactions
