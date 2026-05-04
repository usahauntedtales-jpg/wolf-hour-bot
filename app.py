import ccxt
import pandas as pd
import pandas_ta as ta
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

STATE = {
    "running": False,
    "exchange": None,
    "coin": "BTC/USDT",
    "price": 0.0,
    "message": "Engine Ready. Waiting for API Keys...",
}

def get_accuracy_signal(exchange, symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['ema200'] = ta.ema(df['close'], length=200)
        df['rsi'] = ta.rsi(df['close'], length=14)
        last_price = df['close'].iloc[-1]
        last_ema = df['ema200'].iloc[-1]
        last_rsi = df['rsi'].iloc[-1]
        if last_price > last_ema and last_rsi < 35: return "BUY", last_price
        elif last_price < last_ema and last_rsi > 70: return "SELL", last_price
        else: return "WAIT", last_price
    except: return "ERROR", 0

@app.route('/')
def home():
    return send_file('index.html')

@app.route('/status', methods=['GET'])
def status():
    if STATE['running'] and STATE['exchange']:
        signal, price = get_accuracy_signal(STATE['exchange'], STATE['coin'])
        STATE['price'] = price
        STATE['message'] = f"Strategy: {signal} | Trend: {'UP' if price > 0 else 'CHECKING'}"
    return jsonify(STATE)

@app.route('/start', methods=['POST'])
def start():
    data = request.get_json()
    try:
        ex_class = getattr(ccxt, data['exchange'])
        STATE['exchange'] = ex_class({'apiKey': data['apiKey'], 'secret': data['apiSecret'], 'enableRateLimit': True})
        STATE['coin'] = data.get('coin', 'BTC/USDT')
        STATE['running'] = True
        return jsonify({"status": "success"})
    except: return jsonify({"status": "error", "message": "Invalid Keys"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
