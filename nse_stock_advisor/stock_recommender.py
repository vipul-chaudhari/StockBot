import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import datetime
import os

# --- CONFIGURATION (GET THESE FROM ENVIRONMENT) ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8757431245:AAHjis0btm24n0Q_WIh4GZYY-b-ToYyZKyU')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '8552505296')

# --- TICKERS (Expanded to Nifty 100 for better selection) ---
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

def analyze_stocks(tickers):
    results = {"Intraday": [], "Short-term": [], "Long-term": []}
    print(f"Analyzing {len(tickers)} stocks...")
    
    for ticker in tickers:
        try:
            # Fetch last 1 year for long-term indicators
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            if data.empty or len(data) < 200: continue
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Indicators
            data['RSI'] = ta.rsi(data['Close'], length=14)
            data['EMA_5'] = ta.ema(data['Close'], length=5)
            data['SMA_200'] = ta.sma(data['Close'], length=200)
            
            cp = float(data['Close'].iloc[-1])
            rsi = float(data['RSI'].iloc[-1])
            ema5 = float(data['EMA_5'].iloc[-1])
            sma200 = float(data['SMA_200'].iloc[-1])
            vol_ratio = float(data['Volume'].iloc[-1] / data['Volume'].tail(10).mean())

            # 1. INTRADAY (High Momentum + Vol)
            if rsi > 65 and vol_ratio > 1.2:
                results["Intraday"].append((ticker, cp, rsi))

            # 2. SHORT-TERM (Swing / Mean Reversion)
            if rsi < 45 and cp > ema5:
                results["Short-term"].append((ticker, cp, rsi))

            # 3. LONG-TERM (Trend Following)
            if cp > sma200 and rsi > 50:
                results["Long-term"].append((ticker, cp, rsi))
                
        except Exception as e:
            print(f"Error {ticker}: {e}")

    # Sort and take top 10 for each
    for key in results:
        results[key] = sorted(results[key], key=lambda x: x[2], reverse=(key!="Short-term"))[:10]
        
    return results

def send_telegram_msg(results):
    now = datetime.datetime.now().strftime('%d %b, %Y')
    text = f"📊 *NSE RECOMMENDATIONS - {now}*\n\n"
    
    for category, stocks in results.items():
        text += f"📍 *{category.upper()} (Top {len(stocks)})*\n"
        if not stocks:
            text += "No clear signals today.\n"
        else:
            for s in stocks:
                text += f"• `{s[0]}`: ₹{s[1]:.0f} (RSI: {s[2]:.1f})\n"
        text += "\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    print("Report sent to Telegram!")

if __name__ == "__main__":
    recs = analyze_stocks(TICKERS)
    send_telegram_msg(recs)
