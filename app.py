import ccxt
import pandas as pd
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
import time

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION & STATE ---
STATE = {
    "running": False,
    "exchange": None,
    "coin": "BTC/USDT",
    "price": 0.0,
    "message": "System Online. Waiting for Bitget Keys...",
    "last_signal": "WAIT"
}

# --- HIGH TECH ACCURACY LOGIC (RSI + EMA) ---
def get_signals(exchange, symbol):
    try:
        # 15 min timeframe accuracy ke liye sabse best hai
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        
        # 1. EMA 200 Calculation (Trend Filter)
        ema200 = df['c'].ewm(span=200, adjust=False).mean().iloc[-1]
        
        # 2. RSI Calculation (Momentum Filter)
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        last_price = df['c'].iloc[-1]
        
        # SNIPER STRATEGY: 
        # Buy tabhi jab price EMA 200 ke upar ho (Uptrend) AUR RSI 35 se niche ho (Dip)
        if last_price > ema200 and rsi < 35:
            return "BUY", last_price, rsi
        # Sell tabhi jab price EMA 200 ke niche ho (Downtrend) AUR RSI 70 se upar ho (Peak)
        elif last_price < ema200 and rsi > 70:
            return "SELL", last_price, rsi
        else:
            return "WAIT", last_price, rsi
    except Exception as e:
        print(f"Signal Error: {e}")
        return "ERROR", 0, 0

# --- ROUTES ---
@app.route('/')
def home():
    # Ye file root folder mein honi chahiye
    return send_file('index.html')

@app.route('/status', methods=['GET'])
def status():
    if STATE['running'] and STATE['exchange']:
        signal, price, rsi = get_signals(STATE['exchange'], STATE['coin'])
        STATE['price'] = price
        STATE['last_signal'] = signal
        STATE['message'] = f"Signal: {signal} | RSI: {rsi:.2f} | Price: ${price}"
        
        # $10 Logic: Agar signal BUY hai, toh yahan execution logic trigger hoga
        if signal == "BUY":
            # Auto-trade logic for Bitget can be added here
            pass
            
    return jsonify(STATE)

@app.route('/start', methods=['POST'])
def start():
    data = request.get_json()
    try:
        # Bitget connection setup
        ex_name = data.get('exchange', 'bitget').lower()
        ex_class = getattr(ccxt, ex_name)
        
        STATE['exchange'] = ex_class({
            'apiKey': data['apiKey'],
            'secret': data['apiSecret'],
            'password': data.get('passphrase', ''), # Bitget ke liye zaroori hai
            'enableRateLimit': True
        })
        
        STATE['coin'] = data.get('coin', 'BTC/USDT')
        STATE['running'] = True
        return jsonify({"status": "success", "message": "Engine Started!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# --- RENDER PORT FIX ---
if __name__ == '__main__':
    # Render hamesha PORT environment variable mangta hai
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
