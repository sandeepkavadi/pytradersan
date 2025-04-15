DAYS_IN_A_YEAR = 365

TRANSACTIONS_STANDARD_COLS = [
    "date",
    "account",
    "symbol",
    "action",
    "quantity",
    "price",
    "amount",
]
ACTIONS_STANDARD = [
    "BUY",
    "SELL",
    "DIVIDEND",
    "SPLIT",
    "ACH",
    "INTEREST EARNED",
    "INTEREST PAID",
    "FEE",
    "TRANSFER",
]
SCHWAB_TRANSACTION_TYPES = [
    "TRADE",
    # 'RECEIVE_AND_DELIVER',
    "DIVIDEND_OR_INTEREST",
    # 'ACH_RECEIPT',
    # 'ACH_DISBURSEMENT',
    # 'CASH_RECEIPT',
    # 'CASH_DISBURSEMENT',
    # 'ELECTRONIC_FUND',
    # 'WIRE_OUT',
    # 'WIRE_IN',
    # 'JOURNAL',
    # 'MEMORANDUM',
    # 'MARGIN_CALL',
    # 'MONEY_MARKET',
    # 'SMA_ADJUSTMENT',
]

TAX = {"ST": 0.4, "LT": 0.2}
