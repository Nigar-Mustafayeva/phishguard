"""Security-awareness training content + idempotent seeding.

seed_training() creates missing modules and refreshes existing ones (matched
by slug) so content edits reach databases that were seeded earlier. Quiz
attempts are never deleted. Safe to run repeatedly.

Article format (rendered by render_article):
    ## Heading            -> section heading
    • item                -> bullet list item
    > text                -> highlighted tip
    anything else         -> paragraph
"""
from markupsafe import Markup, escape

from app.extensions import db
from app.models import TrainingModule, QuizQuestion

TRAINING_MODULES = [
    {
        "slug": "phishing-basics",
        "title": "Recognising phishing red flags",
        "icon": "bi-eye",
        "level": "Beginner",
        "minutes": 4,
        "summary": "Spot the classic warning signs before you click anything.",
        "order_index": 1,
        "content": (
            "Phishing emails are designed to rush you into a decision before you "
            "have time to think. Attackers copy real brands, real colleagues and "
            "real processes — so the signs are often small.\n"
            "## The most common red flags\n"
            "• Urgent or threatening tone (\"your account will be closed today\").\n"
            "• An unfamiliar or slightly misspelled sender address.\n"
            "• Generic greetings such as \"Dear user\" or \"Dear customer\".\n"
            "• Links or attachments you did not expect.\n"
            "• Requests for passwords, codes, payments or gift cards.\n"
            "• Spelling mistakes, odd formatting or blurry logos.\n"
            "## Why it works\n"
            "Phishing exploits emotions: fear, curiosity, greed and the wish to be "
            "helpful. The stronger the emotion an email triggers, the more carefully "
            "you should check it.\n"
            "> Pause for five seconds. If an email makes you feel pressured, that "
            "pressure is the attack."
        ),
        "questions": [
            {
                "question": "An email urgently asks you to change your password. What should you do?",
                "a": "Click the link right away and change it",
                "b": "Verify the sender and report it if it looks suspicious",
                "c": "Forward it to your colleagues",
                "d": "Reply asking if it is real",
                "correct": "B",
                "explanation": "Urgency is a classic social-engineering trick. Check "
                               "the sender first and never act through the email's own link.",
            },
            {
                "question": "Which of these is NOT a phishing red flag?",
                "a": "Spelling and grammar mistakes",
                "b": "An urgent, threatening tone",
                "c": "An expected email from your company's official domain",
                "d": "A generic greeting like \"Dear user\"",
                "correct": "C",
                "explanation": "An expected email from the official domain is normal; "
                               "the others should all raise suspicion.",
            },
            {
                "question": "Which emotion do attackers try to trigger most often?",
                "a": "Boredom",
                "b": "Fear or urgency",
                "c": "Calm",
                "d": "Nostalgia",
                "correct": "B",
                "explanation": "Fear and urgency stop people from thinking critically, "
                               "which is exactly what an attacker wants.",
            },
            {
                "question": "\"You won a $500 gift card — claim within 1 hour!\" This is most likely:",
                "a": "A nice surprise from HR",
                "b": "A phishing lure using greed and urgency",
                "c": "A system notification",
                "d": "Safe if the logo looks right",
                "correct": "B",
                "explanation": "Unexpected prizes combined with a short deadline are a "
                               "textbook lure. Logos are trivial to copy.",
            },
        ],
    },
    {
        "slug": "sender-verification",
        "title": "Verifying the sender",
        "icon": "bi-person-check",
        "level": "Beginner",
        "minutes": 4,
        "summary": "Display names lie — learn to read the real address and domain.",
        "order_index": 2,
        "content": (
            "The sender's display name can say anything. What matters is the actual "
            "email address — and especially the domain after the @ sign.\n"
            "## How to check a sender\n"
            "• Look at the domain: microsoft.com is not micros0ft-support.xyz.\n"
            "• Watch for look-alike characters: rn vs m, 0 vs o, l vs I.\n"
            "• Check whether the Reply-To address differs from the sender.\n"
            "• Be wary of free email providers used for \"official\" business.\n"
            "• When in doubt, contact the company through an official channel you "
            "already know — not the one in the email.\n"
            "## Look-alike domains\n"
            "Attackers register domains such as paypa1.com or company-hr-portal.net "
            "that look legitimate at a glance. Read domains from right to left: the "
            "part just before .com/.net/.org is the real owner.\n"
            "> In login.company.com.verify-user.io the real domain is verify-user.io."
        ),
        "questions": [
            {
                "question": "Which sender address is suspicious?",
                "a": "it-support@company.com",
                "b": "it-support@company-security-update.xyz",
                "c": "hr@company.com",
                "d": "None of them",
                "correct": "B",
                "explanation": "An unusual domain (.xyz plus extra words) is a strong "
                               "sign of impersonation.",
            },
            {
                "question": "What is the most reliable way to confirm a sender is genuine?",
                "a": "Call the phone number in the email",
                "b": "Click the link in the email",
                "c": "Confirm through the company's official website or a known channel",
                "d": "Look at the sender's display name",
                "correct": "C",
                "explanation": "Trust an independent, official channel — never the "
                               "contact details supplied by the email itself.",
            },
            {
                "question": "What is the real domain in: https://account.bank.com.secure-login.net/reset ?",
                "a": "bank.com",
                "b": "account.bank.com",
                "c": "secure-login.net",
                "d": "reset",
                "correct": "C",
                "explanation": "Read right to left: the registered domain sits just "
                               "before the first single slash — secure-login.net.",
            },
            {
                "question": "The display name says \"CEO Sarah Lee\" but the address is sarah.lee.ceo@gmail.com. What does this suggest?",
                "a": "The CEO is working from home",
                "b": "Possible impersonation — verify through another channel",
                "c": "It is safe because the name matches",
                "d": "Gmail is always used by executives",
                "correct": "B",
                "explanation": "Executives use corporate addresses. A personal webmail "
                               "account using a leader's name is a common fraud pattern.",
            },
        ],
    },
    {
        "slug": "links-and-passwords",
        "title": "Suspicious links, passwords & MFA",
        "icon": "bi-key",
        "level": "Beginner",
        "minutes": 5,
        "summary": "Hover before you click, and keep credentials out of attackers' hands.",
        "order_index": 3,
        "content": (
            "Links and passwords are an attacker's main targets. One click on a fake "
            "login page can hand over your account.\n"
            "## Links\n"
            "• Hover over a link (or long-press on mobile) to see the real address.\n"
            "• Shortened links (bit.ly, tinyurl) hide the destination.\n"
            "• Type well-known addresses yourself instead of clicking.\n"
            "## Passwords\n"
            "• Never share passwords by email, chat or form — IT will never ask.\n"
            "• Use long, unique passwords and a password manager.\n"
            "• A password manager won't autofill on a fake site — a useful alarm.\n"
            "## Multi-factor authentication (MFA)\n"
            "MFA protects your account even if your password is stolen. But never "
            "approve an MFA prompt you did not start, and never read a code to anyone.\n"
            "> Got a surprise MFA prompt? Deny it and change your password — someone "
            "already knows it."
        ),
        "questions": [
            {
                "question": "Why is MFA (multi-factor authentication) important?",
                "a": "It replaces your password entirely",
                "b": "It adds a layer of protection even if your password is stolen",
                "c": "It makes email faster",
                "d": "It makes links safe",
                "correct": "B",
                "explanation": "MFA requires a second proof, so a stolen password "
                               "alone is not enough.",
            },
            {
                "question": "What should be your first step when you see a suspicious link?",
                "a": "Click it to check",
                "b": "Hover over it to see the real address",
                "c": "Enter your password to test it",
                "d": "Download the attachment",
                "correct": "B",
                "explanation": "Hovering shows where the link really goes without "
                               "visiting it.",
            },
            {
                "question": "You receive an MFA approval request you did not start. What do you do?",
                "a": "Approve it so it stops",
                "b": "Deny it, change your password and inform IT",
                "c": "Ignore it forever",
                "d": "Approve it, then log out",
                "correct": "B",
                "explanation": "An unexpected prompt means someone has your password. "
                               "Deny, change the password and report it.",
            },
            {
                "question": "Your password manager does not autofill on a login page. Why might that matter?",
                "a": "The manager is broken",
                "b": "The page may be on a fake domain",
                "c": "You should type the password manually right away",
                "d": "It never matters",
                "correct": "B",
                "explanation": "Password managers match the exact domain. No autofill "
                               "is a signal to double-check the address bar.",
            },
        ],
    },
    {
        "slug": "attachments",
        "title": "Dangerous attachments",
        "icon": "bi-paperclip",
        "level": "Intermediate",
        "minutes": 4,
        "summary": "Which files can hurt you, and how attackers disguise them.",
        "order_index": 4,
        "content": (
            "Attachments are one of the oldest ways to deliver malware — and they "
            "still work because files look harmless.\n"
            "## High-risk file types\n"
            "• Executables and scripts: .exe, .scr, .js, .vbs, .bat, .ps1.\n"
            "• Office files that ask you to \"Enable content\" or \"Enable macros\".\n"
            "• Compressed archives (.zip, .rar, .iso) that hide other files.\n"
            "• HTML attachments that open a fake login page locally.\n"
            "## Disguise tricks\n"
            "• Double extensions: invoice.pdf.exe.\n"
            "• Password-protected zips (the password is in the email) to evade scanners.\n"
            "• \"Secure document\" links to a shared file that asks you to sign in.\n"
            "> Never enable macros on a document you received by email unless IT "
            "has confirmed it is safe."
        ),
        "questions": [
            {
                "question": "Which file name is the most dangerous?",
                "a": "report.pdf",
                "b": "invoice.pdf.exe",
                "c": "photo.jpg",
                "d": "notes.txt",
                "correct": "B",
                "explanation": "A double extension hides an executable behind a "
                               "harmless-looking name.",
            },
            {
                "question": "A Word file says \"Enable content to view this document\". You should:",
                "a": "Enable it — it's just Word",
                "b": "Close it and report it to IT",
                "c": "Forward it to a colleague to try",
                "d": "Save it to your desktop",
                "correct": "B",
                "explanation": "Enabling macros lets the document run code. Legitimate "
                               "documents rarely need it.",
            },
            {
                "question": "Why do attackers send password-protected zip files?",
                "a": "To protect your privacy",
                "b": "Because email scanners cannot look inside them",
                "c": "Because zips are smaller",
                "d": "It is a legal requirement",
                "correct": "B",
                "explanation": "Encryption stops security tools from inspecting the "
                               "contents, so malware slips through.",
            },
            {
                "question": "An unexpected .html attachment opens a Microsoft login page. This is:",
                "a": "A normal way to sign in",
                "b": "A credential-harvesting trick",
                "c": "A browser update",
                "d": "Safe because it opened offline",
                "correct": "B",
                "explanation": "HTML attachments can render convincing fake login "
                               "forms that send your password to the attacker.",
            },
        ],
    },
    {
        "slug": "social-engineering",
        "title": "Social engineering: calls, texts & chats",
        "icon": "bi-telephone",
        "level": "Intermediate",
        "minutes": 5,
        "summary": "Phishing doesn't only arrive by email — vishing, smishing and pretexting.",
        "order_index": 5,
        "content": (
            "Social engineering targets people, not systems. Attackers build a "
            "believable story (a pretext) and use any channel that reaches you.\n"
            "## Channels\n"
            "• Vishing — voice calls pretending to be IT, a bank or a manager.\n"
            "• Smishing — SMS messages with links (\"your parcel is held\").\n"
            "• Chat & social media — fake recruiters, fake colleagues on Teams/Slack.\n"
            "## Common pretexts\n"
            "• \"I'm from IT, I need your code to fix your account.\"\n"
            "• \"I'm new and my manager is in a meeting — can you help me quickly?\"\n"
            "• \"This is the bank fraud team, please confirm your card number.\"\n"
            "## Defend yourself\n"
            "• Slow down and ask questions — real staff won't mind.\n"
            "• Hang up and call back on a number you already know.\n"
            "• Never share one-time codes, even with \"support\".\n"
            "> Caller ID and sender names can be spoofed. Verify the person, not the screen."
        ),
        "questions": [
            {
                "question": "Someone calls claiming to be IT and asks for the code sent to your phone. You:",
                "a": "Read the code to them",
                "b": "Refuse, hang up and report the call",
                "c": "Send the code by email instead",
                "d": "Give half of the code",
                "correct": "B",
                "explanation": "One-time codes are for you only. IT never needs them.",
            },
            {
                "question": "What is \"smishing\"?",
                "a": "Phishing via SMS text messages",
                "b": "A type of firewall",
                "c": "Phishing using smiley emojis",
                "d": "Secure mail",
                "correct": "A",
                "explanation": "Smishing = SMS + phishing, often with parcel or "
                               "bank themes.",
            },
            {
                "question": "Caller ID shows your bank's real number. Can you trust it?",
                "a": "Yes, numbers can't be faked",
                "b": "No — caller ID can be spoofed; call back on the official number",
                "c": "Only on weekdays",
                "d": "Yes, if the caller knows your name",
                "correct": "B",
                "explanation": "Spoofing caller ID is easy. Hang up and call the "
                               "number printed on your card or the official site.",
            },
            {
                "question": "A friendly \"new colleague\" on chat asks you to share a confidential file urgently. Best response?",
                "a": "Share it — they're on the team",
                "b": "Verify their identity through your manager or the directory first",
                "c": "Send it to their personal email",
                "d": "Ignore all colleagues forever",
                "correct": "B",
                "explanation": "Pretexting relies on helpfulness. Verifying first is "
                               "normal, polite and safe.",
            },
        ],
    },
    {
        "slug": "bec-invoice-fraud",
        "title": "CEO fraud & invoice scams",
        "icon": "bi-cash-coin",
        "level": "Advanced",
        "minutes": 5,
        "summary": "Business email compromise costs companies billions — learn the patterns.",
        "order_index": 6,
        "content": (
            "Business Email Compromise (BEC) attacks don't need malware. They "
            "convince an employee to send money or data by impersonating someone "
            "trusted.\n"
            "## Typical scenarios\n"
            "• \"CEO\" asks for an urgent, confidential wire transfer.\n"
            "• A supplier says their bank details have changed.\n"
            "• \"HR\" requests employee tax or payroll data.\n"
            "• An executive asks you to buy gift cards for a client.\n"
            "## Warning signs\n"
            "• Secrecy: \"don't tell anyone, I'm in a meeting\".\n"
            "• Pressure to bypass the normal approval process.\n"
            "• New payment details sent only by email.\n"
            "## The rule\n"
            "Any change to payment details, or any unusual payment request, must be "
            "confirmed by phone using a number from your own records.\n"
            "> A five-minute phone call is cheaper than an unrecoverable transfer."
        ),
        "questions": [
            {
                "question": "A supplier emails new bank details for their next invoice. You should:",
                "a": "Update them immediately",
                "b": "Call the supplier on a known number to confirm",
                "c": "Reply to the email asking if it's true",
                "d": "Pay both accounts to be safe",
                "correct": "B",
                "explanation": "Payment-detail changes must be verified out of band. "
                               "Replying reaches the attacker.",
            },
            {
                "question": "The \"CEO\" emails: \"Buy 10 gift cards for a client, keep it confidential.\" This is:",
                "a": "A normal executive request",
                "b": "A classic BEC scam",
                "c": "A team-building exercise",
                "d": "Fine if under $1,000",
                "correct": "B",
                "explanation": "Gift cards plus secrecy is one of the most common BEC "
                               "patterns. Verify by phone.",
            },
            {
                "question": "Which is the biggest warning sign in a payment request?",
                "a": "It has an invoice number",
                "b": "Pressure to skip the normal approval process",
                "c": "It is addressed to finance",
                "d": "It includes a PDF",
                "correct": "B",
                "explanation": "Attackers push you to bypass the controls designed to "
                               "stop them.",
            },
            {
                "question": "Why does BEC often succeed without any malware?",
                "a": "Because antivirus is off",
                "b": "Because it exploits trust and authority, not technology",
                "c": "Because email is encrypted",
                "d": "It never succeeds",
                "correct": "B",
                "explanation": "BEC is pure social engineering — process and "
                               "verification are the real defences.",
            },
        ],
    },
    {
        "slug": "qr-and-mobile",
        "title": "QR codes & mobile phishing",
        "icon": "bi-qr-code",
        "level": "Intermediate",
        "minutes": 3,
        "summary": "Quishing and mobile tricks that bypass desktop protections.",
        "order_index": 7,
        "content": (
            "QR codes hide their destination, and phones show less of a URL — "
            "which makes mobile devices an attractive target.\n"
            "## Quishing (QR phishing)\n"
            "• Emails with a QR code to \"re-validate MFA\" or \"view a document\".\n"
            "• Stickers placed over real QR codes on parking meters or posters.\n"
            "• Scanning moves the attack to your phone, outside company filters.\n"
            "## Mobile habits\n"
            "• Preview the URL your camera shows before opening it.\n"
            "• Install apps only from official stores.\n"
            "• Keep your phone's OS and apps updated.\n"
            "> If an email asks you to scan a QR code to log in, treat it like any "
            "other suspicious link."
        ),
        "questions": [
            {
                "question": "An email asks you to scan a QR code to keep your MFA active. You:",
                "a": "Scan it quickly",
                "b": "Treat it as suspicious and report it",
                "c": "Scan it with a colleague's phone",
                "d": "Print it out",
                "correct": "B",
                "explanation": "QR codes in emails are a growing phishing technique "
                               "designed to bypass email link scanning.",
            },
            {
                "question": "Why are QR-code attacks effective?",
                "a": "QR codes are encrypted",
                "b": "The destination is hidden and the phone may lack company protections",
                "c": "QR codes cannot contain links",
                "d": "They only work on desktops",
                "correct": "B",
                "explanation": "You can't read a QR code, and personal phones often "
                               "sit outside corporate security controls.",
            },
            {
                "question": "Before opening a link from a scanned QR code you should:",
                "a": "Check the URL preview shown by the camera",
                "b": "Open it immediately",
                "c": "Turn off Wi-Fi",
                "d": "Nothing — QR codes are safe",
                "correct": "A",
                "explanation": "Most cameras preview the URL — check the domain "
                               "before you tap.",
            },
            {
                "question": "Where should you install mobile apps from?",
                "a": "Links in SMS messages",
                "b": "Official app stores",
                "c": "Any website",
                "d": "Email attachments",
                "correct": "B",
                "explanation": "Official stores review apps; side-loaded apps are a "
                               "common malware source.",
            },
        ],
    },
    {
        "slug": "reporting-incidents",
        "title": "Reporting & what to do if you clicked",
        "icon": "bi-flag",
        "level": "Beginner",
        "minutes": 3,
        "summary": "Fast reporting turns a mistake into a small incident instead of a breach.",
        "order_index": 8,
        "content": (
            "Everyone clicks eventually. What matters is how quickly you report it. "
            "Security teams would much rather hear about a false alarm than miss a "
            "real attack.\n"
            "## If you see a suspicious email\n"
            "• Use the \"Report phishing\" button or forward it to security.\n"
            "• Don't forward it to colleagues to \"ask what they think\".\n"
            "• Delete it after reporting.\n"
            "## If you already clicked or entered data\n"
            "• Disconnect from the network if a file was opened.\n"
            "• Change the affected password immediately (from a trusted device).\n"
            "• Tell IT/security right away — include what you clicked and when.\n"
            "• Watch for unusual MFA prompts or account activity.\n"
            "> Reporting is never a punishment. Speed limits the damage."
        ),
        "questions": [
            {
                "question": "You realise you entered your password on a fake page. First action?",
                "a": "Wait and see what happens",
                "b": "Change the password and report it to IT immediately",
                "c": "Delete the email and forget it",
                "d": "Tell only your friend",
                "correct": "B",
                "explanation": "Changing the password and reporting quickly limits "
                               "what the attacker can do.",
            },
            {
                "question": "What is the best way to handle a suspicious email?",
                "a": "Forward it to all colleagues as a warning",
                "b": "Use the Report button / send it to security",
                "c": "Reply to the sender",
                "d": "Click the unsubscribe link",
                "correct": "B",
                "explanation": "Reporting lets the security team block it for "
                               "everyone. Forwarding spreads the risk.",
            },
            {
                "question": "Why should you report even if you're unsure?",
                "a": "Security teams prefer false alarms over missed attacks",
                "b": "To get a reward",
                "c": "Because it's required for every email",
                "d": "You shouldn't — only report confirmed attacks",
                "correct": "A",
                "explanation": "Early reports help detect campaigns that target "
                               "many people at once.",
            },
            {
                "question": "You opened an unexpected attachment and your PC acts strangely. You should:",
                "a": "Keep working",
                "b": "Disconnect from the network and contact IT",
                "c": "Restart and hope it's fixed",
                "d": "Open it again to check",
                "correct": "B",
                "explanation": "Disconnecting can stop malware spreading while IT "
                               "investigates.",
            },
        ],
    },
]

