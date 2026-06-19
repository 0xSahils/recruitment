RESUME_PARSE_SYSTEM = """You are a precise data extraction engine. Extract structured information from LinkedIn PDF resume text.
Return ONLY valid JSON matching the exact schema below. Do not add commentary or markdown."""

RESUME_PARSE_PROMPT = """Extract all information from the following LinkedIn resume text into this exact JSON structure:

{{
  "identity": {{
    "linkedin_url": "string or null",
    "full_name": "string (required)",
    "headline": "string or null",
    "location": "string or null",
    "email": "string or null",
    "phone": "string or null"
  }},
  "summary": "string or null (the About section)",
  "experience": [
    {{
      "company": "string",
      "role": "string",
      "start_date": "YYYY-MM or null",
      "end_date": "YYYY-MM or null (null means current/present)",
      "description": "string or null"
    }}
  ],
  "education": [
    {{
      "institution": "string",
      "degree": "string or null",
      "field": "string or null",
      "start_date": "YYYY or null",
      "end_date": "YYYY or null"
    }}
  ],
  "skills": {{
    "original": ["list of skills exactly as written in the resume"],
    "normalized": ["list of individual technology/skill names expanded from originals"]
  }},
  "total_experience_months": 0,
  "other_sections": {{
    "certifications": [],
    "projects": [],
    "publications": [],
    "languages": [],
    "awards": []
  }}
}}

Rules:
- Extract ALL experience entries, preserving their order from top (most recent) to bottom.
- For dates, use YYYY-MM format. If only year is given, use YYYY. If "Present" or current, set end_date to null.
- Calculate total_experience_months by summing all experience durations. If dates are missing, estimate from context.
- For skills: list skills exactly as found in "Top Skills" or "Skills" sections as "original". Then expand abbreviations into individual skills for "normalized" (e.g., "MERN" → ["MongoDB", "Express.js", "React", "Node.js"]).
- If a field is not found in the text, set it to null (for strings) or empty array (for lists).
- Never invent information not present in the text.

--- RESUME TEXT ---
{resume_text}
--- END ---"""

JD_PARSE_SYSTEM = """You are a job description parser. Extract structured search criteria from job descriptions or natural language queries.
Return ONLY valid JSON."""

JD_PARSE_PROMPT = """Parse the following job description or search query into structured criteria:

{{
  "role": "string or null (the job title being searched for)",
  "required_skills": ["list of must-have skills"],
  "preferred_skills": ["list of nice-to-have skills"],
  "experience": {{
    "min_years": null or number,
    "max_years": null or number
  }},
  "location": "string or null",
  "industry": "string or null"
}}

Rules:
- Distinguish required vs preferred skills. If unclear, put in required.
- Parse experience requirements like "5+ years" → min_years: 5, max_years: null
- Parse "3-5 years" → min_years: 3, max_years: 5
- Extract location if mentioned (city, state, country, or "remote")
- If the input is a natural language query like "React developers in Bangalore with 5+ years", parse it the same way.

--- INPUT ---
{query_text}
--- END ---"""

MATCH_EXPLANATION_SYSTEM = """You are a recruitment match explainer. Generate concise bullet points explaining why a candidate matches a job description."""

MATCH_EXPLANATION_PROMPT = """Given this candidate profile and job requirements, generate 2-4 concise bullet points explaining why this candidate is a match.

Job Requirements:
- Role: {role}
- Required Skills: {required_skills}
- Preferred Skills: {preferred_skills}
- Experience: {experience_req}
- Location: {location}

Candidate:
- Name: {candidate_name}
- Headline: {headline}
- Current Role: {current_role} at {current_company}
- Location: {candidate_location}
- Total Experience: {experience_months} months
- Skills: {candidate_skills}

Return JSON: {{"explanations": ["bullet point 1", "bullet point 2", ...]}}

Keep each bullet under 80 characters. Be specific — mention actual skill names, years, and companies."""
