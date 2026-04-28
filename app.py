import streamlit as st
import yfinance as yf
from google import genai
import requests
import base64
from datetime import datetime, time
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
import pytz

st.set_page_config(
    page_title="Utilities Trading Agent",
    page_icon="⚡",
    layout="wide"
)

st.markdown('<meta http-equiv="refresh" content="1800">', unsafe_allow_html=True)

uk_tz = pytz.timezone('Europe/London')
uk_now = datetime.now(uk_tz)

st.title("⚡ Utilities Trading Agent")
st.caption(f"Last updated: {uk_now.strftime('%d/%m/%Y %H:%M:%S')} (UK time)")
st.caption("⏱️ Auto refreshes every 30 minutes — Monitoring National Grid")
st.progress(1.0)

market_open = time(8, 0)
market_close = time(16, 30)
current_time = uk_now.time()
is_weekday = uk_now.weekday() < 5

if is_weekday and market_open <= current_time <= market_close:
    st.success("🟢 Market is OPEN — Live data active")
else:
    st.warning("🔴 Market is CLOSED — Showing last closing prices")

T212_API_KEY = st.secrets["T212_API_KEY"]
T212_API_SECRET = st.secrets["T212_API_SECRET"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
ALERT_EMAIL = st.secrets["ALERT_EMAIL"]

client = genai.Client(api_key=GEMINI_API_KEY)
credentials = f"{T212_API_KEY}:{T212_API_SECRET}"
encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
t212_headers = {"Authorization": f"Basic {encoded}"}
BASE_URL = "https://live.trading212.com/api/v0"

def safe_change(current, open_price):
    if open_price and open_price > 0:
        return ((current - open_price) / open_price) * 100
    return 0.0

def send_alert_email(alert_level, alert_msg, stock_name, current_price, todays_change, ai_analysis, gmail_address, gmail_password, alert_emails):
    try:
        recipients = [email.strip() for email in alert_emails.split(',')]
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 {stock_name} Alert: {alert_level}"
        msg['From'] = gmail_address
        msg['To'] = ', '.join(recipients)
        body = f"""
Utilities Trading Agent Alert — {stock_name}

Alert Level: {alert_level}
Message: {alert_msg}

Current Price: £{current_price:.2f}
Todays Change: {todays_change:.2f}%

AI Analysis:
{ai_analysis}

This is not financial advice.
        """
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, recipients, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False

st.subheader("💼 Your Trading 212 Account")
try:
    response = requests.get(f"{BASE_URL}/equity/account/cash", headers=t212_headers)
    if response.status_code == 200:
        cash = response.json()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Free Cash Available", f"£{cash.get('free', 0):,.2f}")
        with col2:
            st.metric("Account Status", "✅ Connected")
    else:
        st.error(f"Trading 212 connection failed: {response.status_code}")
except Exception as e:
    st.error(f"Error connecting to Trading 212: {e}")

st.divider()

ticker = "NG.L"
name = "National Grid"

stock = yf.Ticker(ticker)
history = stock.history(period="3mo")
info = stock.info

history['MA20'] = history['Close'].rolling(window=20).mean()
history['MA50'] = history['Close'].rolling(window=50).mean()

current_price = history['Close'].iloc[-1]
ma20 = history['MA20'].iloc[-1]
ma50 = history['MA50'].iloc[-1]
avg_volume = history['Volume'].mean()
current_volume = history['Volume'].iloc[-1]
volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
week52_high = history['High'].max()
week52_low = history['Low'].min()
distance_from_52high = ((current_price - week52_high) / week52_high) * 100
distance_from_52low = ((current_price - week52_low) / week52_low) * 100
open_price = info.get('open', 0)
todays_change = safe_change(current_price, open_price)

change_icon = "📈" if todays_change > 0 else "📉"
position = ((current_price - week52_low) / (week52_high - week52_low)) * 100
above_below = "above" if current_price > ma20 else "below"

if position >= 80:
    position_comment = "Near yearly high — be cautious"
    position_icon = "🔴"
elif position <= 30:
    position_comment = "Near yearly low — potential opportunity"
    position_icon = "🟢"
else:
    position_comment = "Mid range — watch for direction"
    position_icon = "🟡"

st.subheader("⚡ Utilities Snapshot")
st.markdown(
    f"**⚡ National Grid** | "
    f"{change_icon} £{current_price:.2f} ({todays_change:+.2f}%) | "
    f"{position_icon} {position:.0f}% of 52wk range — {position_comment} | "
    f"📊 Price is {above_below} 20 day average"
)

st.divider()

st.subheader("⚡ National Grid (NG.L)")
st.caption("🤖 AI Recommendation Active")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Current Price", f"£{current_price:.2f}", f"{todays_change:.2f}%")
with col2:
    st.metric("20 Day Average", f"£{ma20:.2f}")
with col3:
    st.metric("52 Week High", f"£{week52_high:.2f}")
with col4:
    st.metric("52 Week Low", f"£{week52_low:.2f}")

st.subheader("📋 Key Stats")
col1, col2, col3 = st.columns(3)
with col1:
    dividend_yield = info.get('dividendYield', 0)
    st.metric("Dividend Yield", f"{dividend_yield:.2f}%" if dividend_yield else "N/A")
with col2:
    pe_ratio = info.get('trailingPE', 0)
    st.metric("P/E Ratio", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
with col3:
    target_price = info.get('targetMeanPrice', 0)
    st.metric("Analyst Target", f"{target_price:.2f}p" if target_price else "N/A")

st.subheader("📈 90 Day Price Chart")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=history.index, y=history['Close'],
    name=name, line=dict(color='#00BFFF', width=2)
))
fig.add_trace(go.Scatter(
    x=history.index, y=history['MA20'],
    name='20 Day Average', line=dict(color='orange', width=1, dash='dash')
))
fig.add_trace(go.Scatter(
    x=history.index, y=history['MA50'],
    name='50 Day Average', line=dict(color='red', width=1, dash='dash')
))
fig.update_layout(
    height=400,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("🔔 Price Alert")
send_email = False
alert_level = ""
alert_msg = ""

if todays_change >= 10 or todays_change <= -10:
    alert_level = "🔴 RED ALERT"
    alert_msg = f"Extreme move of {todays_change:.2f}%"
    st.error(f"{alert_level}: {alert_msg}")
    send_email = True
elif todays_change >= 5 or todays_change <= -5:
    alert_level = "🟠 ORANGE ALERT"
    alert_msg = f"Strong move of {todays_change:.2f}%"
    st.warning(f"{alert_level}: {alert_msg}")
    send_email = True
elif todays_change >= 3 or todays_change <= -3:
    alert_level = "🟡 YELLOW ALERT"
    alert_msg = f"Moderate move of {todays_change:.2f}%"
    st.warning(f"{alert_level}: {alert_msg}")
    send_email = True
else:
    alert_level = "🟢 GREEN"
    alert_msg = f"Normal range — {'UP' if todays_change > 0 else 'DOWN'} {abs(todays_change):.2f}% today"
    st.success(f"{alert_level}: {alert_msg}")

st.subheader("📰 Latest News")
news = stock.news
headlines = []
for article in news[:5]:
    content = article.get('content', {})
    title = content.get('title', '')
    canonical = content.get('canonicalUrl', {})
    link = canonical.get('url', '')
    if title:
        headlines.append(title)
        st.markdown(f"📌 [{title}]({link})")
headlines_text = " | ".join(headlines)

st.subheader("🎯 News Sentiment")
positive_words = ['growth', 'profit', 'up', 'rise', 'gain', 'positive', 'strong',
                  'beat', 'exceed', 'record', 'high', 'deal', 'partner', 'win',
                  'expand', 'boost', 'surge', 'rally', 'outperform', 'infrastructure']
negative_words = ['fall', 'drop', 'loss', 'down', 'decline', 'negative', 'weak',
                  'miss', 'below', 'low', 'cut', 'reduce', 'risk', 'warn',
                  'debt', 'concern', 'struggle', 'slump', 'crash', 'regulatory']
positive_count = 0
negative_count = 0
for headline in headlines:
    headline_lower = headline.lower()
    for word in positive_words:
        if word in headline_lower:
            positive_count += 1
    for word in negative_words:
        if word in headline_lower:
            negative_count += 1
total = positive_count + negative_count
if total == 0:
    sentiment_score = 50
elif positive_count > negative_count:
    sentiment_score = min(50 + ((positive_count / total) * 50), 100)
else:
    sentiment_score = max(50 - ((negative_count / total) * 50), 0)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Positive Signals", f"✅ {positive_count}")
with col2:
    st.metric("Negative Signals", f"❌ {negative_count}")
with col3:
    if sentiment_score >= 65:
        st.metric("Overall Sentiment", "🟢 Positive")
    elif sentiment_score <= 35:
        st.metric("Overall Sentiment", "🔴 Negative")
    else:
        st.metric("Overall Sentiment", "🟡 Neutral")
st.progress(sentiment_score / 100)
st.caption(f"Sentiment score: {sentiment_score:.0f}/100")

st.subheader("🧠 AI Trading Recommendation")
with st.spinner("Analysing National Grid..."):
    prompt = (
        "You are an experienced trading analyst specialising in UK utility stocks. "
        "You are supporting a retail investor monitoring National Grid (LON: NG.). "
        "The investor prefers buying dips and selling when in profit, "
        "wants clear simple buy/sell/wait guidance in plain English. "
        "Key factors for National Grid: UK energy infrastructure investment, "
        "interest rate environment, regulatory decisions from Ofgem, "
        "government energy policy, and dividend sustainability. "
        "National Grid is a defensive stock — it tends to be more stable than the wider market. "
        f"Current Price: {current_price:.2f}p. "
        f"Todays Change: {todays_change:.2f}%. "
        f"20 Day Average: {ma20:.2f}p. "
        f"50 Day Average: {ma50:.2f}p. "
        f"Volume vs Normal: {volume_ratio:.2f}x. "
        f"From 52 week High: {distance_from_52high:.2f}%. "
        f"From 52 week Low: {distance_from_52low:.2f}%. "
        f"Latest News: {headlines_text}. "
        "Key rules: BUY when price is below 20 day average, volume normal or low, no bad news. "
        "SELL when price extended above averages near 52 week highs. "
        "WAIT when signals are mixed. "
        "Provide: 1. RECOMMENDATION: Buy/Sell/Wait. "
        "2. REASON: One clear sentence. "
        "3. KEY LEVEL TO WATCH: One specific price. "
        "4. RISK WARNING: One thing that could go wrong. "
        "Under 150 words, plain English, no jargon."
    )
    try:
        ai_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        ai_text = ai_response.text
        st.info(ai_text)

        if send_email:
            email_sent = send_alert_email(
                alert_level, alert_msg, name, current_price, todays_change,
                ai_text, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, ALERT_EMAIL
            )
            if email_sent:
                st.success("📧 Alert email sent!")
            else:
                st.warning("📧 Email alert could not be sent")

    except Exception:
        st.warning("⏳ AI analysis temporarily unavailable — will resume shortly")

st.subheader("📏 52 Week Position")
pos = ((current_price - week52_low) / (week52_high - week52_low))
st.progress(pos)
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"52wk Low: £{week52_low:.2f}")
with col2:
    st.caption(f"Current: £{current_price:.2f} ({pos*100:.0f}% of range)")
with col3:
    st.caption(f"52wk High: £{week52_high:.2f}")

st.divider()
st.subheader("📝 Trade Journal")

journal_file = "trade_journal.json"

def load_journal():
    if os.path.exists(journal_file):
        with open(journal_file, 'r') as f:
            return json.load(f)
    return []

journal = load_journal()

if journal:
    st.write("**Recent AI Recommendations:**")
    for entry in reversed(journal[-20:]):
        st.markdown(
            f"📅 **{entry['date']}** | "
            f"💰 {entry['price']} ({entry['change']}) | "
            f"{entry['alert']} | "
            f"🤖 {entry['recommendation']}"
        )
else:
    st.info("No recommendations recorded yet — journal will fill up as the agent runs.")

st.divider()
st.caption("⚠️ This tool is for informational purposes only and does not constitute financial advice.")
