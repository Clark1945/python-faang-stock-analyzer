import yfinance as yf
import os,json
import logging as log
import pandas as pd
import plotly.graph_objs as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
from dash import html
from datetime import datetime, timedelta

### Global variable
today_str = datetime.now().strftime('%Y%m%d')
faang_stock_no = ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOG']
faang_stock_xlsx_filename = f'faang_stock_data_{today_str}.xlsx'
log_filename = f'faang_{today_str}.log'
log.basicConfig(level=log.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[log.FileHandler(log_filename),log.StreamHandler()]) # logging on both file and console
company_info = f"company_info{today_str}.json"

class CompanyProfile:
    '''Company Profile Class.'''
    def __init__(self, data: dict):
        self.data = data

    def get_profile_dict(self):
        return {
            "公司名稱": self.data.get("longName", ""),
            "股票代號": self.data.get("symbol", ""),
            "產業": self.data.get("industry", ""),
            "產業別": self.data.get("sector", ""),
            "網站": self.data.get("website", ""),
            "地址": f"{self.data.get('address1', '')}, {self.data.get('city', '')}, {self.data.get('state', '')} {self.data.get('zip', '')}, {self.data.get('country', '')}",
            "電話": self.data.get("phone", ""),
            "員工人數": f"{self.data.get('fullTimeEmployees', 0):,}",
            "公司介紹": self.data.get("longBusinessSummary", ""),
            "市值": self.format_large_number(self.data.get("marketCap", 0)),
            "營收": self.format_large_number(self.data.get("totalRevenue", 0)),
            "淨利": self.format_large_number(self.data.get("netIncomeToCommon", 0)),
            "本益比 (PE)": self.data.get("trailingPE", "N/A"),
            "股息殖利率": f"{self.data.get('dividendYield', 0) * 100:.2f}%",
            "Beta值": self.data.get("beta", "N/A"),
            "分析師評價": self.data.get("averageAnalystRating", "N/A")
        }

    @staticmethod
    def format_large_number(value):
        if value >= 1_000_000_000_000:
            return f"${value / 1_000_000_000_000:.2f}T"
        elif value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        else:
            return f"${value}"

def create_company_card(profile_info):
    '''Create company card with profile information.'''
    return html.Div([
        html.H2(f"{profile_info['公司名稱']} ({profile_info['股票代號']})"),
        html.Hr(),
        html.H3("Description"),
        html.P(profile_info['公司介紹']),
        html.H3("Company Profile"),
        html.Ul([
            html.Li(f"產業: {profile_info['產業']} / {profile_info['產業別']}"),
            html.Li(f"網站: {profile_info['網站']}"),
            html.Li(f"地址: {profile_info['地址']}"),
            html.Li(f"電話: {profile_info['電話']}"),
            html.Li(f"員工人數: {profile_info['員工人數']}"),
            html.Li(f"市值: {profile_info['市值']}"),
            html.Li(f"營收: {profile_info['營收']}"),
            html.Li(f"淨利: {profile_info['淨利']}"),
            html.Li(f"本益比 (PE): {profile_info['本益比 (PE)']}"),
            html.Li(f"股息殖利率: {profile_info['股息殖利率']}"),
            html.Li(f"Beta值: {profile_info['Beta值']}"),
            html.Li(f"分析師評價: {profile_info['分析師評價']}"),
        ], style={'listStyleType': 'none'})
    ], style={
        'border': '1px solid #ccc',
        'padding': '20px',
        'marginBottom': '20px',
        'borderRadius': '10px',
        'backgroundColor': '#f9f9f9'
    })

class FaangStockDataExporter:
    '''Export FAANG stock data from Yahoo Finance. Use For download_stock_data and company_profile'''
    def __init__(self, file_name: str = faang_stock_xlsx_filename):
        self.file_name = file_name

    def download_yahoo_finance_faang_data(self,stock_no_list) -> None:
        '''Download FAANG stock data from Yahoo Finance. If file is not generated, then create it.'''

        # check if exists
        if os.path.exists(self.file_name):
            log.info(f"File Existed!:{self.file_name}. Process will be skipped")
            return
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

        # download company profile
        json_file = company_info
        json_data={}
        for stock_no in stock_no_list:
            dat = yf.Ticker(stock_no)
            json_data[stock_no] = dat.info

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)

class MonthlyStockDataAnalyzer:
    '''Encapsulate get from excel the generate dataframe'''
    def __init__(self, file_name: str = faang_stock_xlsx_filename):
        self.file_name = file_name
        self.stock_data_pd = {}

    def read_excel_and_export_dataframe(self,stock_no_list):
        data = pd.read_excel(faang_stock_xlsx_filename, header=[0, 1], index_col=0, parse_dates=True)  # multi-column
        for element in stock_no_list:
            self.stock_data_pd[element] = data.xs(element, axis=1, level=1) # select from columns, select AAPL from columns

    def get_stock_df(self, symbol):
        return self.stock_data_pd.get(symbol)

def delete_yesterday_file(prefix="faang_stock_data_", suffix=".xlsx"):
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y%m%d')
    filename = f"{prefix}{yesterday_str}{suffix}"

    if os.path.exists(filename):
        try:
            os.remove(filename)
            log.info(f"Yesterday's file deleted: {filename}")
        except Exception as e:
            log.error(f"Failed to delete {filename}: {e}")
    else:
        log.info(f"No yesterday's file found: {filename}")

delete_yesterday_file("faang_stock_data_",".xlsx")
delete_yesterday_file("company_info_",".json")
exporter = FaangStockDataExporter()
exporter.download_yahoo_finance_faang_data(faang_stock_no)
analyzer = MonthlyStockDataAnalyzer()
analyzer.read_excel_and_export_dataframe(faang_stock_no)

# Create Dash Web App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("FAANG Dashboard", style={'textAlign': 'center', 'color': '#503D36', 'font-weight': 'bold'}),
    html.P("Select a FAANG stock from the dropdown menu below:"),
    dcc.Dropdown(
        id='stock-selector',
        options=[{'label': symbol, 'value': symbol} for symbol in faang_stock_no],
        value='AAPL'
    ),
    # 動態公司卡片區域
    html.Div(id='company-card'),
    dcc.Graph(id='candlestick-graph')
])

@app.callback(
    Output('company-card', 'children'),
    Input('stock-selector', 'value')
)
def update_company_card(symbol):
    # 讀取 JSON
    with open(company_info, "r", encoding="utf-8") as f:
        company_data = json.load(f)

    company_profile = CompanyProfile(company_data[symbol])

    info = company_profile.get_profile_dict()
    if not info:
        return html.Div(["No data available"])
    else:
        return create_company_card(info)

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

    # 建立三個子圖: (1)價格 + MA (2)RSI
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],  # 價格60%、RSI20%、Volume20%
        subplot_titles=(f'{symbol} - Candlestick with MA', 'RSI (14)', 'Volume')
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

    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        marker_color='lightblue',
        name='Volume'
    ), row=3, col=1)

    fig.update_layout(template='plotly_dark')

    return fig

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)

