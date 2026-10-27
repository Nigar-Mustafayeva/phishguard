# PhishGuard — Phishing Simulation & Security Awareness Platform

İcazəli təşkilatların nəzarətli mühitdə phishing simulyasiyaları aparması,
istifadəçi reaksiyalarını izləməsi və təhlükəsizlik maarifləndirməsi üçün
veb platforma.

> ⚠️ **Etik qeyd:** Bu platforma yalnız **icazəli** test mühitində istifadə
> üçündür. Real parollar heç vaxt saxlanmır. Public demo həmişə `DEMO_MODE=true`
> rejimində işləyir və real email göndərmir.

## Texnologiyalar
- Backend: Python + Flask (application factory + blueprints)
- Frontend: Jinja2, Bootstrap 5, Chart.js
- DB: SQLite (lokal) / PostgreSQL (deploy)
- ORM: SQLAlchemy + Flask-Migrate
- Təhlükəsizlik: Flask-Login, Flask-WTF (CSRF)

## Quraşdırma (Windows PowerShell)

```powershell
# 1. Layihə qovluğuna keç
cd $HOME\Documents\PhishGuard

# 2. Virtual mühit yarat və aktivləşdir
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Paketləri qur
pip install -r requirements.txt

# 4. .env faylını hazırla
copy .env.example .env
# .env faylını açıb SECRET_KEY-i dəyiş

# 5. Verilənlər bazasını qur (migrasiyalar) və demo data əlavə et
flask db upgrade
python seed.py

# 6. İlk admin istifadəçisini yarat (şifrəni özün təyin edirsən)
flask create-admin

# 7. İşə sal
python run.py
```

İşə saldıqdan sonra **http://127.0.0.1:5000** ünvanı səni login səhifəsinə yönləndirəcək.
Yaratdığın admin email/şifrəsi ilə daxil ol.

Brauzerdə aç: http://127.0.0.1:5000

## Mərhələlər
| # | Mərhələ | Status |
|---|---------|--------|
| 1 | Skelet (app factory, dashboard, dizayn) | ✅ Hazır |
| 2 | DB modelləri + migrasiyalar + demo seed | ✅ Hazır |
| 3 | Auth + RBAC (login, rollar, CSRF) | ✅ Hazır |
| 4 | İştirakçılar CRUD + CSV import | ✅ Hazır |
| 5 | Email şablonları + preview + Mailtrap | ✅ Hazır |
| 6 | Kampaniyalar CRUD + lifecycle | ✅ Hazır |
| 7 | GoPhish servis qatı + demo mode + sync | ✅ Hazır |
| 8 | Nəticələr / event tracking + funnel | ✅ Hazır |
| 9 | Dashboard analitikası (real data) | ✅ Hazır |
| 10 | Təlim modulları + quizlər | ✅ Hazır |
| 11 | Hesabatlar (PDF + CSV) | ✅ Hazır — **MVP tamamlandı** |
| 12 | Audit log + settings (istifadəçi idarəsi) | ✅ Hazır |
| 13 | Avtomatik testlər (52 test) | ✅ Hazır |
| 14 | Render deployment (PostgreSQL, demo mode) | ✅ Hazır |
| + | Risk Intelligence modulu | ✅ Hazır |

### Risk Intelligence (fərqləndirici funksiya)
GoPhish-dən fərqli olaraq, PhishGuard nəticələri bütün kampaniyalar üzrə
birləşdirib hər iştirakçı üçün **risk profili** qurur:
- **Human Risk Intelligence** — 0–100 risk balı (klik, form, təkrar səhv, report).
- **Explainable Risk** — balın səbəbləri açıq göstərilir (qara qutu deyil).
- **Adaptive Training** — iştirakçının aldandığı mövzuya uyğun təlim tövsiyəsi.
- **Training Effectiveness** — kampaniyalar arası klik faizi trendi (əvvəl/sonra).

## Testlər

