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
    "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "POL-USD", "SHIB-USD"
]

def analyze_assets(tickers, is_crypto=False):
    results = []
    print(f"Analyzing {len(tickers)} {'cryptos' if is_crypto else 'stocks'}...")
    for ticker in tickers:
        try:
            period = "1mo" if is_crypto else "1y"
            data = yf.download(ticker, period=period, interval="1d", progress=False)
            if data.empty or len(data) < 14: continue
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            
            data['RSI'] = ta.rsi(data['Close'], length=14)
            data['EMA_5'] = ta.ema(data['Close'], length=5)
            
            cp = float(data['Close'].iloc[-1])
            rsi = float(data['RSI'].iloc[-1])
            ema5 = float(data['EMA_5'].iloc[-1])
            
            # Potential Profit calculation (Upside to 14-day high)
            recent_high = float(data['High'].tail(14).max())
            potential_profit = ((recent_high - cp) / cp) * 100

            # CRITERIA
            if is_crypto:
                # Relaxed Crypto Criteria: RSI < 45 or RSI > 55
                if (rsi < 45 or rsi > 55) and cp > ema5:
                    results.append((ticker, cp, rsi, potential_profit))
            else:
                if rsi < 45 and cp > ema5:
                    results.append((ticker, cp, rsi, potential_profit))
        except: continue
    return sorted(results, key=lambda x: x[3], reverse=True)[:10]

def send_telegram_msg(stock_recs, crypto_recs, chat_id):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%d %b, %Y %H:%M')
    text = f"🚀 *DAILY ADVISOR - {now} IST*\n\n"
    
    if not stock_recs and not crypto_recs:
        text += "📉 No clear signals identified at this time."
    else:
        if stock_recs:
            text += "📈 *TOP STOCK SWINGS (NSE)*\n"
            for s in stock_recs:
                text += f"• `{s[0]}`: ₹{s[1]:.0f} | Target: +{s[3]:.1f}%\n"
            text += "\n"
        
        if crypto_recs:
            text += "🪙 *TOP CRYPTO SIGNALS*\n"
            for c in crypto_recs:
                text += f"• `{c[0].replace('-USD','')}`: ${c[1]:,.2f} | Target: +{c[3]:.1f}%\n"
            text += "\n"

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    is_weekday = now_ist.weekday() < 5
    is_market_hours = 9 <= now_ist.hour < 21

    stock_results = []
    if is_weekday and is_market_hours:
        stock_results = analyze_assets(STOCK_TICKERS, is_crypto=False)
    
    crypto_results = analyze_assets(CRYPTO_TICKERS, is_crypto=True)
    
    # Send message even if results are empty to show the bot is active
    send_telegram_msg(stock_results, crypto_results, TELEGRAM_CHAT_ID)
    print("Done.")
