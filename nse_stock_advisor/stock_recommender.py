import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import datetime
import os
import time

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8757431245:AAHjis0btm24n0Q_WIh4GZYY-b-ToYyZKyU')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '8552505296')

TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "INFY.NS", "SBIN.NS", "LICI.NS", "HINDUNILVR.NS", "ITC.NS",
    "LT.NS", "HCLTECH.NS", "BAJFINANCE.NS", "SUNPHARMA.NS", "M&M.NS",
    "ADANIENT.NS", "TATAMOTORS.NS", "KOTAKBANK.NS", "TITAN.NS", "MARUTI.NS",
    "AXISBANK.NS", "ASIANPAINT.NS", "ADANIPORTS.NS", "ULTRACEMCO.NS", "COALINDIA.NS",
    "BAJAJFINSV.NS", "NTPC.NS", "POWERGRID.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "HINDALCO.NS", "NESTLEIND.NS", "GRASIM.NS", "TECHM.NS", "ONGC.NS",
    "SBILIFE.NS", "WIPRO.NS", "HDFCLIFE.NS", "CIPLA.NS", "BRITANNIA.NS",
    "EICHERMOT.NS", "DRREDDY.NS", "TATACONSUM.NS", "APOLLOHOSP.NS", "BPCL.NS",
    "INDUSINDBK.NS", "SHRIRAMFIN.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "BEL.NS",
    "TRENT.NS", "HAL.NS", "VBL.NS", "DLF.NS", "JIOFIN.NS", "CHOLAFIN.NS", "ZOMATO.NS",
    "PNB.NS", "BANKBARODA.NS", "CANBK.NS", "GAIL.NS", "IRFC.NS", "RECLTD.NS", "PFC.NS"
]

def analyze_stocks():
    results = {"Intraday": [], "Short-term": [], "Long-term": []}
    print(f"Analyzing {len(TICKERS)} stocks...")
    for ticker in TICKERS:
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            if data.empty or len(data) < 200: continue
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            data['RSI'] = ta.rsi(data['Close'], length=14)
            data['EMA_5'] = ta.ema(data['Close'], length=5)
            data['SMA_200'] = ta.sma(data['Close'], length=200)
            cp, rsi, ema5, sma200 = float(data['Close'].iloc[-1]), float(data['RSI'].iloc[-1]), float(data['EMA_5'].iloc[-1]), float(data['SMA_200'].iloc[-1])
            vol_ratio = float(data['Volume'].iloc[-1] / data['Volume'].tail(10).mean())
            if rsi > 65 and vol_ratio > 1.2: results["Intraday"].append((ticker, cp, rsi))
            if rsi < 45 and cp > ema5: results["Short-term"].append((ticker, cp, rsi))
            if cp > sma200 and rsi > 50: results["Long-term"].append((ticker, cp, rsi))
        except: continue
    for key in results:
        results[key] = sorted(results[key], key=lambda x: x[2], reverse=(key!="Short-term"))[:10]
    return results

def send_telegram_msg(results, chat_id):
    now = datetime.datetime.now().strftime('%d %b, %Y %H:%M')
    text = f"📊 *NSE RECOMMENDATIONS - {now}*\n\n"
    for category, stocks in results.items():
        text += f"📍 *{category.upper()}*\n"
        if not stocks: text += "No clear signals.\n"
        else:
            for s in stocks: text += f"• `{s[0]}`: ₹{s[1]:.0f} (RSI: {s[2]:.1f})\n"
        text += "\n"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def handle_listener():
    last_update_id = 0
    print("Bot is listening for messages...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id + 1}"
            response = requests.get(url).json()
            if response['ok'] and response['result']:
                for update in response['result']:
                    last_update_id = update['update_id']
                    if 'message' in update:
                        chat_id = update['message']['chat']['id']
                        print(f"Received ping from {chat_id}. Processing recommendations...")
                        recs = analyze_stocks()
                        send_telegram_msg(recs, chat_id)
            time.sleep(10) # Check every 10 seconds
        except Exception as e:
            print(f"Error in listener: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # If run normally (from GitHub Cron), it sends once.
    # To use as a bot, run 'python stock_recommender.py listen'
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'listen':
        handle_listener()
    else:
        recs = analyze_stocks()
        send_telegram_msg(recs, TELEGRAM_CHAT_ID)
