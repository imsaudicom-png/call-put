# بوصلة السوق — منصة تحليل مبنية على منطق مؤشر "بوصلة المثلث الذهبية"

مشروع كامل (Frontend + Backend) يترجم منطق مؤشر Pine Script إلى API وموقع تفاعلي.
راجع ملف `التوثيق_الفني_الكامل.md` لشرح كل قاعدة رياضية مستخدمة.

## البنية

```
backend/    → FastAPI + pandas (محرك التحليل الفعلي)
frontend/   → Next.js + TypeScript + Lightweight Charts
```

---

## الخطوات الكاملة من الصفر إلى رابط يعمل

### 1) الحصول على مفتاح بيانات مجاني

سجّل حسابًا مجانيًا في **[twelvedata.com](https://twelvedata.com/)** واحصل على مفتاح API
(الخطة المجانية تكفي للتجربة والاستخدام الخفيف — تحقق من الحدود الحالية على موقعهم وقت التسجيل).

### 2) رفع الكود إلى GitHub

من داخل مجلد المشروع (بعد فك الضغط أو تحميله):

```bash
git init
git add .
git commit -m "النسخة الأولى - بوصلة السوق"
git branch -M main
git remote add origin https://github.com/USERNAME/market-compass.git
git push -u origin main
```

> استبدل `USERNAME` باسم حسابك على GitHub، وأنشئ المستودع (Repository) فارغًا أولًا من واجهة GitHub قبل تنفيذ `git push`.

⚠️ **مهم:** لا ترفع أبدًا ملفي `.env` أو `.env.local` الحقيقيين (فيهما مفاتيحك السرية) — ملف `.gitignore` المرفق يمنع ذلك تلقائيًا.

### 3) نشر الـ Backend (على Render — مجاني للبداية)

1. اذهب إلى [render.com](https://render.com) → New → Web Service.
2. اربط مستودع GitHub الذي رفعته للتو.
3. Root Directory: `backend`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. أضف متغيرات البيئة (Environment):
   - `TWELVE_DATA_API_KEY` = مفتاحك من الخطوة 1
   - `CORS_ORIGINS` = سنضيفه في الخطوة التالية بعد معرفة رابط الواجهة الأمامية
7. اضغط Deploy — بعد الانتهاء ستحصل على رابط مثل: `https://market-compass-api.onrender.com`

### 4) نشر الـ Frontend (على Vercel — مجاني)

1. اذهب إلى [vercel.com](https://vercel.com) → Add New Project.
2. اربط نفس مستودع GitHub، واختر مجلد `frontend` كـ Root Directory.
3. أضف متغير البيئة:
   - `NEXT_PUBLIC_API_BASE_URL` = رابط الـ Backend من الخطوة السابقة
4. اضغط Deploy — ستحصل على رابط موقعك النهائي مثل: `https://market-compass.vercel.app`

### 5) اربط الاتجاهين

ارجع إلى إعدادات Render (Backend) وحدّث `CORS_ORIGINS` ليصبح رابط الـ Vercel الذي حصلت عليه، ثم أعد النشر (Redeploy).

---

## التشغيل محليًا (للتجربة قبل النشر)

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ثم ضع مفتاحك داخل .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.local.example .env.local   # القيمة الافتراضية تكفي محليًا
npm run dev
```
افتح `http://localhost:3000`

---

## ملاحظات مهمة

- الأصول المدعومة تعتمد على تغطية Twelve Data (أسهم عالمية، فوركس، عملات رقمية). لعملة رقمية اكتب مثلًا `BTC/USD`، ولفوركس `EUR/USD`.
- لا تتوقع تطابقًا حرفيًا 100% مع TradingView في كل رقم — الفروق الطبيعية تأتي من اختلاف مصدر السعر اللحظي بين المزوّدين، لكن منطق الحساب (Pivot/RSI/ATR/EMA) مطابق حرفيًا.
- راجع قسم "التحسينات" في التوثيق الفني لأفكار تطوير لاحقة (سجل أداء الإشارات، تنبيهات، إلخ).
