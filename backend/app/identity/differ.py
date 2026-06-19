def generate_changes_summary(old: dict, new: dict) -> list[str]:
    changes = []

    old_identity = old.get("identity", {})
    new_identity = new.get("identity", {})
    for field in ["full_name", "headline", "location", "email", "phone"]:
        old_val = old_identity.get(field)
        new_val = new_identity.get(field)
        if old_val != new_val:
            if old_val and new_val:
                changes.append(f'~ Changed {field} from "{old_val}" to "{new_val}"')
            elif new_val:
                changes.append(f"+ Added {field}: {new_val}")

    if old.get("summary") != new.get("summary") and new.get("summary"):
        changes.append("~ Updated summary/about section")

    old_exp = {(e.get("company", ""), e.get("role", "")) for e in old.get("experience", [])}
    new_exp = {(e.get("company", ""), e.get("role", "")) for e in new.get("experience", [])}
    for company, role in new_exp - old_exp:
        changes.append(f"+ Added {role} role at {company}")
    for company, role in old_exp - new_exp:
        changes.append(f"- Removed {role} role at {company}")

    old_edu = {e.get("institution", "") for e in old.get("education", [])}
    new_edu = {e.get("institution", "") for e in new.get("education", [])}
    for inst in new_edu - old_edu:
        changes.append(f"+ Added education at {inst}")

    old_skills = set(old.get("skills", {}).get("original", []))
    new_skills = set(new.get("skills", {}).get("original", []))
    for skill in new_skills - old_skills:
        changes.append(f"+ Added {skill} skill")
    for skill in old_skills - new_skills:
        changes.append(f"- Removed {skill} skill")

    old_months = old.get("total_experience_months", 0)
    new_months = new.get("total_experience_months", 0)
    if old_months != new_months:
        changes.append(f"~ Total experience changed from {old_months} to {new_months} months")

    if not changes:
        changes.append("No significant changes detected")

    return changes
