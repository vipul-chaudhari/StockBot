import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import datetime
import os
import time
import pytz
import matplotlib.pyplot as plt
import mplfinance as mpf
import io

# --- CONFIGURATION (GITHUB SECRETS RECOMMENDED) ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or '8757431245:AAHjis0btm24n0Q_WIh4GZYY-b-ToYyZKyU'

# Load Chat IDs from env (comma separated) or use defaults
# FIXED: Checking both singular and plural env variable names for compatibility
env_ids = os.getenv('TELEGRAM_CHAT_IDS') or os.getenv('TELEGRAM_CHAT_ID')
if env_ids:
    TELEGRAM_CHAT_IDS = [id.strip() for id in env_ids.split(',')]
else:
    # Defaults: Your Private ID + GrowHigh Group ID
    TELEGRAM_CHAT_IDS = ['8552505296', '-1003818653543']
# ----------------------------------------------------

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

def generate_professional_chart(ticker, df, res):
    """Generates a professional financial chart for the signal."""
    try:
        plot_df = df.tail(40).copy()
        mc = mpf.make_marketcolors(up='#26a69a', down='#ef5350', inherit=True)
        s = mpf.make_mpf_style(base_mpf_style='charles', marketcolors=mc, gridstyle='--')
        
        # Overlay lines
        entry_l = [res['entry']] * len(plot_df)
        tp_l = [res['tp']] * len(plot_df)
        sl_l = [res['sl']] * len(plot_df)
        
        apds = [
            mpf.make_addplot(entry_l, color='gold', width=1, linestyle='-'),
            mpf.make_addplot(tp_l, color='lime', width=1.2, linestyle='--'),
            mpf.make_addplot(sl_l, color='red', width=1.2, linestyle='--')
        ]
        
        buf = io.BytesIO()
        mpf.plot(plot_df, type='candle', style=s, addplot=apds,
                 title=f"\n{ticker} Analysis",
                 savefig=dict(fname=buf, format='png', bbox_inches='tight'))
        buf.seek(0)
        return buf
    except: return None

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

        res = None
        if mode == "Intraday":
            data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])
            st = ta.supertrend(data['High'], data['Low'], data['Close'], length=10, multiplier=3.0)
            vwap = float(data['VWAP'].iloc[-1])
            st_dir = int(st['SUPERTd_10_3.0'].iloc[-1])
            # RELAXED: vol_ratio > 1.0 (was 1.2)
            if cp > vwap and st_dir == 1 and vol_ratio > 1.0 and 40 < rsi < 80:
                sl = cp - (atr * 1.5)
                tp = cp + ((cp - sl) * 2)
                res = {"ticker": ticker, "entry": cp, "sl": sl, "tp": tp, "mode": mode, "rsi": rsi}

        elif mode == "Swing":
            data['EMA20'] = ta.ema(data['Close'], length=20)
            data['EMA50'] = ta.ema(data['Close'], length=50)
            e20, e50 = float(data['EMA20'].iloc[-1]), float(data['EMA50'].iloc[-1])
            if e20 > e50 and cp > e20 and rsi > 45:
                sl = cp - (atr * 2.0)
                tp = cp + ((cp - sl) * 3)
                res = {"ticker": ticker, "entry": cp, "sl": sl, "tp": tp, "mode": mode, "rsi": rsi}

        if res:
            res['chart'] = generate_professional_chart(ticker, data, res)
            return res
        return None
    except: return None

def send_vip_signal(res):
    ticker_clean = res['ticker'].replace('.NS', '').replace('-USD', '')
    curr = "₹" if ".NS" in res['ticker'] else "$"
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%H:%M')
    
    risk = abs(res['entry'] - res['sl'])
    reward = abs(res['tp'] - res['entry'])
    rr = round(reward / risk, 1) if risk != 0 else 0

    caption = (
        f"🌟 *VIP SIGNAL: {ticker_clean}* 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 **STRATEGY:** `{res['mode'].upper()}`\n"
        f"📊 **RSI:** `{round(res['rsi'], 1)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 **ENTRY:** `{curr}{res['entry']:.2f}`\n"
        f"🎯 **TARGET:** `{curr}{res['tp']:.2f}`\n"
        f"🛑 **STOP LOSS:** `{curr}{res['sl']:.2f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚖️ **R/R RATIO:** `{rr}`\n"
        f"⏰ _Time: {now} IST_"
    )

    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            if res.get('chart'):
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", 
                              data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
                              files={'photo': ('chart.png', res['chart'], 'image/png')})
            else:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                              json={"chat_id": chat_id, "text": caption, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Error sending signal: {e}")

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    is_market_open = (now_ist.weekday() < 5 and 9 <= now_ist.hour < 16) # NSE hours
    
    # STATUS UPDATE: Send "Scan Started" message to Telegram so user knows bot is alive
    status_msg = f"🔍 *MARKET SCAN IN PROGRESS*\n⏰ IST: {now_ist.strftime('%H:%M:%S')}\n💹 Monitoring: {len(STOCK_TICKERS)} Stocks & {len(CRYPTO_TICKERS)} Crypto"
    for chat_id in TELEGRAM_CHAT_IDS:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": status_msg, "parse_mode": "Markdown"})

    print(f"Starting Professional Scan at {now_ist.strftime('%H:%M')} IST...")

    found_count = 0
    # Scan Stocks (only during NSE hours)
    if is_market_open:
        for t in STOCK_TICKERS:
            for m in ["Intraday", "Swing"]:
                res = analyze_professional(t, m)
                if res:
                    send_vip_signal(res)
                    found_count += 1
                    time.sleep(1)

    # Scan Crypto (24/7)
    for t in CRYPTO_TICKERS:
        for m in ["Intraday", "Swing"]:
            res = analyze_professional(t, m)
            if res:
                send_vip_signal(res)
                found_count += 1
                time.sleep(1)

    print(f"Scan Complete. Found {found_count} signals.")
