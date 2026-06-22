import fitz, sys
sys.path.insert(0, ".")
from app.parsing.linkedin_parser import _split_sections, _parse_header, _parse_experience, parse_linkedin_pdf

doc = fitz.open(r"C:\Users\sahil\Downloads\Profile (10).pdf")
text = "\n".join(p.get_text("text") for p in doc if p.get_text("text").strip())
doc.close()

# Normalize
text = text.replace("\xa0", " ").replace("’", "'").replace("‘", "'")
text = text.replace("“", '"').replace("”", '"')
text = text.replace("–", "-").replace("—", "-")

sections = _split_sections(text)
print("Sections found:", list(sections.keys()))
print()
for k, v in sections.items():
    print(f"--- {k} ---")
    print(v[:300])
    print()

identity = _parse_header(sections.get("_header", ""))
print("Identity:", identity)
