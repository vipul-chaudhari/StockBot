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

# List of Chat IDs (Your Private ID + Group ID)
TELEGRAM_CHAT_IDS = ['8552505296', '-1003818653543']

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

def analyze_professional(ticker, mode="Intraday"):
    try:
        interval = "1h" if mode == "Intraday" else "1d"
        period = "1mo" if mode == "Intraday" else "2y"
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty or len(data) < 30: return None
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)

        data['RSI'] = ta.rsi(data['Close'], length=14)
        data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
        cp, rsi, atr = float(data['Close'].iloc[-1]), float(data['RSI'].iloc[-1]), float(data['ATR'].iloc[-1])
        vol_ratio = data['Volume'].iloc[-1] / data['Volume'].tail(20).mean()

        if mode == "Intraday":
            data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])
            st = ta.supertrend(data['High'], data['Low'], data['Close'], length=10, multiplier=3.0)
            vwap = float(data['VWAP'].iloc[-1])
            st_dir = int(st['SUPERTd_10_3.0'].iloc[-1])
            if cp > vwap and st_dir == 1 and vol_ratio > 1.3 and 50 < rsi < 75:
                sl = cp - (atr * 1.5)
                tp = cp + ((cp - sl) * 2)
                return {"ticker": ticker, "entry": cp, "sl": sl, "tp": tp}

        elif mode == "Swing":
            data['EMA20'] = ta.ema(data['Close'], length=20)
            data['EMA50'] = ta.ema(data['Close'], length=50)
            e20, e50 = float(data['EMA20'].iloc[-1]), float(data['EMA50'].iloc[-1])
            if e20 > e50 and cp > e20 and rsi > 55 and vol_ratio > 1.1:
                sl = cp - (atr * 2.0)
                tp = cp + ((cp - sl) * 3)
                return {"ticker": ticker, "entry": cp, "sl": sl, "tp": tp}

        elif mode == "LongTerm":
            data['SMA200'] = ta.sma(data['Close'], length=200)
            s200 = float(data['SMA200'].iloc[-1])
            if cp > s200 and rsi > 50 and cp > (s200 * 1.05):
                sl = cp - (atr * 3.0)
                tp = cp + ((cp - sl) * 5)
                return {"ticker": ticker, "entry": cp, "sl": sl, "tp": tp}
        return None
    except: return None

def send_professional_msg(results, chat_ids):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%d %b, %Y %H:%M')
    text = f"🏛️ *THE PROFESSIONAL TRADING DESK*\nTime: {now} IST\n────────────────────\n\n"
    
    has_content = False
    for mode in ["Intraday", "Swing", "LongTerm"]:
        mode_results = results.get(mode, [])
        if mode_results:
            has_content = True
            icon = "⚡" if mode == "Intraday" else "🌊" if mode == "Swing" else "💎"
            text += f"{icon} *{mode.upper()} CALLS*\n"
            for r in mode_results:
                ticker = r['ticker'].replace('.NS', '').replace('-USD', '')
                curr = "₹" if ".NS" in r['ticker'] else "$"
                text += f"• `{ticker}` | Entry: {curr}{r['entry']:.2f}\n  Target: {curr}{r['tp']:.2f} | SL: {curr}{r['sl']:.2f}\n"
            text += "\n"

    if not has_content:
        text += "🛡️ *CAPITAL PRESERVATION MODE*\nMarket conditions are sideways. Protect your capital."

    for chat_id in chat_ids:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    is_market_open = (now_ist.weekday() < 5 and 9 <= now_ist.hour < 21)
    final_results = {"Intraday": [], "Swing": [], "LongTerm": []}
    
    if is_market_open:
        for t in STOCK_TICKERS:
            for m in ["Intraday", "Swing", "LongTerm"]:
                res = analyze_professional(t, m)
                if res: final_results[m].append(res)
    
    for t in CRYPTO_TICKERS:
        for m in ["Intraday", "Swing", "LongTerm"]:
            res = analyze_professional(t, m)
            if res: final_results[m].append(res)

    for m in final_results: final_results[m] = final_results[m][:3]
    send_professional_msg(final_results, TELEGRAM_CHAT_IDS)
    print("Market Advisory Dispatched to all chats.")
