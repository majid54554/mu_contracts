# MU Contracts — نظام عقود الموظفين الإلكترونية

تطبيق Frappe / ERPNext لإدارة عقود العمل الموسمية بالعربية مع توقيع إلكتروني من الموظف عبر رابط عام، وتوليد PDF بصيغة جاهزة للطباعة.

> صُمم وتم اختباره على **Frappe v17 / ERPNext v17** فقط. التوافق مع v15/v16 غير مضمون.

---

## المميزات

- ✍️ **بوابة توقيع عامة** على `/sign` — الموظف يدخل رقم الجوال + رقم الهوية ويوقّع بإصبعه/فأرته
- 🪪 **تحقق هوية بدون OTP** — مطابقة جوال + رقم هوية فقط (بدون SMS أو WhatsApp)
- 📄 **عقد جاهز بالعربية** (عقد عمل موسمي) — قابل للتخصيص من Print Format
- 📅 **تواريخ هجرية تلقائية** عبر `hijri-converter`
- 🖼️ **letterhead مع header/footer** يظهرون في الصفحة الأولى والأخيرة فقط
- 🖋️ **توقيعان في العقد**: توقيع المؤسس (ثابت من الإعدادات) + توقيع الموظف (مرسوم على الجهاز)
- 📥 **PDF مولّد بـ Chrome** (يحترم `@page` و RTL بشكل ممتاز)
- ⚙️ **إعدادات مركزية** (`Contract Settings`) لبيانات المؤسسة والمالك — تعدّل من Desk بدون لمس الكود

---

## المتطلبات

- Frappe Framework **v17** (لم يُختبر على إصدارات أقدم)
- Python **3.10+**
- `hijri-converter>=2.3.0` (يثبت تلقائياً مع التطبيق)
- **Chrome PDF Generator** مفعّل في Frappe (للحصول على PDFs عالية الجودة بالعربي)
  - يثبت من `bench setup chrome`

---

## التثبيت

```bash
# 1. ادخل لمجلد البنش
cd /path/to/frappe-bench

# 2. اجلب التطبيق
bench get-app https://github.com/<USERNAME>/mu_contracts

# 3. ثبّته على السايت
bench --site your-site.local install-app mu_contracts

# 4. (اختياري) أعد تشغيل البنش
bench restart
```

سيقوم `after_install` تلقائياً بـ:
- تثبيت Print Format "Contract Employee"
- ضبطه كافتراضي عبر Property Setter
- إنشاء Contract Settings مع قيم افتراضية
- إضافة Workspace "First Party" مع اختصارات

---

## بعد التثبيت

### 1) إعدادات العقود
افتح **Desk → First Party → الإعدادات → إعدادات العقود** (أو `/desk/contract-settings`):

- عدّل بيانات المؤسسة (الاسم، السجل التجاري، الرقم الموحد، المدينة، إلخ)
- عدّل بيانات الطرف الأول (الاسم، رقم الهوية، تاريخ الميلاد، الصفة)
- ارفع صورة توقيع المالك (PNG شفاف مفضل، 300×120 بكسل)

### 2) أضف موظف
**Desk → First Party → إضافة موظف جديد** — املأ:
- الاسم، رقم الجوال، رقم الهوية (مطلوبة)
- الجنسية، تاريخ الميلاد، العنوان الوطني
- المسمى الوظيفي، الراتب/المكافأة، تاريخ بدء العقد

### 3) أرسل رابط التوقيع للموظف
شارك الرابط: `https://your-site.com/sign`

الموظف:
1. يدخل رقم جواله ورقم هويته
2. يؤكد اسمه
3. يقرأ العقد ويوقع بإصبعه
4. يحمّل نسخة PDF

### 4) من Desk
صفحة الموظف فيها زرين:
- **معاينة العقد** — يفتح Print View في تبويب جديد
- **تحميل العقد PDF** — يحمّل PDF بصورة التوقيع inline

---

## البنية

```
mu_contracts/
├── mu_contracts/
│   ├── api.py                              # API endpoints + PDF generation
│   ├── install.py                          # after_install / after_migrate hooks
│   ├── hooks.py
│   ├── doctype/
│   │   ├── contract_employee/              # سجل الموظف + العقد
│   │   └── contract_settings/              # Single — إعدادات المؤسسة والمالك
│   ├── fixtures/                           # Print Format + Workspace + Property Setter
│   ├── public/images/                      # header.jpg, footer.jpg, logo.png
│   └── www/
│       └── sign.html                       # بوابة التوقيع العامة
└── pyproject.toml
```

---

## تخصيص نص العقد

نص العقد محفوظ كـ **Print Format** اسمه `Contract Employee`. لتعديله:

1. روح **Desk → Print Format List → Contract Employee**
2. عدّل الـ HTML/CSS فيه
3. متغيرات Jinja المتاحة:
   - `doc.*` — حقول الموظف (employee_name, national_id, phone_number, position, salary, start_date, ...)
   - `settings.*` — إعدادات الطرف الأول/المؤسسة (من Contract Settings)
   - `format_hijri(date)` — تحويل لتاريخ هجري
   - `format_gregorian(date)` — تحويل لتاريخ ميلادي
   - `add_hijri_days(date, days)` — جمع أيام على تاريخ وإرجاعه هجري

---

## API endpoints

| Endpoint | Method | Auth | الوصف |
|---|---|---|---|
| `/api/method/mu_contracts.api.lookup_employee` | POST | Guest | تحقق هوية بـ phone + national_id |
| `/api/method/mu_contracts.api.get_contract` | POST | Guest (token) | يرجع HTML العقد |
| `/api/method/mu_contracts.api.submit_signature` | POST | Guest (token) | يحفظ التوقيع |
| `/api/method/mu_contracts.api.get_signed_contract` | POST | Guest (token) | يرجع HTML العقد الموقّع |
| `/api/method/mu_contracts.api.download_signed_pdf` | GET | Guest (token) | يحمّل PDF (للموظف) |
| `/api/method/mu_contracts.api.download_contract_pdf` | GET | Logged in | يحمّل PDF (للموظفين الداخليين) |

> الـ token صلاحيته **30 دقيقة** (قابل للتعديل من `TOKEN_TTL` في `api.py`).

---

## ملاحظات تقنية

- **توقيع الـ Guest على /sign**: يستخدم `frappe.cache` (Redis) بـ token عشوائي بدل cookies
- **صور التوقيع inline**: Chrome PDF generator ما يقدر يجيب `/private/files/...` (مافي session)، فحوّلتها لـ base64 data URI قبل ما تروح للـ Chrome
- **Print Format Permission**: `validate_print_permission` ما يحترم `ignore_permissions`، فحلّيتها بـ `set_user("Administrator")` مؤقت
- **Footer/Header**: عناصر `display: block` عادية داخل `.ec` (مو `position: fixed`) — كذا تطلع في أول/آخر صفحة فقط

---

## الترخيص

MIT