52 avtomatik test `tests/` qovluğunda modullara görə bölünüb (auth, participants,
templates, campaigns, results/reports, integration, training, settings, schema).

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
```

Gözlənilən nəticə: `52 passed`. Əhatə olunan sahələr: autentifikasiya, icazələr
(RBAC), kampaniya lifecycle, şablon validasiyası, hadisə qeydiyyatı, metrika
hesablamaları, hesabat yaradılması, yanlış girişlər, inteqrasiya xətaları və
verilənlər bazası sxemi.

## Deployment (Render + PostgreSQL)

Public deploy həmişə **demo mode**-da işləyir (`DEMO_MODE=true`): real email
göndərilmir, GoPhish qoşulmur. GoPhish ayrıca, lokal/qorunan mühitdə qalır
(aşağıya bax).

### Fayllar
- `render.yaml` — Blueprint (web servis + pulsuz PostgreSQL).
- `start.sh` — migrasiyaları işlədir (`flask db upgrade`), `flask init-app`
  çağırır (admin + demo data), sonra Gunicorn-u başladır.
- `Procfile` — `web: bash start.sh` (portativ).
- `/health` — health-check endpoint.

### Addımlar
1. **GitHub-a yüklə.** Layihəni GitHub reposuna push et (`.env` və `venv`
   `.gitignore`-dadır, yüklənmir).
2. **Render-də Blueprint yarat.** render.com → "New +" → "Blueprint" →
   GitHub reposunu seç. Render `render.yaml`-ı oxuyub web servisi və
   PostgreSQL bazasını avtomatik yaradır.
3. **Admin env dəyişənlərini təyin et.** Render dashboard → servis →
   "Environment" bölməsində:
   - `ADMIN_EMAIL` = giriş emailin
   - `ADMIN_PASSWORD` = güclü şifrə (ən az 8 simvol)

   (`SECRET_KEY` avtomatik yaradılır, `DATABASE_URL` bazadan avtomatik gəlir.)
4. **Deploy.** Render build edir, migrasiyalar işləyir, admin və demo data
   yaradılır. Bitəndə verilən URL-ə get, admin email/şifrə ilə daxil ol.

### Migrasiyalar
`start.sh` hər deploy-da `flask db upgrade` işlədir, ona görə əl ilə heç nə
lazım deyil. Yeni migrasiya əlavə edəndə sadəcə push et.

### Pulsuz tier məhdudiyyətləri və xərc
- Web servis **15 dəq fəaliyyətsizlikdən sonra yuxuya gedir**; növbəti sorğu
  ~30-60 san yavaş açılır (soyuq start).
- Pulsuz PostgreSQL **90 gün** sonra bitir; davamı aylıq ~$7.
- Pulsuz diskdə yüklənən fayllar saxlanmır — ona görə bütün davamlı data
  PostgreSQL-dədir (SQLite deploy-da istifadə olunmur).

### Troubleshooting
- **Build uğursuz:** Logs-a bax; adətən `requirements.txt` versiyası və ya
  `PYTHON_VERSION` uyğunsuzluğu. render.yaml-da `PYTHON_VERSION=3.12.7`.
- **"Application failed to respond":** Gunicorn `0.0.0.0:$PORT`-a bağlanmalıdır
  (`start.sh` bunu edir). Start command `bash start.sh` olmalıdır.
- **DB bağlantı xətası:** `DATABASE_URL` render.yaml-da bazadan gəlir; əl ilə
  dəyişmə. Kod `postgres://` → `postgresql://` çevirməsini avtomatik edir.
- **Login alınmır:** `ADMIN_EMAIL`/`ADMIN_PASSWORD` təyin olunubmu yoxla,
  sonra "Manual Deploy" ilə yenidən işə sal.

### GoPhish-i Flask-dan ayrı saxlamaq
Public deploy demo mode-dadır və GoPhish-ə qoşulmur. Real icazəli test üçün
GoPhish-i ayrıca, **qorunan** mühitdə (admin paneli public deyil — VPN/firewall
arxasında) işlədin və yalnız o mühitdə `.env`-də `DEMO_MODE=false`,
`GOPHISH_API_URL`, `GOPHISH_API_KEY` təyin et. Public portfolio deploy-u heç
vaxt canlı phishing motoruna bağlama.
