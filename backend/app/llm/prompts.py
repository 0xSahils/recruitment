RESUME_PARSE_SYSTEM = """You are a precise resume data extraction engine. You extract structured JSON from LinkedIn PDF text.
Return ONLY valid JSON. No markdown, no commentary, no extra text."""

RESUME_PARSE_PROMPT = """Extract structured data from this LinkedIn PDF resume text.

IMPORTANT LinkedIn PDF layout:
- The person's name is usually the FIRST line.
- The headline/title is the line right AFTER the name (e.g. "Software Engineer at Google").
- Location follows, usually a city like "Bangalore, India" or "New York, USA".
- "Contact" section may contain email, phone, LinkedIn URL (linkedin.com/in/...).
- "Top Skills" or "Skills" section lists skills.
- "Summary" or "About" section has a paragraph about them.
- "Experience" section has jobs with company, role, dates (like "Jan 2020 - Present" or "2019 - 2021").
- "Education" section has institution, degree, field, dates.

Return this exact JSON schema:

{{
  "identity": {{
    "linkedin_url": "the linkedin.com/in/... URL or null",
    "full_name": "person's full name (REQUIRED - first line of resume)",
    "headline": "their job title/headline (line after the name) or null",
    "location": "city, country or null",
    "email": "email address or null",
    "phone": "phone number or null"
  }},
  "summary": "the About/Summary paragraph or null",
  "experience": [
    {{
      "company": "company name",
      "role": "job title/position",
      "start_date": "YYYY-MM format (e.g. 2020-01 for Jan 2020)",
      "end_date": "YYYY-MM format or null if current/present job",
      "description": "job description text or null"
    }}
  ],
  "education": [
    {{
      "institution": "school/university name",
      "degree": "degree type (B.Tech, MBA, etc.) or null",
      "field": "field of study or null",
      "start_date": "YYYY or null",
      "end_date": "YYYY or null"
    }}
  ],
  "skills": {{
    "original": ["exact skill names from resume"],
    "normalized": ["expanded individual skills"]
  }},
  "total_experience_months": 0
}}

Date rules:
- Convert ALL dates to YYYY-MM format. "Jan 2020" → "2020-01". "March 2019" → "2019-03". "2021" → "2021-01".
- Month mapping: Jan=01, Feb=02, Mar=03, Apr=04, May=05, Jun=06, Jul=07, Aug=08, Sep=09, Oct=10, Nov=11, Dec=12
- If job is current/present, set end_date to null.
- Calculate total_experience_months by adding up all job durations.

Extraction rules:
- Extract the headline — it is almost always on line 2 of a LinkedIn PDF, right below the name.
- Extract ALL experience entries in order (most recent first).
- For skills: list exactly as found, then expand abbreviations (e.g. "MERN" → ["MongoDB", "Express.js", "React", "Node.js"]).
- Never invent data. Use null for missing strings, empty arrays for missing lists.

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
