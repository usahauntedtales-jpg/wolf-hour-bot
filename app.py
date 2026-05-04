import ccxt
import pandas as pd
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# --- GLOBAL STATE ---
STATE = {
    "running": False,
    "exchange": None,
    "coin": "BTC/USDT",
    "price": 0.0,
    "message": "Wolf Engine Online! Waiting for Keys...",
    "wins": 0,
    "loss": 0,
    "total_trades": 0,
    "last_signal": "SCANNING"
}

# --- LOGIC: Ticker & Signals ---
def get_market_ticker():
    try:
        ex = ccxt.bitget()
        tickers = ex.fetch_tickers()
        # Top 20 volume coins for the scrolling line
        top_20 = sorted(tickers.values(), key=lambda x: x['quoteVolume'], reverse=True)[:20]
        ticker_line = ""
        for coin in top_20:
            sym = coin['symbol'].split('/')
            price = coin['last']
            change = round(coin['percentage'], 2)
            icon = "🟢" if change >= 0 else "🔴"
            ticker_line += f" &nbsp;&nbsp;&nbsp; {sym}: ${price} {icon} {change}% &nbsp;&nbsp;&nbsp; |"
        return ticker_line
    except:
        return "Connecting to Global Market..."

def calculate_signal(exchange, symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        price = df['c'].iloc[-1]
        
        if rsi < 35: return "BUY", price, rsi
        elif rsi > 70: return "SELL", price, rsi
        return "WAIT", price, rsi
    except:
        return "ERROR", 0, 0

# --- ROUTES ---
@app.route('/')
def home():
    return send_file('index.html')

@app.route('/status', methods=['GET'])
def status():
    ticker_content = get_market_ticker()
    if STATE['running'] and STATE['exchange']:
        sig, price, rsi = calculate_signal(STATE['exchange'], STATE['coin'])
        STATE['price'] = price
        STATE['last_signal'] = sig
        wr = (STATE['wins'] / STATE['total_trades'] * 100) if STATE['total_trades'] > 0 else 0
        STATE['message'] = f"Strategy: {sig} | RSI: {rsi:.1f} | WinRate: {wr:.1f}%"
    
    return jsonify({**STATE, "ticker": ticker_content})

@app.route('/start', methods=['POST'])
def start():
    data = request.get_json()
    try:
        ex_class = getattr(ccxt, data.get('exchange', 'bitget').lower())
        STATE['exchange'] = ex_class({
            'apiKey': data['apiKey'],
            'secret': data['apiSecret'],
            'password': data.get('passphrase', ''),
            'enableRateLimit': True
        })
        STATE['coin'] = data.get('coin', 'BTC/USDT')
        STATE['running'] = True
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