_BY_SLUG = {m["slug"]: m for m in TRAINING_MODULES}


def module_meta(slug: str) -> dict:
    """Display metadata (icon, level, minutes, summary) for a module slug."""
    m = _BY_SLUG.get(slug, {})
    return {"icon": m.get("icon", "bi-mortarboard"), "level": m.get("level", "Beginner"),
            "minutes": m.get("minutes", 3), "summary": m.get("summary", "")}


def render_article(text: str) -> Markup:
    """Turn the simple article format (see module docstring) into safe HTML."""
    out, in_list = [], False
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("• "):
            if not in_list:
                out.append("<ul class='article-list'>")
                in_list = True
            out.append(f"<li>{escape(line[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if line.startswith("## "):
            out.append(f"<h3>{escape(line[3:])}</h3>")
        elif line.startswith("> "):
            out.append(f"<div class='article-tip'><i class='bi bi-lightbulb'></i>"
                       f"<span>{escape(line[2:])}</span></div>")
        else:
            out.append(f"<p>{escape(line)}</p>")
    if in_list:
        out.append("</ul>")
    return Markup("".join(out))


def _question_rows(data):
    return [(q["question"], q["a"], q["b"], q["c"], q["d"], q["correct"],
             q["explanation"]) for q in data["questions"]]


def seed_training() -> int:
    """Create missing modules and refresh existing ones. Returns number created."""
    created = 0
    for data in TRAINING_MODULES:
        module = TrainingModule.query.filter_by(slug=data["slug"]).first()
        if module is None:
            module = TrainingModule(slug=data["slug"])
            db.session.add(module)
            created += 1
        module.title = data["title"]
        module.order_index = data["order_index"]
        module.content = data["content"]
        db.session.flush()

        current = [(q.question, q.option_a, q.option_b, q.option_c, q.option_d,
                    q.correct_option, q.explanation) for q in module.questions]
        if current != _question_rows(data):
            # Attempts reference the module, not questions, so replacing is safe.
            for q in list(module.questions):
                db.session.delete(q)
            db.session.flush()
            for q in data["questions"]:
                db.session.add(QuizQuestion(
                    module_id=module.id, question=q["question"],
                    option_a=q["a"], option_b=q["b"], option_c=q["c"], option_d=q["d"],
                    correct_option=q["correct"], explanation=q["explanation"]))
    db.session.commit()
    db.session.expire_all()
    return created
