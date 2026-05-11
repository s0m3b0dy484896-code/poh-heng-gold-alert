import os
import re
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POH_HENG_URL = "https://pohheng.com.sg/"
STATE_FILE = "last_price.json"


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise Exception("Missing Telegram secrets")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=payload, timeout=30)
    response.raise_for_status()


def get_poh_heng_price():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(POH_HENG_URL, headers=headers, timeout=30)
    response.raise_for_status()

    text = response.text

    match = re.search(
        r"22K\s*/\s*916\.67\s*at\s*\$([\d,.]+)\s*per gram\s*\|\s*24K\s*/\s*999\s*at\s*\$([\d,.]+)\s*per gram",
        text,
        re.IGNORECASE
    )

    if not match:
        raise Exception("Cannot find Poh Heng gold price on website")

    price_22k = float(match.group(1).replace(",", ""))
    price_24k = float(match.group(2).replace(",", ""))

    return {
        "22K": price_22k,
        "24K": price_24k
    }


def load_last_price():
    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_price(price):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(price, f, indent=2)


def build_change_text(old_price, new_price):
    lines = []

    for key in ["22K", "24K"]:
        old = old_price.get(key)
        new = new_price.get(key)

        if old != new:
            diff = new - old

            if diff > 0:
                emoji = "📈"
                direction = "上升"
            else:
                emoji = "📉"
                direction = "下降"

            lines.append(
                f"{emoji} {key}: ${old:.2f} → ${new:.2f} "
                f"({direction} ${abs(diff):.2f}/gram)"
            )

    return "\n".join(lines)


def main():
    sg_time = datetime.now(
        ZoneInfo("Asia/Singapore")
    ).strftime("%Y-%m-%d %H:%M:%S")

    new_price = get_poh_heng_price()
    old_price = load_last_price()

    if old_price is None:
        save_price(new_price)

        message = f"""🟡 Poh Heng Gold Price Tracker Started

22K / 916.67:
${new_price["22K"]:.2f}/gram

24K / 999:
${new_price["24K"]:.2f}/gram

⏰ Singapore Time:
{sg_time}

下一次開始，如果價格有變動才會通知你。
"""

        send_telegram(message)
        return

    if old_price == new_price:
        print("No price change.")
        return

    change_text = build_change_text(old_price, new_price)
    save_price(new_price)

    message = f"""🔔 Poh Heng Gold Price Changed

{change_text}

Current Price:
22K / 916.67: ${new_price["22K"]:.2f}/gram
24K / 999: ${new_price["24K"]:.2f}/gram

⏰ Singapore Time:
{sg_time}
"""

    send_telegram(message)


if __name__ == "__main__":
    main()
