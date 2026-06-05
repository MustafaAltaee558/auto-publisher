# دليل الإعداد الكامل — نظام نشر شفرة السكينة

---

## الخطوة 1 — إنشاء بوت تيليغرام

1. افتح تيليغرام وابحث عن **@BotFather**
2. أرسل `/newbot`
3. أدخل اسم البوت (مثال: `شفرة السكينة`)
4. أدخل username (مثال: `shakrat_alsakina_bot`)
5. احفظ الـ **TOKEN** الذي يعطيك إياه

---

## الخطوة 2 — الحصول على Gemini API Key

1. اذهب إلى: https://aistudio.google.com/app/apikey
2. اضغط **Create API Key**
3. احفظ المفتاح

---

## الخطوة 3 — إعداد Make (Integromat)

### إنشاء السيناريو:

1. اذهب إلى [make.com](https://make.com) وأنشئ حساباً
2. اضغط **Create a new scenario**
3. أضف الموديولات بهذا الترتيب:

```
[Webhooks] Custom webhook
    ↓
[Router] — ينقسم لـ 3 مسارات
    ├→ [Facebook Pages] Create a Post
    ├→ [Instagram] Create a Photo/Video Post  
    └→ [TikTok] Upload Video
```

### تفاصيل إعداد الـ Webhook:

1. اضغط على موديول **Webhooks > Custom webhook**
2. اضغط **Add** ثم أعطه اسماً
3. انسخ رابط الـ Webhook (يبدأ بـ `https://hook.eu2.make.com/...`)
4. هذا هو `MAKE_WEBHOOK_URL`

### البيانات التي يستقبلها Make من السيرفر:

```json
{
  "chat_id": 123456789,
  "media_url": "https://api.telegram.org/file/bot.../photo.jpg",
  "media_type": "photo",
  "facebook_text": "نص فيسبوك هنا...",
  "instagram_text": "نص انستغرام هنا...",
  "tiktok_text": "نص تيك توك هنا..."
}
```

### ربط المتغيرات في Make:

في كل موديول نشر، اربط:
- **النص** ← `{{facebook_text}}` أو `{{instagram_text}}` أو `{{tiktok_text}}`
- **الصورة/الفيديو** ← `{{media_url}}`

---

## الخطوة 4 — رفع السيرفر على Render (مجاني)

1. ارفع الملفات على GitHub (مستودع جديد)
2. اذهب إلى [render.com](https://render.com) وسجّل دخول
3. اضغط **New > Web Service**
4. اربط مستودع GitHub
5. أضف متغيرات البيئة:
   - `TELEGRAM_TOKEN` ← من الخطوة 1
   - `GEMINI_API_KEY` ← من الخطوة 2
   - `MAKE_WEBHOOK_URL` ← من الخطوة 3
6. اضغط **Deploy**
7. انتظر حتى يظهر رابط السيرفر (مثال: `https://shakrat-alsakina.onrender.com`)

---

## الخطوة 5 — ربط تيليغرام بالسيرفر

بعد اكتمال الـ Deploy، شغّل:

```bash
python set_webhook.py
```

أدخل رابط السيرفر عندما يطلب منك، مثال:
```
https://shakrat-alsakina.onrender.com
```

يجب أن يظهر:
```
✅ تم ربط الـ Webhook بنجاح
```

---

## الخطوة 6 — الاختبار

1. افتح البوت في تيليغرام
2. أرسل `/start`
3. أرسل أي صورة
4. انتظر الرسائل:
   - `📸 استلمت الصورة!`
   - `⏳ جاري تحليل المحتوى...`
   - `✍️ تمت كتابة النصوص...`
   - `تم النشر ✅`

---

## بنية البيانات في Make

| المتغير | الوصف |
|---------|-------|
| `media_url` | رابط الصورة أو الفيديو |
| `media_type` | `photo` أو `video` |
| `facebook_text` | النص المخصص لفيسبوك |
| `instagram_text` | النص المخصص لانستغرام |
| `tiktok_text` | النص المخصص لتيك توك |
| `chat_id` | معرّف المحادثة في تيليغرام |

---

## الملفات

```
.
├── main.py              ← السيرفر الرئيسي (FastAPI)
├── set_webhook.py       ← ربط تيليغرام بالسيرفر
├── requirements.txt     ← المكتبات
├── .env.example         ← نموذج متغيرات البيئة
├── render.yaml          ← إعدادات Render
└── Procfile             ← أمر التشغيل
```
