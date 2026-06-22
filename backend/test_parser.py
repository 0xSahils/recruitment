"""Quick test of the rule-based LinkedIn parser."""
import fitz
import sys
import glob
import os

sys.path.insert(0, ".")
from app.parsing.linkedin_parser import parse_linkedin_pdf
from app.parsing.validators import sanitize_parsed_data


def test_pdf(path):
    with open(path, "rb") as f:
        pdf_bytes = f.read()

    doc = fitz.open(path)
    text = "\n".join(p.get_text("text") for p in doc if p.get_text("text").strip())
    doc.close()

    parsed = parse_linkedin_pdf(text, pdf_bytes=pdf_bytes)
    if not parsed:
        print(f"  FAILED: returned None")
        return

    parsed = sanitize_parsed_data(parsed)
    ident = parsed["identity"]
    print(f"  Name: {ident['full_name']}")
    print(f"  Headline: {ident.get('headline')}")
    print(f"  Location: {ident.get('location')}")
    print(f"  LinkedIn: {ident.get('linkedin_url')}")
    print(f"  Email: {ident.get('email')}")
    print(f"  Exp months: {parsed['total_experience_months']}")
    print(f"  Skills: {parsed['skills']['original']}")

    for i, exp in enumerate(parsed.get("experience", [])):
        desc = (exp.get("description") or "")[:80]
        print(f"  Exp {i+1}: {exp['role']} at {exp['company']} ({exp.get('start_date')} -> {exp.get('end_date')}) | {desc}")

    for edu in parsed.get("education", []):
        print(f"  Edu: {edu.get('degree')} @ {edu['institution']} ({edu.get('start_date')}-{edu.get('end_date')})")
    print()


if __name__ == "__main__":
    pdfs = sorted(glob.glob(r"C:\Users\sahil\Downloads\Profile*.pdf"))
    for pdf in pdfs:
        print(f"=== {os.path.basename(pdf)} ===")
        try:
            test_pdf(pdf)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
        print()
