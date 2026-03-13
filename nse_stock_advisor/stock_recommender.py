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

def check_macro_trend(ticker, is_crypto=False):
    """Higher Timeframe (Daily) Analysis to ensure we don't fight the trend."""
    try:
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if data.empty or len(data) < 200: return False
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        data['EMA20'] = ta.ema(data['Close'], length=20)
        data['EMA50'] = ta.ema(data['Close'], length=50)
        data['SMA200'] = ta.sma(data['Close'], length=200)
        
        cp = float(data['Close'].iloc[-1])
        e20 = float(data['EMA20'].iloc[-1])
        e50 = float(data['EMA50'].iloc[-1])
        s200 = float(data['SMA200'].iloc[-1])
        
        # PRO RULE 1: Must be in a long-term uptrend, short-term momentum aligned.
        if cp > s200 and e20 > e50 and cp > e20:
            return True
        return False
    except:
        return False

def institutional_grade_analysis(ticker, is_crypto=False):
    """Intraday execution criteria + Risk Management."""
    try:
        # 1. MACRO TREND FILTER (Skip if daily trend is bad)
        if not check_macro_trend(ticker, is_crypto):
            return None

        # 2. INTRADAY EXECUTION (1-Hour)
        period = "1mo" if is_crypto else "7d"
        data = yf.download(ticker, period=period, interval="1h", progress=False)
        if data.empty or len(data) < 30: return None
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)

        # Calculate Indicators
        data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])
        st = ta.supertrend(data['High'], data['Low'], data['Close'], length=10, multiplier=3.0)
        data['ST_Dir'] = st['SUPERTd_10_3.0'] 
        data['RSI'] = ta.rsi(data['Close'], length=14)
        data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
        
        cp = float(data['Close'].iloc[-1])
        vwap = float(data['VWAP'].iloc[-1])
        st_dir = int(data['ST_Dir'].iloc[-1])
        rsi = float(data['RSI'].iloc[-1])
        atr = float(data['ATR'].iloc[-1])
        
        avg_vol = data['Volume'].tail(20).mean()
        curr_vol = data['Volume'].iloc[-1]
        
        # PRO RULE 2: Intraday Institutional Confirmation
        # - Price > VWAP (Institutions are net buyers today)
        # - Supertrend is Long (Trend confirmation)
        # - Volume > 1.5x average (Real money is moving it)
        # - RSI between 50 and 70 (Strong, but not exhausted)
        
        if cp > vwap and st_dir == 1 and curr_vol > (avg_vol * 1.5) and 50 < rsi < 75:
            # RISK MANAGEMENT (1.5x ATR Stop, 1:2 Risk/Reward)
            stop_loss = cp - (atr * 1.5)
            risk = cp - stop_loss
            take_profit = cp + (risk * 2)
            
            return {
                "ticker": ticker,
                "entry": cp,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward": "1:2",
                "is_crypto": is_crypto
            }
        return None
    except:
        return None

def send_telegram_msg(stock_recs, crypto_recs, chat_id):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%d %b, %Y %H:%M')
    
    # Very stern, professional tone.
    text = f"🏛️ *INSTITUTIONAL DESK - {now} IST*\n"
    text += "_Strict MTFA + Volume + ATR Risk Management_\n\n"
    
    if stock_recs:
        text += "📈 *NSE EQUITIES (EXECUTION READY)*\n"
        for s in stock_recs:
            text += f"• `{s['ticker']}`\n"
            text += f"  Entry: ₹{s['entry']:.2f}\n"
            text += f"  Target (TP): ₹{s['take_profit']:.2f}\n"
            text += f"  Invalidation (SL): ₹{s['stop_loss']:.2f}\n\n"
        
    if crypto_recs:
        text += "🪙 *DIGITAL ASSETS (EXECUTION READY)*\n"
        for c in crypto_recs:
            text += f"• `{c['ticker'].replace('-USD','')}`\n"
            text += f"  Entry: ${c['entry']:.2f}\n"
            text += f"  Target (TP): ${c['take_profit']:.2f}\n"
            text += f"  Invalidation (SL): ${c['stop_loss']:.2f}\n\n"

    if not stock_recs and not crypto_recs:
        text += "🛡️ *CAPITAL PRESERVATION MODE*\n"
        text += "No assets meet the strict institutional criteria. Cash is a position. Protect your capital."

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    is_weekday = now_ist.weekday() < 5
    is_market_hours = 9 <= now_ist.hour < 21

    stock_results = []
    if is_weekday and is_market_hours:
        print("Executing Institutional Scan: NSE...")
        for t in STOCK_TICKERS:
            res = institutional_grade_analysis(t, is_crypto=False)
            if res: stock_results.append(res)
    
    crypto_results = []
    print("Executing Institutional Scan: Crypto...")
    for t in CRYPTO_TICKERS:
        res = institutional_grade_analysis(t, is_crypto=True)
        if res: crypto_results.append(res)
    
    send_telegram_msg(stock_results, crypto_results, TELEGRAM_CHAT_ID)
    print("Scan Complete.")
