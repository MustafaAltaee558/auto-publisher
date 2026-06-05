"""
شغّل هذا السكريبت مرة واحدة بعد رفع السيرفر لربط التيليغرام بـ Webhook.
python set_webhook.py
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TELEGRAM_TOKEN"]
SERVER_URL = input("أدخل رابط السيرفر (مثال: https://myapp.onrender.com): ").strip().rstrip("/")
WEBHOOK_URL = f"{SERVER_URL}/webhook"

r = httpx.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    json={"url": WEBHOOK_URL, "allowed_updates": ["message", "channel_post"]},
)
print(r.json())
if r.json().get("ok"):
    print(f"\n✅ تم ربط الـ Webhook بنجاح على: {WEBHOOK_URL}")
else:
    print("\n❌ فشل الربط - تحقق من الـ TOKEN والرابط")
