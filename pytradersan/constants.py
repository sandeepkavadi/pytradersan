DAYS_IN_A_YEAR = 365.25
DAYS_IN_A_MONTH = 30.4375
EPSILON = 1e-10

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

ASSET_CLASSES_STANDARD = [
    "EQUITY",
    "BOND",
    "REAL_ESTATE",
    "COMMODITY",
    "FOREX",
    "CRYPTO",
    "CASH",
    "ETF",
]

TAX = {"ST": 0.4, "LT": 0.2}
