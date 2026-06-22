"""
Rule-based parser for LinkedIn PDF exports.
LinkedIn PDFs have a sidebar (Contact, Top Skills, Certifications) on the left
and main content (Name, Headline, Experience, Education) on the right.
PyMuPDF extracts them interleaved in plain text mode, but we use spatial
block extraction (coordinates + font size) to reliably separate sidebar
from main content and identify the name (always largest font on page 1).
"""
import re
import logging

try:
    import fitz
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

SECTION_HEADERS = {
    "summary", "about", "experience", "education",
    "top skills", "skills", "certifications", "licenses & certifications",
    "honors & awards", "honors-awards", "languages", "publications",
    "projects", "volunteer experience", "contact", "courses",
    "organizations", "recommendations",
}

MONTH_MAP = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03", "apr": "04", "april": "04",
    "may": "05", "jun": "06", "june": "06", "jul": "07", "july": "07",
    "aug": "08", "august": "08", "sep": "09", "sept": "09", "september": "09",
    "oct": "10", "october": "10", "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}

DATE_RANGE_RE = re.compile(
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{4}|\d{4})"
    r"\s*-\s*"
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{4}|\d{4}|Present|present)",
    re.IGNORECASE,
)

DURATION_RE = re.compile(r"\([\d]+ (?:year|month|day)", re.IGNORECASE)
LINKEDIN_URL_RE = re.compile(r"linkedin\.com/in/[\w-]+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"[\+]?\d[\d\s\-().]{6,14}\d")
PAGE_FOOTER_RE = re.compile(r"Page\s+\d+\s+of\s+\d+", re.IGNORECASE)


def _normalize_date(date_str: str) -> str | None:
    date_str = date_str.strip()
    if date_str.lower() in ("present", "current", "now"):
        return None
    m = re.match(r"(\w+)\s+(\d{4})", date_str, re.IGNORECASE)
    if m:
        month = MONTH_MAP.get(m.group(1).lower())
        if month:
            return f"{m.group(2)}-{month}"
    m = re.match(r"^(\d{4})$", date_str.strip())
    if m:
        return f"{m.group(1)}-01"
    return date_str


def _clean_text(raw_text: str) -> str:
    """Normalize unicode artifacts from PDF extraction."""
    text = raw_text.replace("\xa0", " ")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    # Remove zero-width and other invisible chars
    text = re.sub(r"[�]", "", text)
    # Remove page footers
    text = PAGE_FOOTER_RE.sub("", text)
    return text


def _find_sections(lines: list[str]) -> dict[str, list[str]]:
    """Split lines into named sections."""
    sections: dict[str, list[str]] = {}
    current = "_pre"
    sections[current] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            sections.setdefault(current, []).append("")
            continue

        key = stripped.lower()
        if key in SECTION_HEADERS:
            current = key
            if current == "about":
                current = "summary"
            if current == "licenses & certifications":
                current = "certifications"
            sections.setdefault(current, [])
            continue

        sections.setdefault(current, [])
        sections[current].append(stripped)

    return {k: v for k, v in sections.items() if v}


def _extract_identity_spatial(pdf_bytes: bytes) -> dict | None:
    """
    Use PyMuPDF spatial extraction to get name/headline/location from page 1.
    LinkedIn PDFs always have:
      - Sidebar at x ≈ 21 (Contact, Skills, Certifications)
      - Main content at x ≈ 223 (Name in large font, Headline, Location)
    The name is always the LARGEST font on the right side of page 1.
    """
    if fitz is None:
        return None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None

    if len(doc) == 0:
        doc.close()
        return None

    page = doc[0]
    page_width = page.rect.width
    mid_x = page_width * 0.33

    # Collect all text lines with position and font info from page 1
    main_lines = []  # (y, font_size, text)
    sidebar_lines = []

    try:
        blocks = page.get_text("dict")["blocks"]
    except Exception:
        doc.close()
        return None

    for b in blocks:
        if b.get("type", 0) != 0:
            continue
        for line in b.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            x0 = line["bbox"][0]
            y0 = line["bbox"][1]
            font_size = line["spans"][0]["size"] if line["spans"] else 0

            text = text.replace("\xa0", " ").replace("’", "'").replace("‘", "'")
            text = text.replace("“", '"').replace("”", '"')
            text = text.replace("–", "-").replace("—", "-")

            if x0 >= mid_x:
                main_lines.append((y0, font_size, text))
            else:
                sidebar_lines.append((y0, font_size, text))

    doc.close()

    if not main_lines:
        return None

    main_lines.sort(key=lambda t: t[0])

    # The name is the line with the largest font size (typically 26pt)
    max_font = max(ml[1] for ml in main_lines)
    identity = {"full_name": None, "headline": None, "location": None,
                "linkedin_url": None, "email": None, "phone": None}

    name_parts = []
    headline_parts = []
    location = None
    phase = "name"

    for y, sz, text in main_lines:
        low = text.lower()
        if low in SECTION_HEADERS:
            break

        if phase == "name":
            if sz >= max_font - 2:
                name_parts.append(text)
            else:
                phase = "headline"
                headline_parts.append(text)
        elif phase == "headline":
            headline_parts.append(text)

    if name_parts:
        identity["full_name"] = " ".join(name_parts)
    if len(headline_parts) >= 2:
        identity["headline"] = " ".join(headline_parts[:-1])
        identity["location"] = headline_parts[-1]
    elif len(headline_parts) == 1:
        identity["headline"] = headline_parts[0]

    # Extract contact info from sidebar
    sidebar_text = " ".join(t for _, _, t in sidebar_lines)
    joined_sidebar = sidebar_text.replace("- ", "").replace("-\n", "")
    url_match = LINKEDIN_URL_RE.search(joined_sidebar) or LINKEDIN_URL_RE.search(sidebar_text)
    if url_match:
        identity["linkedin_url"] = url_match.group(0)
    email_match = EMAIL_RE.search(sidebar_text)
    if email_match:
        identity["email"] = email_match.group(0)
    phone_match = PHONE_RE.search(sidebar_text)
    if phone_match:
        identity["phone"] = phone_match.group(0)

    return identity


def _extract_identity(sections: dict[str, list[str]], full_text: str) -> dict:
    """Fallback text-based identity extraction (used when pdf_bytes not available)."""
    identity = {
        "full_name": None, "headline": None, "location": None,
        "linkedin_url": None, "email": None, "phone": None,
    }

    joined = full_text.replace("-\n", "").replace("- \n", "")
    url_match = LINKEDIN_URL_RE.search(joined) or LINKEDIN_URL_RE.search(full_text)
    if url_match:
        identity["linkedin_url"] = url_match.group(0)

    contact_text = " ".join(sections.get("contact", []))
    email_match = EMAIL_RE.search(contact_text) or EMAIL_RE.search(full_text)
    if email_match:
        identity["email"] = email_match.group(0)
    phone_match = PHONE_RE.search(contact_text)
    if phone_match:
        identity["phone"] = phone_match.group(0)

    all_lines = [l.strip() for l in full_text.split("\n")]
    main_idx = len(all_lines)
    for idx, line in enumerate(all_lines):
        if line.lower() in ("experience", "summary", "about"):
            main_idx = idx
            break

    block = []
    i = main_idx - 1
    while i >= 0 and len(block) < 3:
        line = all_lines[i]
        i -= 1
        if not line:
            if block:
                break
            continue
        block.insert(0, line)

    if len(block) >= 3:
        identity["full_name"] = block[0]
        identity["headline"] = block[1]
        identity["location"] = block[2]
    elif len(block) == 2:
        identity["full_name"] = block[0]
        identity["headline"] = block[1]
    elif len(block) == 1:
        identity["full_name"] = block[0]

    return identity


DURATION_ONLY_RE = re.compile(
    r"^\d+\s+(?:year|month|day)s?(?:\s+\d+\s+(?:year|month|day)s?)?$",
    re.IGNORECASE,
)


def _parse_experience(lines: list[str]) -> list[dict]:
    """Parse experience section. LinkedIn format:
    Company
    Role
    Month Year - Month Year (Duration)
    Location (optional)
    Description lines...
    """
    if not lines:
        return []

    entries = []
    current_company = None
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue

        # Skip standalone duration lines like "2 years 9 months"
        if DURATION_ONLY_RE.match(line):
            i += 1
            continue

        # Skip orphaned date/duration lines
        if DATE_RANGE_RE.match(line) or (line.startswith("(") and DURATION_RE.search(line)):
            i += 1
            continue

        # Find the next date line within 3 lines
        date_line_idx = None
        for j in range(i + 1, min(i + 4, len(lines))):
            if j < len(lines) and lines[j] and DATE_RANGE_RE.search(lines[j]):
                date_line_idx = j
                break

        if date_line_idx is None:
            i += 1
            continue

        # Determine company/role based on gap to date line
        gap = date_line_idx - i
        company = None
        role = None

        if gap == 1:
            role = line
            company = current_company
        elif gap >= 2:
            company = line
            role = lines[i + 1]
            current_company = company

        dm = DATE_RANGE_RE.search(lines[date_line_idx])
        start_date = _normalize_date(dm.group(1)) if dm else None
        end_date = _normalize_date(dm.group(2)) if dm else None
        i = date_line_idx + 1

        # Skip "(3 months)" duration line
        if i < len(lines) and lines[i] and lines[i].startswith("(") and DURATION_RE.search(lines[i]):
            i += 1

        # Collect location + description until next entry
        description_parts = []
        while i < len(lines):
            dl = lines[i]
            if not dl:
                i += 1
                continue

            if DURATION_ONLY_RE.match(dl):
                break

            is_new = False
            for j in range(i, min(i + 3, len(lines))):
                if j < len(lines) and lines[j] and DATE_RANGE_RE.search(lines[j]):
                    is_new = True
                    break
            if is_new:
                break

            description_parts.append(dl)
            i += 1

        if role:
            desc_text = " ".join(description_parts).strip() if description_parts else None
            entries.append({
                "company": company or current_company or role,
                "role": role,
                "start_date": start_date,
                "end_date": end_date,
                "description": desc_text,
            })

    return entries


def _parse_education(lines: list[str]) -> list[dict]:
    """Parse education section."""
    if not lines:
        return []

    entries = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue

        institution = line
        degree = None
        field = None
        start_date = None
        end_date = None
        i += 1

        # Collect remaining lines for this entry
        detail_lines = []
        while i < len(lines):
            dl = lines[i]
            if not dl:
                i += 1
                continue

            # Check if this looks like a new institution
            # (a line not containing degree keywords, dates, or dots,
            # followed by degree-like content)
            is_degree_line = any(kw in dl.lower() for kw in [
                "bachelor", "master", "mba", "phd", "b.tech", "btech",
                "m.tech", "mtech", "pgdm", "diploma", "associate",
                "b.sc", "m.sc", "b.a.", "m.a.", "bba", "bca", "mca",
                "doctor", "engineering", "science", "arts", "commerce",
            ]) or "(" in dl or dl.startswith("·") or dl.startswith("- ")

            has_date = DATE_RANGE_RE.search(dl) or re.search(r"\d{4}\s*-\s*\d{4}", dl)

            if not is_degree_line and not has_date and detail_lines:
                # Probably a new institution
                break

            detail_lines.append(dl)
            i += 1

        # Parse detail lines for degree, field, dates
        full_detail = " ".join(detail_lines)

        # Extract dates
        date_match = re.search(r"\(?(\w*\s*\d{4})\s*-\s*(\w*\s*\d{4})\)?", full_detail)
        if date_match:
            s = date_match.group(1).strip()
            e = date_match.group(2).strip()
            year_s = re.search(r"(\d{4})", s)
            year_e = re.search(r"(\d{4})", e)
            if year_s:
                start_date = year_s.group(1)
            if year_e:
                end_date = year_e.group(1)

        # Extract degree and field
        degree_text = re.sub(r"\(.*?\)", "", full_detail).strip()
        degree_text = re.sub(r"[·].*", "", degree_text).strip()
        degree_text = degree_text.strip(" -·")

        if ", " in degree_text:
            parts = degree_text.split(", ", 1)
            degree = parts[0].strip()
            field = parts[1].strip()
        elif " - " in degree_text:
            parts = degree_text.split(" - ", 1)
            degree = parts[0].strip()
            field = parts[1].strip()
        elif degree_text:
            degree = degree_text

        if institution:
            entries.append({
                "institution": institution,
                "degree": degree,
                "field": field,
                "start_date": start_date,
                "end_date": end_date,
            })

    return entries


def parse_linkedin_pdf(raw_text: str, pdf_bytes: bytes | None = None) -> dict | None:
    """
    Parse LinkedIn PDF text using rules.
    If pdf_bytes is provided, uses spatial extraction for name/headline/location
    (100% reliable). Falls back to text-based extraction otherwise.
    Returns structured dict or None if it doesn't look like a LinkedIn PDF.
    """
    raw_text = _clean_text(raw_text)

    if "linkedin.com/in/" not in raw_text.lower():
        if not ("experience" in raw_text.lower() and "education" in raw_text.lower()):
            return None

    lines = [l.rstrip() for l in raw_text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)

    sections = _find_sections(lines)

    # Try spatial extraction first (uses PDF coordinates + font size)
    identity = None
    if pdf_bytes:
        identity = _extract_identity_spatial(pdf_bytes)
    if not identity or not identity.get("full_name"):
        identity = _extract_identity(sections, raw_text)

    if not identity.get("full_name"):
        return None

    experience = _parse_experience(sections.get("experience", []))
    education = _parse_education(sections.get("education", []))

    # Clean leaked name/headline/location from skills sections
    identity_text = " ".join(
        identity.get(k, "") or "" for k in ("full_name", "headline", "location")
    )

    def _is_identity_leak(s: str) -> bool:
        if not s.strip():
            return True
        if s in (identity.get("full_name"), identity.get("headline"), identity.get("location")):
            return True
        # Multi-line headline fragments: long or contain | @ characters
        if identity.get("headline") and s.rstrip(",") in identity["headline"]:
            if len(s) > 25 or any(c in s for c in "|@"):
                return True
        return False

    skills_raw = sections.get("top skills", []) or sections.get("skills", [])
    skills_raw = [s for s in skills_raw if not _is_identity_leak(s)]

    summary_lines = sections.get("summary", [])
    summary = " ".join(l for l in summary_lines if l.strip()).strip() or None

    certifications = [l for l in sections.get("certifications", []) if l.strip()]

    # Derive headline from experience if missing
    if not identity.get("headline") and experience:
        role = experience[0].get("role", "")
        comp = experience[0].get("company", "")
        if role and comp:
            identity["headline"] = f"{role} at {comp}"
        elif role:
            identity["headline"] = role

    result = {
        "identity": identity,
        "summary": summary,
        "experience": experience,
        "education": education,
        "skills": {
            "original": skills_raw,
            "normalized": skills_raw,
        },
        "total_experience_months": 0,
        "other_sections": {
            "certifications": certifications,
            "projects": [],
            "publications": [],
            "languages": [],
            "awards": [],
        },
    }

    logger.info(
        f"Rule-based parse: {identity.get('full_name')} - "
        f"{len(experience)} exp, {len(education)} edu, {len(skills_raw)} skills"
    )

    return result
