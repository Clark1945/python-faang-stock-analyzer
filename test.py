import yfinance as yf
import os
import logging as log
from datetime import datetime
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio


faang_stock_no = ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOG']
faang_stock_xlsx_filename = 'faang_stock_data.xlsx'
today_str = datetime.now().strftime('%Y%m%d')
log_filename = f'faang_{today_str}.log'
log.basicConfig(level=log.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[log.FileHandler(log_filename),log.StreamHandler()]) # logging on both file and console

class FaangStockDataExporter:
    def __init__(self, file_name: str = faang_stock_xlsx_filename):
        self.file_name = file_name

    def download_yahoo_finance_faang_data(self,stock_no_list) -> None:
        '''Download FAANG stock data from Yahoo Finance. If file is not generated, then create it.'''

        # check if exists
        if os.path.exists(self.file_name):
            log.info(f"File Existed!:{self.file_name}. Process will be skipped")
            return

        # only for test
        # tickers = yf.Tickers('META AAPL AMZN NFLX GOOG')
        # tickers.tickers['META'].info

        # Start download
        log.info("Start downloading FAANG stock data...")
        data = yf.download(stock_no_list, period='1mo')

        if not data.empty:
            data.to_excel(self.file_name)
            log.info(f"downloaded successfully and save as {self.file_name}")
        else:
            log.info("File not generated...some error happened!")



class MonthlyStockDataAnalyzer:
    def __init__(self, file_name: str = faang_stock_xlsx_filename):
        self.file_name = file_name
        self.stock_data_pd = {}

    def read_excel_and_export_dataframe(self,stock_no_list):
        data = pd.read_excel(faang_stock_xlsx_filename, header=[0, 1], index_col=0, parse_dates=True)  # multi-column
        for element in stock_no_list:
            self.stock_data_pd[element] = data.xs(element, axis=1, level=1) # select from columns, select AAPL from columns

    def plot_close_price(self):
        if not self.stock_data_pd:
            log.warning("No stock data available to plot.")
            return

        fig = go.Figure()
        for symbol, df in self.stock_data_pd.items():
            if 'Close' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['Close'],
                    mode='lines',
                    name=symbol
                ))

        fig.update_layout(
            title='FAANG Stocks Close Prices - Last 1 Month',
            xaxis_title='Date',
            yaxis_title='Price (USD)',
            template='plotly_dark',
            hovermode='x unified'
        )

        fig.show()

if __name__ == '__main__':
    exporter = FaangStockDataExporter()
    exporter.download_yahoo_finance_faang_data(faang_stock_no)

    analyzer = MonthlyStockDataAnalyzer()
    analyzer.read_excel_and_export_dataframe(faang_stock_no)
    analyzer.plot_close_price()  # << 加這一行畫圖

