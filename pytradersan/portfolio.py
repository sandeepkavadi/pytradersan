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
    portfolio_price_data = None

    def __init__(
        self,
        trades: pd.DataFrame,
        price_data: pd.DataFrame = None,
        as_of_date: str = None,
    ):
        # TODO: define process trades function. Easier to combine portfolios
        self._trades = trades.copy(deep=True)
        if price_data is not None:
            if self.__class__.portfolio_price_data is not None:
                self.__class__.portfolio_price_data = (
                    self.__class__.portfolio_price_data.combine_first(
                        price_data.copy(deep=True)
                    )
                )
            else:
                self.__class__.portfolio_price_data = price_data.copy(deep=True)
        if as_of_date:
            self.as_of_date = pd.to_datetime(
                as_of_date
            )  # TODO: Create a getter and setter for as_of_date
        else:
            self.as_of_date = pd.Timestamp.now()
        self._process_trades()
        self.update_price_data()
        self._assign_price_data()
        self._update_snapshot()

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
        self._trades = self._trades.sort_values(
            by=["symbol", "date"], ascending=[True, True]
        ).reset_index(drop=True)
        self._trades["cum_quantity"] = self._trades.groupby("symbol")[
            "quantity"
        ].cumsum()
        self._trades["ltcg_cost"] = self._trades["ltcg_shares"] * self._trades["price"]
        self._ltcg_lots = self._trades[self._trades.ltcg_flag == 1]
        self._stcg_lots = self._trades[self._trades.ltcg_flag == 0]
        self.symbols = self._trades.symbol.unique().tolist()
        self.tickers = {symbol: yf.Ticker(symbol) for symbol in self.symbols}

    @classmethod
    def _download_price_data(cls, symbols, **kwargs):
        if symbols is None:
            return None
        params = {}
        params["tickers"] = symbols
        if not kwargs:
            params["period"] = "max"
        else:
            params.update(kwargs)
        print(f"Downloading data for {params['tickers']}")
        downloaded_data = yf.download(**params)
        return downloaded_data

    def _get_download_params(self):
        if self.__class__.portfolio_price_data is None:
            print(f"Prices data not found. Need to download data for {self.symbols}")
            return (self.symbols, None)
        else:
            missing_symbols = set(self.symbols) - set(
                self.__class__.portfolio_price_data.columns.get_level_values("Ticker")
            )
            max_available_date = self.__class__.portfolio_price_data.index.max()
            last_row = self.__class__.portfolio_price_data.loc[max_available_date]
            additional_missing_symbols = set(
                last_row.index[last_row.isna()].get_level_values("Ticker")
            )
            missing_symbols = missing_symbols.union(additional_missing_symbols)
            print(f"Missing symbols: {missing_symbols}, max date: {max_available_date}")
            return (list(missing_symbols), max_available_date)

    def update_price_data(self) -> None:
        missing_symbols, max_available_date = self._get_download_params()
        if missing_symbols:
            # Get data for missing symbols first
            print(f"Getting data for missing symbols: {missing_symbols}")
            new_symbols_price_data = self.__class__._download_price_data(
                symbols=missing_symbols
            )
            print(f"Max date for new symbols: {new_symbols_price_data.index.max()}")
            if self.__class__.portfolio_price_data is None:
                self.__class__.portfolio_price_data = new_symbols_price_data.copy(
                    deep=True
                )
            else:
                self.__class__.portfolio_price_data = (
                    self.__class__.portfolio_price_data.combine_first(
                        new_symbols_price_data
                    )
                )
        else:
            print("No missing symbols found")
        # Get data for missing dates
        if max_available_date.strftime("%Y-%m-%d") < pd.Timestamp.now().strftime(
            "%Y-%m-%d"
        ):
            print(f"Getting data for missing dates from {max_available_date}")
            data_for_missing_dates = self.__class__._download_price_data(
                symbols=self.__class__.portfolio_price_data.columns.get_level_values(
                    "Ticker"
                )
                .unique()
                .tolist(),
                start=max_available_date.strftime("%Y-%m-%d"),
                end=pd.Timestamp.now().strftime("%Y-%m-%d"),
            )
            self.__class__.portfolio_price_data = (
                self.__class__.portfolio_price_data.combine_first(
                    data_for_missing_dates
                )
            )
        else:
            print("Prices are up to date")
        # Remove duplicates
        self.__class__.portfolio_price_data = (
            self.__class__.portfolio_price_data.T.drop_duplicates().T.drop_duplicates()
        )  # This update is not working. Need to create a class method to do this
        print(
            f"Price data updated. New max date: {self.__class__.portfolio_price_data.index.max()}"
        )
        return None

    def _assign_price_data(self) -> None:
        if self.__class__.portfolio_price_data is None:
            raise ValueError("Price data not found. Please download price data first.")
        if not self.symbols:
            raise ValueError("No symbols found. Please provide symbols.")
        if not self.as_of_date:
            raise ValueError("No as_of_date found. Please provide as_of_date.")
        print(
            f"Max date for price data: {self.__class__.portfolio_price_data.index.max()}"
        )
        print(f"As of date: {self.as_of_date}")
        self.prices = self.__class__.portfolio_price_data.T.loc[
            (
                self.__class__.portfolio_price_data.columns.get_level_values("Price")
                == "Close"
            )
            & (
                self.__class__.portfolio_price_data.columns.get_level_values(
                    "Ticker"
                ).isin(self.symbols)
            )
        ].T
        self.volumes = self.__class__.portfolio_price_data.T.loc[
            (
                self.__class__.portfolio_price_data.columns.get_level_values("Price")
                == "Volume"
            )
            & (
                self.__class__.portfolio_price_data.columns.get_level_values(
                    "Ticker"
                ).isin(self.symbols)
            )
        ].T
        self.prices.columns = self.prices.columns.droplevel("Price")
        self.volumes.columns = self.volumes.columns.droplevel("Price")
        self.prices = self.prices[
            self.prices.index <= self.as_of_date.strftime("%Y-%m-%d")
        ]
        self.volumes = self.volumes[
            self.volumes.index <= self.as_of_date.strftime("%Y-%m-%d")
        ]
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
        self._positions = self._positions.rename(
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
            self._positions["num_shares"] * self._positions["current_price"]
        )
        self._positions["gain"] = (
            self._positions["cost_basis"] + self._positions["market_value"]
        )
        self._positions["gain_perc"] = -(
            self._positions["gain"] / self._positions["cost_basis"]
        )
        self._positions["wtd_holding_days"] = -self._positions["wtd_holding_days"]
        self._positions["wtd_avg_holding_period_days"] = -(
            self._positions["wtd_holding_days"] / self._positions["cost_basis"]
        )
        self._positions = self._positions.applymap(lambda x: round(x, 4))
        return self._positions

    @property
    def snapshot(self):
        positions = self._update_snapshot()
        positions = positions.applymap(lambda x: round(x, 2))
        positions = positions[positions["num_shares"].abs() >= 1]
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
        lots = lots[lots.symbol.isin(self._active_symbols)]
        return lots

    def combine(self, new_portfolio, as_of_date=None):
        self._trades = pd.concat([self._trades, new_portfolio.trades], axis=0)
        if as_of_date:
            self.as_of_date = pd.to_datetime(self.as_of_date)
        else:
            self.as_of_date = min(self.as_of_date, new_portfolio.as_of_date)
        self._process_trades()
        self.update_price_data()
        self._assign_price_data()
        self._update_snapshot()

    # TODO: Add ATH, ATL, 52WH, 52L, price_statistics, asset_allocation, info,
    # calendar, price targets
