"""Tolerant CSV parsing for participant lists.

Accepts files saved by Excel in any locale: UTF-8 or Windows encodings,
comma / semicolon / tab separators, and common header spellings such as
"First Name", "E-mail" or a single "Name" column.
"""
import csv
import io

from email_validator import validate_email, EmailNotValidError

from app.extensions import db
from app.models import Participant, Department

CSV_COLUMNS = ["first_name", "last_name", "email", "department"]

_ALIASES = {
    "first_name": {"first_name", "firstname", "first", "given_name", "ad"},
    "last_name": {"last_name", "lastname", "last", "surname", "family_name", "soyad"},
    "email": {"email", "e_mail", "email_address", "mail"},
    "department": {"department", "dept", "position", "team", "group", "sobe", "şöbə"},
    "name": {"name", "full_name", "fullname", "ad_soyad"},
}


class CSVError(ValueError):
    pass


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp1254", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise CSVError("The file could not be read. Save it as CSV UTF-8.")


def _key(header: str):
    h = (header or "").strip().lower().replace("-", "_").replace(" ", "_")
    for field, names in _ALIASES.items():
        if h in names:
            return field
    return None


def parse_csv(raw: bytes):
    """Return (rows, error_rows). rows: dicts with first_name, last_name,
    email (lower-case), department. error_rows: (line_no, reason)."""
    text = _decode(raw)
    if not text.strip():
        raise CSVError("The file is empty.")
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, [])
    keys = [_key(h) for h in header]
    if "email" not in keys:
        raise CSVError("No email column found. Expected columns: "
                       + ", ".join(CSV_COLUMNS) + ".")

    rows, errors, seen = [], [], set()
    for line_no, values in enumerate(reader, start=2):  # row 1 = header
        if not any(v.strip() for v in values):
            continue
        rec = {}
        for k, v in zip(keys, values):
            if k and k not in rec:
                rec[k] = v.strip()
        fn, ln = rec.get("first_name", ""), rec.get("last_name", "")
        if not (fn or ln) and rec.get("name"):
            fn, _, ln = rec["name"].partition(" ")
        em = rec.get("email", "").lower()
        if not (fn and em):
            errors.append((line_no, "empty field (name/email)"))
            continue
        try:
            validate_email(em, check_deliverability=False)
        except EmailNotValidError:
            errors.append((line_no, "invalid email format"))
            continue
        if em in seen:
            continue
        seen.add(em)
        rows.append({"first_name": fn, "last_name": ln.strip() or "-",
                     "email": em, "department": rec.get("department", "")})
    return rows, errors


def _department(name: str):
    name = (name or "").strip()
    if not name:
        return None
    dept = Department.query.filter_by(name=name).first()
    if dept is None:
        dept = Department(name=name)
        db.session.add(dept)
        db.session.flush()
    return dept


def save_rows(rows):
    """Create participants that don't exist yet. Returns (participants, added)
    where participants covers every row, new or already existing."""
    people, added = [], 0
    for r in rows:
        p = Participant.query.filter_by(email=r["email"]).first()
        if p is None:
            p = Participant(first_name=r["first_name"], last_name=r["last_name"],
                            email=r["email"], department=_department(r["department"]),
                            is_demo=False)
            db.session.add(p)
            db.session.flush()
            added += 1
        people.append(p)
    return people, added
