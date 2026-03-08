import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import datetime
import os
import time
import pytz

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or '8757431245:AAHjis0btm24n0Q_WIh4GZYY-b-ToYyZKyU'
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID') or '8552505296'

STOCK_TICKERS = [
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

CRYPTO_TICKERS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", 
    "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "LTC-USD", "SHIB-USD"
]

def analyze_crypto(tickers):
    st_results = []
    lt_results = []
    print(f"Analyzing {len(tickers)} cryptos...")
    
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            if data.empty or len(data) < 200: continue
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            
            data['RSI'] = ta.rsi(data['Close'], length=14)
            data['EMA_5'] = ta.ema(data['Close'], length=5)
            data['SMA_200'] = ta.sma(data['Close'], length=200)
            
            cp = float(data['Close'].iloc[-1])
            rsi = float(data['RSI'].iloc[-1])
            ema5 = float(data['EMA_5'].iloc[-1])
            sma200 = float(data['SMA_200'].iloc[-1])

            # 1. SHORT-TERM GOAL (7-day upside)
            if (rsi < 45 or rsi > 55) and cp > ema5:
                high_7d = float(data['High'].tail(7).max())
                profit_st = ((high_7d - cp) / cp) * 100
                st_results.append((ticker, cp, rsi, profit_st))

            # 2. LONG-TERM GOAL (90-day upside)
            if cp > sma200 and rsi > 50:
                high_90d = float(data['High'].tail(90).max())
                profit_lt = ((high_90d - cp) / cp) * 100
                lt_results.append((ticker, cp, rsi, profit_lt))
        except: continue
        
    return {
        "Short-term": sorted(st_results, key=lambda x: x[3], reverse=True)[:5],
        "Long-term": sorted(lt_results, key=lambda x: x[3], reverse=True)[:5]
    }

def analyze_stocks(tickers):
    results = []
    print(f"Analyzing {len(tickers)} stocks...")
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            if data.empty or len(data) < 14: continue
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            data['RSI'] = ta.rsi(data['Close'], length=14)
            data['EMA_5'] = ta.ema(data['Close'], length=5)
            cp, rsi, ema5 = float(data['Close'].iloc[-1]), float(data['RSI'].iloc[-1]), float(data['EMA_5'].iloc[-1])
            if rsi < 45 and cp > ema5:
                recent_high = float(data['High'].tail(14).max())
                profit = ((recent_high - cp) / cp) * 100
                results.append((ticker, cp, rsi, profit))
        except: continue
    return sorted(results, key=lambda x: x[3], reverse=True)[:10]

def send_telegram_msg(stock_recs, crypto_recs, chat_id):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%d %b, %Y %H:%M')
    text = f"🚀 *DAILY ADVISOR - {now} IST*\n\n"
    
    if stock_recs:
        text += "📈 *NSE STOCKS (SWING)*\n"
        for s in stock_recs:
            text += f"• `{s[0]}`: ₹{s[1]:.0f} | Target: +{s[3]:.1f}%\n"
        text += "\n"
        
    if crypto_recs["Short-term"]:
        text += "🪙 *CRYPTO (SHORT-TERM)*\n"
        for c in crypto_recs["Short-term"]:
            text += f"• `{c[0].replace('-USD','')}`: ${c[1]:,.2f} | Target: +{c[3]:.1f}%\n"
        text += "\n"

    if crypto_recs["Long-term"]:
        text += "💎 *CRYPTO (LONG-TERM)*\n"
        for c in crypto_recs["Long-term"]:
            text += f"• `{c[0].replace('-USD','')}`: ${c[1]:,.2f} | Target: +{c[3]:.1f}%\n"
        text += "\n"

    if not stock_recs and not crypto_recs["Short-term"] and not crypto_recs["Long-term"]:
        text += "📉 No clear signals identified at this time."

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    is_weekday = now_ist.weekday() < 5
    is_market_hours = 9 <= now_ist.hour < 21

    stock_results = []
    if is_weekday and is_market_hours:
        stock_results = analyze_stocks(STOCK_TICKERS)
    
    crypto_results = analyze_crypto(CRYPTO_TICKERS)
    
    send_telegram_msg(stock_results, crypto_results, TELEGRAM_CHAT_ID)
    print("Done.")
