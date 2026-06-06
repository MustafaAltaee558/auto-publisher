import os
import asyncio
import base64
import httpx
from openai import AsyncOpenAI
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="شفرة السكينة - نظام النشر التلقائي")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
MAKE_WEBHOOK_URL = os.environ["MAKE_WEBHOOK_URL"]

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}"

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# ─── Telegram helpers ────────────────────────────────────────────────────────

async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })


async def get_file_url(file_id: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        r.raise_for_status()
        file_path = r.json()["result"]["file_path"]
        return f"{TELEGRAM_FILE_API}/{file_path}"


async def download_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


# ─── OpenAI ───────────────────────────────────────────────────────────────────

PLATFORM_HINTS = {
    "facebook": "منشور فيسبوك طويل نسبياً (150-250 كلمة)، يبدأ بسؤال أو عبارة تشويقية",
    "instagram": "كابشن انستغرام قصير ومؤثر (80-120 كلمة)، ينتهي بـ call-to-action واضح",
    "tiktok": "نص تيك توك ديناميكي وسريع (50-70 كلمة)، بلغة شبابية وحماسية",
}

SYSTEM_PROMPT = """أنت خبير تسويق محتوى متخصص في تسويق كتب التطوير الذاتي.
الكتاب الذي تسوّق له اسمه "شفرة السكينة" - كتاب عربي يساعد القارئ على إيجاد السلام الداخلي والتحرر من القلق والتوتر.
أسلوبك: عاطفي، محفّز، صادق، يلمس الجرح ثم يقدم الأمل.
اكتب دائماً باللغة العربية الفصحى المبسطة."""


async def generate_marketing_text(media_bytes: bytes, mime_type: str, platform: str) -> str:
    platform_hint = PLATFORM_HINTS.get(platform, PLATFORM_HINTS["facebook"])
    hashtags = _hashtags_for(platform)

    prompt = f"""بناءً على الصورة المرفقة، اكتب نصاً تسويقياً احترافياً لكتاب "شفرة السكينة".
المنصة المستهدفة: {platform.upper()} — {platform_hint}.

الشروط:
- ابدأ مباشرة بالنص التسويقي بدون أي مقدمة أو شرح
- اجعل النص يتحدث عن الكتاب بشكل غير مباشر (كأنك تحكي قصة أو تطرح سؤالاً)
- أضف هذه الهاشتاقات في نهاية النص:
{hashtags}"""

    image_b64 = base64.b64encode(media_bytes).decode("utf-8")

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()


def _hashtags_for(platform: str) -> str:
    base = "#شفرة_السكينة #كتب_تطوير_الذات #السكينة_الداخلية #القلق #الراحة_النفسية"
    extra = {
        "facebook": " #كتب_عربية #تطوير_الذات",
        "instagram": " #books #selfhelp #اقرأ #كتاب",
        "tiktok": " #fyp #كتب_تيك_توك #بوك_توك",
    }
    return base + extra.get(platform, "")


# ─── Make Webhook ─────────────────────────────────────────────────────────────

async def send_to_make(chat_id: int, file_url: str, media_type: str, texts: dict):
    payload = {
        "chat_id": chat_id,
        "file_url": file_url,
        "facebook_text": texts["facebook"],
        "instagram_text": texts["instagram"],
    }

    logger.info("📤 إرسال للـ Make Webhook...")
    logger.info(f"   URL: {MAKE_WEBHOOK_URL}")
    logger.info(f"   chat_id: {chat_id}")
    logger.info(f"   file_url: {file_url}")
    logger.info(f"   facebook_text: {texts['facebook'][:80]}...")
    logger.info(f"   instagram_text: {texts['instagram'][:80]}...")

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(MAKE_WEBHOOK_URL, json=payload)
        logger.info(f"📥 رد Make — status: {r.status_code} | body: {r.text[:200]}")
        r.raise_for_status()

    logger.info("✅ تم الإرسال لـ Make بنجاح")


# ─── Processing pipeline ─────────────────────────────────────────────────────

async def process_media(chat_id: int, file_id: str, media_type: str, mime_type: str):
    try:
        await send_message(chat_id, "⏳ جاري تحليل المحتوى وكتابة النصوص...")

        file_url = await get_file_url(file_id)
        media_bytes = await download_bytes(file_url)

        # توليد النصوص للمنصات الثلاث بالتوازي
        fb_task = generate_marketing_text(media_bytes, mime_type, "facebook")
        ig_task = generate_marketing_text(media_bytes, mime_type, "instagram")
        tt_task = generate_marketing_text(media_bytes, mime_type, "tiktok")

        fb_text, ig_text, tt_text = await asyncio.gather(fb_task, ig_task, tt_task)

        texts = {"facebook": fb_text, "instagram": ig_text, "tiktok": tt_text}

        await send_message(chat_id, "✍️ تمت كتابة النصوص، جاري النشر على المنصات...")
        await send_to_make(chat_id, file_url, media_type, texts)
        await send_message(chat_id, "تم النشر ✅\n\nتم نشر المحتوى على فيسبوك وانستغرام وتيك توك بنجاح 🎉")

    except Exception as e:
        logger.error(f"خطأ في المعالجة: {e}")
        await send_message(chat_id, f"❌ حدث خطأ أثناء المعالجة:\n<code>{e}</code>")


# ─── Webhook endpoint ─────────────────────────────────────────────────────────

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message = data.get("message") or data.get("channel_post")
    if not message:
        return JSONResponse({"ok": True})

    chat_id = message["chat"]["id"]

    # صورة
    if "photo" in message:
        photo = message["photo"][-1]  # أعلى جودة
        asyncio.create_task(process_media(chat_id, photo["file_id"], "photo", "image/jpeg"))
        await send_message(chat_id, "📸 استلمت الصورة! جاري التحليل...")

    # فيديو
    elif "video" in message:
        video = message["video"]
        mime = video.get("mime_type", "video/mp4")
        asyncio.create_task(process_media(chat_id, video["file_id"], "video", mime))
        await send_message(chat_id, "🎬 استلمت الفيديو! جاري التحليل...")

    # رسائل نصية - مساعدة
    elif "text" in message:
        text = message["text"]
        if text == "/start":
            await send_message(chat_id,
                "مرحباً! 👋\n\n"
                "أنا بوت نشر محتوى كتاب <b>شفرة السكينة</b> 📖\n\n"
                "أرسل لي <b>صورة أو فيديو</b> وسأقوم بـ:\n"
                "1️⃣ تحليل المحتوى بالذكاء الاصطناعي\n"
                "2️⃣ كتابة نص تسويقي لكل منصة\n"
                "3️⃣ النشر على فيسبوك + انستغرام + تيك توك\n\n"
                "ابدأ الآن! 🚀"
            )
        else:
            await send_message(chat_id, "📎 أرسل لي صورة أو فيديو للبدء.")

    return JSONResponse({"ok": True})


@app.get("/")
async def root():
    return {"status": "running", "service": "شفرة السكينة - نظام النشر التلقائي"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
