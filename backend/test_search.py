"""Test search components."""
import sys
sys.path.insert(0, ".")

from app.search.jd_parser import _rule_based_parse
from app.search.scorer import _skill_match, compute_skill_score, compute_role_score

print("=== JD Parser Tests ===\n")
tests = [
    "React developer",
    "Python developer in Bangalore with 5+ years",
    "fiber engineer",
    "software engineer with docker kubernetes",
    "talent acquisition specialist noida",
    "full stack developer react node.js",
    "data scientist machine learning 3-5 years",
    "SDE",
    "research analyst",
    "hardware engineer altium",
]

for q in tests:
    r = _rule_based_parse(q)
    print(f'Q: "{q}"')
    print(f'  role={r["role"]}, skills={r["required_skills"]}, loc={r["location"]}, exp={r["experience"]}')
    print()


print("=== Skill Match Tests ===\n")
skills = {"react", "node.js", "python", "docker", "typescript"}
match_tests = [
    ("react", skills),
    ("reactjs", skills),
    ("nodejs", skills),
    ("java", skills),
    ("ts", skills),
    ("javascript", skills),
]
for query_skill, cand_skills in match_tests:
    score = _skill_match(query_skill, cand_skills)
    print(f"  {query_skill} vs {cand_skills}: {score}")


print("\n=== Role Score Tests ===\n")
role_tests = [
    ("Software Engineer", "SDE2", "Software Engineer @WheelsEye"),
    ("Software Engineer", "Fiber Engineer", "Fiber Engineer ||Amdocs"),
    ("React Developer", "Full Stack Engineer", "Full Stack Developer | React, Next.js"),
    ("Data Scientist", "Associate - Research", "Research & Data Analyst"),
    ("Fiber Engineer", "Fiber Engineer", "Fiber Engineer ||Amdocs"),
]
for jd_role, cand_role, cand_headline in role_tests:
    score = compute_role_score(cand_role, cand_headline, jd_role)
    print(f'  "{jd_role}" vs role="{cand_role}" headline="{cand_headline}": {score}')
