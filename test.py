import yfinance as yf
import os
import logging as log
from datetime import datetime
import pandas as pd
import plotly.graph_objs as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

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

    def get_stock_df(self, symbol):
        return self.stock_data_pd.get(symbol)

    @DeprecationWarning
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

exporter = FaangStockDataExporter()
exporter.download_yahoo_finance_faang_data(faang_stock_no)

analyzer = MonthlyStockDataAnalyzer()
analyzer.read_excel_and_export_dataframe(faang_stock_no)

# Create Dash Web App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("FAANG Stock CandleStick Charts", style={'textAlign': 'center', 'color': '#503D36', 'font-weight': 'bold'}),
    html.P("Select a FAANG stock from the dropdown menu below:"),
    dcc.Dropdown(
        id='stock-selector',
        options=[{'label': symbol, 'value': symbol} for symbol in faang_stock_no],
        value='AAPL'
    ),
    dcc.Graph(id='candlestick-graph')
])


@app.callback(
    Output('candlestick-graph', 'figure'),
    [Input('stock-selector', 'value')]
)
def update_candlestick(symbol):
    df = analyzer.get_stock_df(symbol)

    if df is None or df.empty:
        return go.Figure()

    # 計算 MA (以 20 日為例)
    df['MA20'] = df['Close'].rolling(window=20).mean()

    # 繪製主圖 (K線 + MA20)
    fig = go.Figure()

    # CandleStick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Candlestick'
    ))
    fig.update_layout(
        title=f'{symbol} - CandleStick Chart (Last one month)',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        template='plotly_dark'
    )

    # MA20 線
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA20'],
        mode='lines',
        line=dict(color='orange', width=1.5),
        name='MA20'
    ))
    fig.update_layout(
        title=f'{symbol} - CandleStick Chart with MA20 (Last one month)',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        template='plotly_dark'
    )

    return fig

if __name__ == '__main__':
    app.run(debug=True)




    # analyzer.plot_close_price()  # << 加這一行畫圖

