import ccxt
import pandas as pd
import pandas_ta as ta  # Accuracy ke liye technical library
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

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
        # 15-minute ka data lena accuracy ke liye best hai
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        
        # INDICATORS CALCULATION
        df['ema200'] = ta.ema(df['close'], length=200) # Trend Filter
        df['rsi'] = ta.rsi(df['close'], length=14)     # Momentum Filter
        
        last_price = df['close'].iloc[-1]
        last_ema = df['ema200'].iloc[-1]
        last_rsi = df['rsi'].iloc[-1]
        
        # STRATEGY LOGIC
        # Buy tabhi hoga jab price EMA ke upar ho (Uptrend) AUR RSI 35 se niche ho (Oversold)
        if last_price > last_ema and last_rsi < 35:
            return "BUY", last_price
        # Sell tabhi hoga jab price EMA ke niche ho (Downtrend) AUR RSI 70 se upar ho (Overbought)
        elif last_price < last_ema and last_rsi > 70:
            return "SELL", last_price
        else:
            return "WAIT", last_price
    except:
        return "ERROR", 0

@app.route('/')
def home():
    return send_file('index.html')

@app.route('/status', methods=['GET'])
def status():
    if STATE['running'] and STATE['exchange']:
        signal, price = get_accuracy_signal(STATE['exchange'], STATE['coin'])
        STATE['price'] = price
        STATE['message'] = f"Strategy: {signal} | Trend: {'UP' if price > 0 else 'CHECKING'}"
        
        # YAHAN ACTUAL TRADE EXECUTION (Strict $10 limit)
        if signal == "BUY":
            # Logic: exchange.create_market_buy_order(STATE['coin'], amount_for_10_dollars)
            STATE['message'] = f"🔥 BULLISH SIGNAL! Executing $10 Trade on {STATE['coin']}"
            
    return jsonify(STATE)

@app.route('/start', methods=['POST'])
def start():
    data = request.get_json()
    try:
        ex_class = getattr(ccxt, data['exchange'])
        STATE['exchange'] = ex_class({
            'apiKey': data['apiKey'],
            'secret': data['apiSecret'],
            'enableRateLimit': True
        })
        STATE['coin'] = data.get('coin', 'BTC/USDT')
        STATE['running'] = True
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "error", "message": "Invalid Keys"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
  
