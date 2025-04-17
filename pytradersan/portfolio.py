from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from pytradersan import constants


class Portfolio:
    """
    The object aims to capture the essence of a stock market portfolio through
    a list of historical transactions.
    """

    transaction_columns = constants.TRANSACTIONS_STANDARD_COLS
    asset_classes = constants.ASSET_CLASSES_STANDARD
    tax = constants.TAX
    price_data = None

    def __init__(self, trades: pd.DataFrame, as_of_date: str = None):
        # TODO: define process trades function. Easier to combine portfolios
        self._trades = trades.copy(deep=True)
        if as_of_date:
            self.as_of_date = pd.to_datetime(self.as_of_date)
        else:
            self.as_of_date = pd.Timestamp.now()
        self._process_trades()
        self.update_price_data()
        self._assign_price_data()

    def _process_trades(self):
        self._trades["date"] = pd.to_datetime(self._trades["date"])
        self._trades["holding_period_days"] = (
            self.as_of_date - self._trades["date"]
        ).dt.days
        self._trades["amount_holding_period_days"] = (
            self._trades["amount"] * self._trades["holding_period_days"]
        )
        self._trades["ltcg_flag"] = (
            self._trades["holding_period_days"] > constants.DAYS_IN_A_YEAR
        ).astype(int)
        self._trades["ltcg_shares"] = (
            self._trades["ltcg_flag"] * self._trades["quantity"]
        )
        self._trades["ltcg_cost"] = self._trades["ltcg_shares"] * self._trades["price"]
        self._ltcg_lots = self._trades[self._trades.ltcg_flag == 1]
        self._stcg_lots = self._trades[self._trades.ltcg_flag == 0]
        self.symbols = self._trades.symbol.unique().tolist()
        self.tickers = {symbol: yf.Ticker(symbol) for symbol in self.symbols}

    @classmethod
    def _download_price_data(cls, symbols, **kwargs):
        params = {}
        params["tickers"] = symbols
        if not kwargs:
            params["period"] = "max"
        else:
            params.update(kwargs)
        downloaded_data = yf.download(**params)
        return downloaded_data

    def _get_download_params(self):
        if Portfolio.price_data is not None:
            return (self.symbols, None)
        else:
            missing_symbols = set(self.symbols) - set(
                Portfolio.price_data.columns.get_level_values("Ticker")
            )
            max_available_date = Portfolio.price_data.index.max()
            last_row = Portfolio.price_data.loc[max_available_date]
            additional_missing_symbols = set(
                last_row.index[last_row.isna()].get_level_values("Ticker")
            )
            missing_symbols = missing_symbols.union(additional_missing_symbols)
            return (list(missing_symbols), max_available_date)

    def update_price_data(self) -> None:
        missing_symbols, max_available_date = self._get_download_params()
        # Get data for missing symbols first
        new_symbols_price_data = Portfolio._download_price_data(missing_symbols)
        if Portfolio.price_data is not None:
            Portfolio.price_data = new_symbols_price_data.copy(deep=True)
        else:
            Portfolio.price_data = Portfolio.price_data.combine_first(
                new_symbols_price_data
            )
        # Get data for missing dates
        data_for_missing_dates = Portfolio._download_price_data(
            symbols=Portfolio.price_data.columns.get_level_values("Ticker")
            .unique()
            .tolist(),
            start=max_available_date,
            end=pd.Timestamp.now().strftime("%Y-%m-%d"),
        )
        Portfolio.price_data = Portfolio.price_data.combine_first(
            new_symbols_price_data
        )
        Portfolio.price_data = (
            Portfolio.price_data.T.drop_duplicates().T.drop_duplicates()
        )
        return None

    def _assign_price_data(self) -> None:
        self.prices = Portfolio.price_data.T.loc[
            (Portfolio.price_data.columns.get_level_values("Price") == "Close")
            & (
                Portfolio.price_data.columns.get_level_values("Ticker").isin(
                    self.symbols
                )
            )
        ].T
        self.volumes = Portfolio.price_data.T.loc[
            (Portfolio.price_data.columns.get_level_values("Price") == "Volume")
            & (
                Portfolio.price_data.columns.get_level_values("Ticker").isin(
                    self.symbols
                )
            )
        ].T
        self.prices.columns = self.prices.columns.droplevel("Price")
        self.volumes.columns = self.volumes.columns.droplevel("Price")
        self.prices = self.prices[self.prices.index <= self.as_of_date]
        self.current_prices = self.prices.loc[self.prices.index.max()].rename(
            "current_price"
        )
        return None

    def _update_snapshot(self):
        self._positions = self._trades.groupby("symbol")[
            [
                "quantity",
                "amount",
                "amount_holding_period_days",
                "ltcg_shares",
                "ltcg_cost",
            ]
        ].sum()
        self._positions.rename(
            columns={
                "quantity": "num_shares",
                "amount": "cost_basis",
                "amount_holding_period_days": "wtd_holding_days",
                "ltcg_shares": "ltcg_shares",
                "ltcg_cost": "ltcg_cost",
            }
        )
        self._positions = self._positions.join(self.current_prices)
        self._positions["market_value"] = (
            self._positions["current_price"] * self._positions["current_price"]
        )
        self._positions["gain"] = (
            self._positions["market_value"] * self._positions["cost_basis"]
        )
        self._positions["gain_perc"] = (
            self._positions["gain"] / self._positions["cost_basis"]
        )
        self._positions["wtd_avg_holding_period_days"] = (
            self._positions["wtd_holding_days"] / self._positions["cost_basis"]
        )
        return self._positions

    @property
    def snapshot(self):
        positions = self._update_snapshot(self)
        return positions

    @property
    def trades(self):
        return self._trades

    def get_upcoming_ltcg_lots(self, days: int = 7, symbols: list | str = None):
        print(
            f"""Getting lots crossing the Long Term Capital Gains threshold
              within the next {days} days"""
        )
        lots = self._stcg_lots.copy(deep=True)
        lots = lots[lots.holding_period_days > (constants.DAYS_IN_A_YEAR - days)]
        if symbols:
            if isinstance(symbols, str):
                lots = lots[lots.symbol == symbols]
            elif isinstance(symbols, list):
                lots = lots[lots.symbol.isin(symbols)]
            else:
                raise TypeError(
                    "Unsupported type for symbols. Inputs"
                    "should be given as a string for a single input of as a list"
                    "in case of multiple inputs"
                )
        return lots

    def combine(self, new_portfolio, as_of_date):
        self._trades = pd.concat([self._trades, new_portfolio.trades], axis=0)
        if as_of_date:
            self.as_of_date = pd.to_datetime(self.as_of_date)
        else:
            self.as_of_date = pd.Timestamp.now()
        self._process_trades()
        self.update_price_data()
        self._assign_price_data()

    # TODO: Add ATH, ATL, 52WH, 52L, price_statistics, asset_allocation, info,
    # calendar, price targets
