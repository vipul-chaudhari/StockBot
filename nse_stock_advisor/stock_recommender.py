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

def ultra_refined_analysis(ticker, is_crypto=False):
    try:
        # Fetch Intraday 1-Hour data (last 7 days)
        interval = "1h"
        period = "1mo" if is_crypto else "7d"
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        
        if data.empty or len(data) < 30: return None
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)

        # 1. VWAP (The Institutional Support)
        # Note: ta.vwap requires 'anchor' - we use daily reset for VWAP
        data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])
        
        # 2. SuperTrend (Volatility + Trend)
        # Returns: Trend (1 or -1), Direction, Long/Short values
        st = ta.supertrend(data['High'], data['Low'], data['Close'], length=10, multiplier=3.0)
        data['ST_Trend'] = st['SUPERT_10_3.0']
        data['ST_Dir'] = st['SUPERTd_10_3.0'] # 1 is Long, -1 is Short

        # 3. RSI for Overbought/Oversold check
        data['RSI'] = ta.rsi(data['Close'], length=14)
        
        # Current Values
        cp = float(data['Close'].iloc[-1])
        vwap = float(data['VWAP'].iloc[-1])
        st_dir = int(data['ST_Dir'].iloc[-1])
        rsi = float(data['RSI'].iloc[-1])
        
        # Potential upside to recent 3-day high
        recent_high = float(data['High'].tail(24).max()) 
        potential = ((recent_high - cp) / cp) * 100

        # --- THE GOLDEN ENTRY RULES ---
        # A. Price MUST be above VWAP (Institutional Buying)
        # B. SuperTrend MUST be in a 'Long' direction (1)
        # C. RSI should be between 45 and 65 (Strength, not yet overbought)
        
        score = 0
        if cp > vwap: score += 2  # VWAP is high weight
        if st_dir == 1: score += 2 # SuperTrend is high weight
        if 45 < rsi < 65: score += 1
        
        # Volume Spike Check
        avg_vol = data['Volume'].tail(20).mean()
        if data['Volume'].iloc[-1] > (avg_vol * 1.2): score += 1

        if score >= 4:
            return {
                "ticker": ticker,
                "price": cp,
                "potential": potential,
                "score": score,
                "rsi": rsi,
                "is_crypto": is_crypto
            }
        return None
    except Exception as e:
        print(f"Error {ticker}: {e}")
        return None

def send_telegram_msg(stock_recs, crypto_recs, chat_id):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%d %b, %Y %H:%M')
    text = f"🎯 *ULTRA-VALID ADVISOR - {now} IST*\n"
    text += "_System: 1h VWAP + SuperTrend Strategy_\n\n"
    
    if stock_recs:
        text += "📈 *NSE STOCKS (PRO-SIGNALS)*\n"
        for s in stock_recs:
            score_label = "🔥🔥" if s['score'] >= 5 else "🔥"
            text += f"• `{s['ticker']}`: ₹{s['price']:.0f} | Target: +{s['potential']:.1f}% {score_label}\n"
        text += "\n"
        
    if crypto_recs:
        text += "🪙 *CRYPTO (PRO-SIGNALS)*\n"
        for c in crypto_recs:
            score_label = "🔥🔥" if c['score'] >= 5 else "🔥"
            text += f"• `{c['ticker'].replace('-USD','')}`: ${c['price']:.2f} | Target: +{c['potential']:.1f}% {score_label}\n"
        text += "\n"

    if not stock_recs and not crypto_recs:
        text += "📉 Waiting for high-probability setups..."

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    is_weekday = now_ist.weekday() < 5
    is_market_hours = 9 <= now_ist.hour < 21

    stock_results = []
    if is_weekday and is_market_hours:
        print("Analyzing NSE Stocks (Intraday)...")
        for t in STOCK_TICKERS:
            res = ultra_refined_analysis(t, is_crypto=False)
            if res: stock_results.append(res)
    
    crypto_results = []
    print("Analyzing Crypto (Intraday)...")
    for t in CRYPTO_TICKERS:
        res = ultra_refined_analysis(t, is_crypto=True)
        if res: crypto_results.append(res)
    
    # Sort by score (confidence) and potential
    stock_results = sorted(stock_results, key=lambda x: (x['score'], x['potential']), reverse=True)[:6]
    crypto_results = sorted(crypto_results, key=lambda x: (x['score'], x['potential']), reverse=True)[:6]
    
    send_telegram_msg(stock_results, crypto_results, TELEGRAM_CHAT_ID)
    print("Done.")
