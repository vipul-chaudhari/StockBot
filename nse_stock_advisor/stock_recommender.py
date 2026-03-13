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

def refined_analysis(ticker, is_crypto=False):
    try:
        # Fetch 1 year of data for reliable indicators
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if data.empty or len(data) < 50: return None
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        # 1. Trend Indicators
        data['EMA20'] = ta.ema(data['Close'], length=20)
        data['EMA50'] = ta.ema(data['Close'], length=50)
        data['SMA200'] = ta.sma(data['Close'], length=200)
        
        # 2. Momentum Indicators
        data['RSI'] = ta.rsi(data['Close'], length=14)
        macd = ta.macd(data['Close'], fast=12, slow=26, signal=9)
        data['MACD'] = macd['MACD_12_26_9']
        data['MACDs'] = macd['MACDs_12_26_9']
        
        # 3. Volume & Trend Strength
        data['ADX'] = ta.adx(data['High'], data['Low'], data['Close'], length=14)['ADX_14']
        avg_vol = data['Volume'].tail(20).mean()
        curr_vol = data['Volume'].iloc[-1]
        
        # Current Values
        cp = float(data['Close'].iloc[-1])
        rsi = float(data['RSI'].iloc[-1])
        ema20 = float(data['EMA20'].iloc[-1])
        ema50 = float(data['EMA50'].iloc[-1])
        sma200 = float(data['SMA200'].iloc[-1])
        macd_val = float(data['MACD'].iloc[-1])
        macds_val = float(data['MACDs'].iloc[-1])
        adx = float(data['ADX'].iloc[-1])
        vol_ratio = curr_vol / avg_vol
        
        # Upside Potential (Target)
        high_90d = float(data['High'].tail(90).max())
        potential = ((high_90d - cp) / cp) * 100

        # --- REFINED STRATEGY ---
        # 1. Trend must be bullish: EMA20 > EMA50
        # 2. ADX > 20: Trend is strong enough
        # 3. Volume confirmation: Volume > 1.2x of Average
        # 4. Momentum: MACD > Signal Line OR RSI rebounding from 40
        
        score = 0
        if ema20 > ema50: score += 1
        if cp > sma200: score += 1
        if vol_ratio > 1.2: score += 1
        if macd_val > macds_val: score += 1
        if 40 < rsi < 70: score += 1
        if adx > 20: score += 1

        # Only recommend if confidence score is high (4 or more points out of 6)
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
    except:
        return None

def send_telegram_msg(stock_recs, crypto_recs, chat_id):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%d %b, %Y %H:%M')
    text = f"🛡️ *REFINED MARKET ADVISOR - {now} IST*\n"
    text += "_Strategy: Trend + Volume + MACD Confirmation_\n\n"
    
    if stock_recs:
        text += "📈 *STOCKS (HIGH CONFIDENCE)*\n"
        for s in stock_recs:
            stars = "⭐" * (s['score'] - 3)
            text += f"• `{s['ticker']}`: ₹{s['price']:.0f} | Target: +{s['potential']:.1f}% {stars}\n"
        text += "\n"
        
    if crypto_recs:
        text += "🪙 *CRYPTO (STRONG SIGNALS)*\n"
        for c in crypto_recs:
            stars = "⭐" * (c['score'] - 3)
            text += f"• `{c['ticker'].replace('-USD','')}`: ${c['price']:.2f} | Target: +{c['potential']:.1f}% {stars}\n"
        text += "\n"

    if not stock_recs and not crypto_recs:
        text += "📉 No high-confidence signals found right now. Markets are sideways."

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    is_weekday = now_ist.weekday() < 5
    is_market_hours = 9 <= now_ist.hour < 21

    stock_results = []
    if is_weekday and is_market_hours:
        print("Analyzing Stocks...")
        for t in STOCK_TICKERS:
            res = refined_analysis(t, is_crypto=False)
            if res: stock_results.append(res)
    
    crypto_results = []
    print("Analyzing Crypto...")
    for t in CRYPTO_TICKERS:
        res = refined_analysis(t, is_crypto=True)
        if res: crypto_results.append(res)
    
    # Sort by confidence score and then potential
    stock_results = sorted(stock_results, key=lambda x: (x['score'], x['potential']), reverse=True)[:8]
    crypto_results = sorted(crypto_results, key=lambda x: (x['score'], x['potential']), reverse=True)[:8]
    
    send_telegram_msg(stock_results, crypto_results, TELEGRAM_CHAT_ID)
    print("Done.")
