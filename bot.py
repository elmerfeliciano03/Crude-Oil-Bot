"""
Crude Oil Price Alert Bot - Telegram
Sends alert when CL=F reaches your target price
"""

import os
import logging
import requests
import time
import yfinance as yf
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ============ CONFIGURATION ============
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ============ PRICE TARGETS (MODIFY THESE) ============
# Set your desired price targets for Crude Oil
TARGETS = {
    "alert_above": 1.00,    # Alert when price goes ABOVE this
    "alert_below": 100.00,    # Alert when price goes BELOW this
    "exact_price": 96.00,    # Alert when price hits EXACTLY this (within 0.05)
}

# Track if alerts were already sent to avoid spam
alert_state = {
    "above_triggered": False,
    "below_triggered": False,
    "exact_triggered": False
}

# Alert cooldown (prevents repeated alerts)
ALERT_COOLDOWN = 3600  # 1 hour between same type of alerts

# ============ HELPER FUNCTIONS ============
def get_crude_oil_price():
    """Fetch current Crude Oil price from Yahoo Finance"""
    try:
        ticker = yf.Ticker("CL=F")
        
        # Try fast_info first (faster)
        try:
            fast_info = ticker.fast_info
            if hasattr(fast_info, 'last_price') and fast_info.last_price:
                return float(fast_info.last_price)
        except:
            pass
        
        # Fallback to history
        data = ticker.history(period="1d", interval="5m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
        
        return None
    except Exception as e:
        log.error(f"Error fetching price: {e}")
        return None

def send_telegram(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        r.raise_for_status()
        log.info("✅ Telegram sent")
        return True
    except Exception as e:
        log.error(f"Telegram failed: {e}")
        return False

def check_cooldown(alert_type):
    """Check if alert type is in cooldown"""
    cooldown_file = "/tmp/alert_cooldown.txt"
    try:
        with open(cooldown_file, 'r') as f:
            for line in f:
                if line.startswith(f"{alert_type}:"):
                    last = float(line.split(':')[1])
                    if (datetime.now().timestamp() - last) < ALERT_COOLDOWN:
                        return True
    except:
        pass
    return False

def save_cooldown(alert_type):
    """Save cooldown timestamp"""
    cooldown_file = "/tmp/alert_cooldown.txt"
    try:
        with open(cooldown_file, 'a') as f:
            f.write(f"{alert_type}:{datetime.now().timestamp()}\n")
    except:
        pass

# ============ ALERT MESSAGES ============
def build_alert_message(alert_type, current_price, target):
    """Build alert message based on alert type"""
    emoji = "🔴" if alert_type == "above" else "🔵" if alert_type == "below" else "🎯"
    
    if alert_type == "above":
        title = f"{emoji} PRICE SPIKED ABOVE TARGET!"
        details = f"Crude Oil exploded to <b>${current_price:.2f}</b>"
    elif alert_type == "below":
        title = f"{emoji} PRICE DROPPED BELOW TARGET!"
        details = f"Crude Oil fell to <b>${current_price:.2f}</b>"
    else:
        title = f"{emoji} PRICE HIT EXACT TARGET!"
        details = f"Crude Oil reached <b>${current_price:.2f}</b>"
    
    message = f"""<b>{title}</b>

<b>🛢️ Crude Oil (CL=F)</b>
{details}

<b>🎯 Your Target:</b> ${target:.2f}
<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC

<code>Consider taking action according to your trading plan!</code>"""
    
    return message

# ============ MAIN LOOP ============
def main():
    log.info("=" * 50)
    log.info("🛢️ CRUDE OIL PRICE ALERT BOT")
    log.info("=" * 50)
    log.info(f"Alert Targets:")
    log.info(f"  • Above: ${TARGETS['alert_above']:.2f}")
    log.info(f"  • Below: ${TARGETS['alert_below']:.2f}")
    log.info(f"  • Exact: ${TARGETS['exact_price']:.2f}")
    log.info("=" * 50)
    
    # Send startup confirmation
    startup_msg = f"""<b>🛢️ Crude Oil Alert Bot Activated!</b>

Monitoring CL=F with targets:
• 🔴 Above: ${TARGETS['alert_above']:.2f}
• 🔵 Below: ${TARGETS['alert_below']:.2f}
• 🎯 Exact: ${TARGETS['exact_price']:.2f}

I'll alert you when price reaches any target!"""
    send_telegram(startup_msg)
    
    last_price = None
    
    while True:
        current_price = get_crude_oil_price()
        
        if current_price is not None:
            log.info(f"📊 Current Crude Oil: ${current_price:.2f}")
            
            # Check ABOVE target
            if current_price >= TARGETS["alert_above"]:
                if not check_cooldown("above"):
                    send_telegram(build_alert_message("above", current_price, TARGETS["alert_above"]))
                    save_cooldown("above")
                    log.info(f"🔔 ALERT: Price ${current_price:.2f} is above ${TARGETS['alert_above']:.2f}")
            
            # Check BELOW target
            if current_price <= TARGETS["alert_below"]:
                if not check_cooldown("below"):
                    send_telegram(build_alert_message("below", current_price, TARGETS["alert_below"]))
                    save_cooldown("below")
                    log.info(f"🔔 ALERT: Price ${current_price:.2f} is below ${TARGETS['alert_below']:.2f}")
            
            # Check EXACT target (within 0.05)
            if abs(current_price - TARGETS["exact_price"]) <= 0.05:
                if not check_cooldown("exact"):
                    send_telegram(build_alert_message("exact", current_price, TARGETS["exact_price"]))
                    save_cooldown("exact")
                    log.info(f"🔔 ALERT: Price hit target ${TARGETS['exact_price']:.2f}")
            
            # Optional: Send price update every hour
            if last_price is None or abs(current_price - last_price) >= 1.00:
                log.info(f"💰 Price changed to ${current_price:.2f}")
                last_price = current_price
        
        # Check every 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    main()
