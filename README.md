# stock-trading
Repository holding functionality to make trading decisions on a personal portfolio.

We start by creating a portfolio class and add attributes to summarize the characeristics and performance of a defined portfolio.
As a next step we create functionality to modify the portfolio based on a given set of transactions.
We use FIFO method to determine the impact on the portfolio due to Sell transactions.

To simplify the calculations, we use 40% on Short Term Capital Gains and 15% on Long Term Capital Gains Tax
There are no fees on purchase of stock but there is a flat fees for sale of stocks. (based on Schwab's fee structure)
