import yfinance as yf
import os
import logging as log
from datetime import datetime
import pandas as pd
import plotly.graph_objs as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots

today_str = datetime.now().strftime('%Y%m%d')
faang_stock_no = ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOG']
faang_stock_xlsx_filename = f'faang_stock_data_{today_str}.xlsx'
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

        try:
            data = yf.download(stock_no_list, period='6mo')
        except Exception as e:
            log.error(f"Download failed: {e}")
            return

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
            title='FAANG Stocks Close Prices - Last 6 Month',
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

    # 計算 MA5、MA20、MA60 移動平均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()

    # 計算 RSI (14日)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 繪製主圖 (K線 + MA20)
    fig = go.Figure()

    # 建立兩個子圖: (1)價格 + MA (2)RSI
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} - Candlestick with MA', 'RSI (14)')
    )

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
        title=f'{symbol} - CandleStick Chart (Last 6 month)',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        template='plotly_dark'
    )

    # MA5 (紅色)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA5'],
        mode='lines',
        line=dict(color='red', width=1.5),
        name='MA5'
    ))

    # MA20 (橘色)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA20'],
        mode='lines',
        line=dict(color='orange', width=1.5),
        name='MA20'
    ))

    # MA60 (綠色)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA60'],
        mode='lines',
        line=dict(color='green', width=1.5),
        name='MA60'
    ))

    # RSI 子圖
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['RSI'],
        mode='lines',
        line=dict(color='purple', width=1.5),
        name='RSI (14)'
    ), row=2, col=1)

    # RSI 標準線（超買、超賣區）
    fig.add_hline(y=70, line_dash="dash", line_color="gray", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="gray", row=2, col=1)

    fig.update_layout(
        template='plotly_dark',
        height=1000
    )

    return fig

if __name__ == '__main__':
    app.run(debug=True)

