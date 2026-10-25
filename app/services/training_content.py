"""Security-awareness training content + idempotent seeding.

seed_training() adds any modules whose slug is missing, WITHOUT deleting
existing data. Safe to run repeatedly.
"""
from app.extensions import db
from app.models import TrainingModule, QuizQuestion

TRAINING_MODULES = [
    {
        "slug": "phishing-basics",
        "title": "Phishing əlamətlərini tanımaq",
        "order_index": 1,
        "content": (
            "Phishing emailləri sizi tələsik qərar verməyə məcbur etmək üçün "
            "hazırlanır. Ən çox rast gəlinən əlamətlər:\n"
            "• Təcili və ya qorxuducu ton (\"hesabınız bağlanacaq\").\n"
            "• Tanış olmayan və ya saxta göndərən ünvanı.\n"
            "• Ümumi salamlaşma (\"Hörmətli istifadəçi\").\n"
            "• Şübhəli linklər və gözlənilməz qoşmalar.\n"
            "• Qrammatik səhvlər və qeyri-peşəkar dizayn."
        ),
        "questions": [
            {
                "question": "Email təcili şəkildə şifrənizi dəyişməyi tələb edirsə, nə etməlisiniz?",
                "a": "Dərhal linkə klikləyib şifrəni dəyişmək",
                "b": "Göndərəni yoxlamaq və şübhəlidirsə report etmək",
                "c": "Emaili həmkarlara yönləndirmək",
                "d": "Heç nə etməmək",
                "correct": "B",
                "explanation": "Təcili ton klassik social engineering üsuludur. "
                               "Əvvəlcə göndərəni yoxlayın, link vasitəsilə deyil.",
            },
            {
                "question": "Aşağıdakılardan hansı phishing əlaməti DEYİL?",
                "a": "Qrammatik səhvlər",
                "b": "Təcili ton",
                "c": "Şirkətin rəsmi domenindən gələn gözlənilən email",
                "d": "Ümumi salamlaşma",
                "correct": "C",
                "explanation": "Rəsmi domendən gələn gözlənilən email adi haldır; "
                               "qalanları isə şübhə doğurmalıdır.",
            },
        ],
    },
    {
        "slug": "sender-verification",
        "title": "Göndərən ünvanını yoxlamaq",
        "order_index": 2,
        "content": (
            "Göndərənin adı aldadıcı ola bilər — əsas olan email ünvanının "
            "domenidir.\n"
            "• Domenə diqqət edin: microsoft.com ≠ micros0ft-support.xyz.\n"
            "• \"Reply-to\" ünvanının göndərəndən fərqli olmasına fikir verin.\n"
            "• Şübhə olanda şirkətlə rəsmi kanalla (telefon/sayt) əlaqə saxlayın."
        ),
        "questions": [
            {
                "question": "Hansı göndərən ünvanı şübhəlidir?",
                "a": "it-support@sirket.com",
                "b": "it-support@sirket-security-update.xyz",
                "c": "hr@sirket.com",
                "d": "Heç biri",
                "correct": "B",
                "explanation": "Qeyri-adi domen (.xyz və əlavə sözlər) saxtakarlıq əlamətidir.",
            },
            {
                "question": "Göndərənin həqiqiliyini yoxlamağın ən etibarlı yolu?",
                "a": "Emaildəki telefon nömrəsinə zəng etmək",
                "b": "Emaildəki linkə klikləmək",
                "c": "Şirkətin rəsmi saytından/kanalından təsdiq almaq",
                "d": "Göndərənin adına baxmaq",
                "correct": "C",
                "explanation": "Emailin öz məlumatlarına deyil, müstəqil rəsmi "
                               "kanala güvənin.",
            },
        ],
    },
    {
        "slug": "links-and-passwords",
        "title": "Şübhəli linklər, parol və MFA",
        "order_index": 3,
        "content": (
            "Linklər və parollar hücumçuların əsas hədəfidir.\n"
            "• Linkin üzərinə gəlib (hover) real ünvanı yoxlayın, klik etməyin.\n"
            "• Parolları heç vaxt email və ya forma vasitəsilə paylaşmayın.\n"
            "• Güclü, unikal parollar və parol menecerindən istifadə edin.\n"
            "• Çoxfaktorlu autentifikasiya (MFA) hesabınızı parol oğurlansa belə qoruyur.\n"
            "• Şübhəli emaili \"Report\" düyməsi ilə bildirin."
        ),
        "questions": [
            {
                "question": "MFA (çoxfaktorlu autentifikasiya) nə üçün vacibdir?",
                "a": "Parolu tamamilə əvəz edir",
                "b": "Parol oğurlansa belə əlavə qoruma təbəqəsi verir",
                "c": "Emailləri sürətləndirir",
                "d": "Linkləri təhlükəsiz edir",
                "correct": "B",
                "explanation": "MFA ikinci təsdiq tələb edir, ona görə tək parol "
                               "oğurlanması kifayət etmir.",
            },
            {
                "question": "Şübhəli link gördükdə ilk addım nə olmalıdır?",
                "a": "Klikləyib yoxlamaq",
                "b": "Üzərinə gələrək (hover) real ünvanı yoxlamaq",
                "c": "Parolu daxil etmək",
                "d": "Qoşmanı yükləmək",
                "correct": "B",
                "explanation": "Hover etməklə kliklemədən linkin hara apardığını görə bilərsiniz.",
            },
        ],
    },
]


def seed_training() -> int:
    """Add missing modules by slug. Returns number of modules created."""
    created = 0
    for data in TRAINING_MODULES:
        if TrainingModule.query.filter_by(slug=data["slug"]).first():
            continue
        module = TrainingModule(slug=data["slug"], title=data["title"],
                                order_index=data["order_index"],
                                content=data["content"])
        db.session.add(module)
        db.session.flush()
        for q in data["questions"]:
            db.session.add(QuizQuestion(
                module_id=module.id, question=q["question"],
                option_a=q["a"], option_b=q["b"], option_c=q["c"], option_d=q["d"],
                correct_option=q["correct"], explanation=q["explanation"]))
        created += 1
    db.session.commit()
    return created
