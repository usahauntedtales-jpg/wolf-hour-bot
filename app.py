import ccxt
import pandas as pd
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# --- Naya Performance State ---
STATE = {
    "running": False,
    "exchange": None,
    "coin": "BTC/USDT",
    "price": 0.0,
    "message": "Waiting for Bitget Keys...",
    "wins": 0,
    "loss": 0,
    "profit_pct": 0.0,
    "total_trades": 0
}

def get_performance_stats(exchange, symbol):
    try:
        # Live Price aur RSI check
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        last_price = df['c'].iloc[-1]
        
        # Win/Loss logic (Bitget se closed trades uthayega)
        # Abhi ke liye hum ise tracker mein save rakhenge
        return last_price
    except:
        return 0

@app.route('/')
def home():
    return send_file('index.html')

@app.route('/status', methods=['GET'])
def status():
    if STATE['running'] and STATE['exchange']:
        price = get_performance_stats(STATE['exchange'], STATE['coin'])
        STATE['price'] = price
        # Win Rate calculation
        wr = (STATE['wins'] / STATE['total_trades'] * 100) if STATE['total_trades'] > 0 else 0
        STATE['message'] = f"Wins: {STATE['wins']} | Loss: {STATE['loss']} | Win Rate: {wr:.1f}%"
    return jsonify(STATE)

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
    
