import ccxt
import pandas as pd
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# State initialization
STATE = {
    "running": False,
    "exchange": None,
    "coin": "BTC/USDT",
    "price": 0.0,
    "message": "Wolf Engine Online! Waiting for Bitget Keys...",
}

def calculate_accuracy_signal(exchange, symbol):
    try:
        # Simple manual RSI calculation for accuracy
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        last_price = df['c'].iloc[-1]
        
        if rsi < 35: return "BUY", last_price
        elif rsi > 70: return "SELL", last_price
        return "WAIT", last_price
    except:
        return "ERROR", 0

@app.route('/')
def home():
    # Seedha file name use karo, Render ke liye yahi best hai
    return send_file('index.html')

@app.route('/status', methods=['GET'])
def status():
    if STATE['running'] and STATE['exchange']:
        signal, price = calculate_accuracy_signal(STATE['exchange'], STATE['coin'])
        STATE['price'] = price
        STATE['message'] = f"Strategy: {signal} | Price: ${price}"
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
    # Render ke liye default port 10000 hi rakho
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
