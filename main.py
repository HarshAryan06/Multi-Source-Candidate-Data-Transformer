import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


# A small fixed dictionary keeps skill extraction deterministic and easy to explain.
SKILL_ALIASES = {
    "py": "Python",
    "python": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "react": "React",
    "node": "Node.js",
    "node.js": "Node.js",
    "sql": "SQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "aws": "AWS",
    "airflow": "Airflow",
    "dbt": "dbt",
    "docker": "Docker",
    "excel": "Excel",
    "figma": "Figma",
    "kubernetes": "Kubernetes",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "power bi": "Power BI",
    "pytest": "Pytest",
    "selenium": "Selenium",
    "snowflake": "Snowflake",
    "spark": "Spark",
    "tableau": "Tableau",
    "terraform": "Terraform",
}


def clean_text(value):
    if value is None:
        return None
    value = " ".join(value.strip().split())
    return value or None


def normalize_email(value):
    value = clean_text(value)
    if not value:
        return None
    value = value.lower()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return value
    return None


def normalize_phone(value):
    value = clean_text(value)
    if not value:
        return None

    digits = re.sub(r"\D", "", value)
    if not digits:
        return None

    if value.startswith("+"):
        return "+" + digits
    if len(digits) == 10:
        return "+91" + digits
    if len(digits) > 10:
        return "+" + digits
    return None


def normalize_location(value):
    value = clean_text(value)
    if not value:
        return None

    parts = [part.strip() for part in value.split(",") if part.strip()]
    country_map = {
        "in": "IN",
        "india": "IN",
        "us": "US",
        "usa": "US",
        "united states": "US",
        "uk": "GB",
        "united kingdom": "GB",
    }

    city = parts[0] if len(parts) > 0 else None
    region = parts[1] if len(parts) > 1 else None
    country = parts[2] if len(parts) > 2 else None
    if country:
        country = country_map.get(country.lower(), country.upper())

    return {"city": city, "region": region, "country": country}


def read_csv_rows(path):
    rows = []
    warnings = []
    csv_path = Path(path)

    if not csv_path.exists():
        return rows, [f"csv file missing: {csv_path}"]

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row_number, row in enumerate(reader, start=2):
            email = normalize_email(row.get("email"))
            if row.get("email") and not email:
                warnings.append(f"row {row_number}: invalid email ignored")

            rows.append(
                {
                    "row_number": row_number,
                    "name": clean_text(row.get("name")),
                    "email": email,
                    "phone": normalize_phone(row.get("phone")),
                    "current_company": clean_text(row.get("current_company")),
                    "title": clean_text(row.get("title")),
                }
            )

    return rows, warnings


def read_notes(path):
    notes_path = Path(path)
    if not notes_path.exists():
        return [], [f"notes file missing: {notes_path}"]

    text = notes_path.read_text(encoding="utf-8")
    if not text.strip():
        return [], [f"notes file empty: {notes_path}"]

    sections = re.split(r"^\s*---+\s*$", text, flags=re.MULTILINE)
    notes = []
    for section_number, section in enumerate(sections, start=1):
        section = section.strip()
        if section:
            notes.append(parse_note_section(section, section_number))

    return notes, []


def parse_note_section(text, section_number):
    return {
        "section_number": section_number,
        "name": get_label(text, "Name"),
        "headline": get_label(text, "Headline"),
        "location": normalize_location(get_label(text, "Location")),
        "email": normalize_email(find_first_email(text)),
        "phone": normalize_phone(find_first_phone(text)),
        "years_experience": find_years_experience(text),
        "skills": find_skills(text),
    }


def get_label(text, label):
    pattern = rf"^{re.escape(label)}\s*:\s*(.+)$"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if match:
        return clean_text(match.group(1))
    return None


def find_first_email(text):
    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None


def find_first_phone(text):
    match = re.search(r"(?:\+\d{1,3}[\s-]?)?(?:\d[\s-]?){10,14}", text)
    return match.group(0) if match else None


def find_years_experience(text):
    match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\b", text, flags=re.IGNORECASE)
    return float(match.group(1)) if match else None


def find_skills(text):
    found = []
    lower_text = text.lower()

    for alias, skill in sorted(SKILL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = r"(?<![a-z0-9.+#])" + re.escape(alias) + r"(?![a-z0-9.+#])"
        if re.search(pattern, lower_text) and skill not in found:
            found.append(skill)

    return found


def empty_profile():
    return {
        "candidate_id": None,
        "full_name": None,
        "emails": [],
        "phones": [],
        "location": None,
        "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
        "headline": None,
        "years_experience": None,
        "skills": [],
        "experience": [],
        "education": [],
        "provenance": [],
        "overall_confidence": 0.0,
        "warnings": [],
    }


def build_profile(all_csv_rows, note, source_warnings):
    profile = empty_profile()
    profile["warnings"].extend(source_warnings)

    matched_rows = find_matching_csv_rows(all_csv_rows, note, profile["warnings"])

    for row in matched_rows:
        add_single_value(profile, "full_name", row["name"], csv_source(row), "csv name", 0.95)

    if not profile["full_name"] and note:
        add_single_value(profile, "full_name", note["name"], notes_source(note), "notes name", 0.70)

    for row in matched_rows:
        add_list_value(profile, "emails", row["email"], csv_source(row), "csv email", 0.95)
    if note:
        add_list_value(profile, "emails", note["email"], notes_source(note), "notes email", 0.75)

    for row in matched_rows:
        add_list_value(profile, "phones", row["phone"], csv_source(row), "csv phone", 0.90)
    if note:
        add_list_value(profile, "phones", note["phone"], notes_source(note), "notes phone", 0.70)

    if note:
        add_single_value(profile, "headline", note["headline"], notes_source(note), "notes headline", 0.75)
        add_single_value(profile, "location", note["location"], notes_source(note), "notes location", 0.70)
        add_single_value(
            profile,
            "years_experience",
            note["years_experience"],
            notes_source(note),
            "notes years of experience",
            0.65,
        )

    if not profile["headline"]:
        for row in matched_rows:
            add_single_value(profile, "headline", row["title"], csv_source(row), "csv title", 0.85)
            if profile["headline"]:
                break

    add_experience(profile, matched_rows)
    add_skills(profile, note)

    profile["candidate_id"] = make_candidate_id(profile)
    profile["overall_confidence"] = calculate_confidence(profile)
    return profile


def find_matching_csv_rows(csv_rows, note, warnings):
    if not csv_rows:
        return []
    if not note:
        return csv_rows[:1]

    matched = []
    for row in csv_rows:
        same_email = note["email"] and row["email"] == note["email"]
        same_phone = note["phone"] and row["phone"] == note["phone"]
        same_name = names_look_same(row["name"], note["name"])

        if same_email or same_phone or same_name:
            matched.append(row)

    if matched:
        skipped_count = len(csv_rows) - len(matched)
        if skipped_count:
            warnings.append(f"ignored {skipped_count} csv rows for other candidates")
        return matched

    warnings.append("no matching csv row found; used first row as fallback")
    return csv_rows[:1]


def names_look_same(left, right):
    if not left or not right:
        return False
    left_words = {word.lower().strip(".") for word in left.split() if len(word.strip(".")) > 1}
    right_words = {word.lower().strip(".") for word in right.split() if len(word.strip(".")) > 1}
    return left_words <= right_words or right_words <= left_words


def add_single_value(profile, field, value, source, method, confidence):
    if value in (None, "", []):
        return

    if profile[field] in (None, "", []):
        profile[field] = value
        add_provenance(profile, field, source, method, confidence)
    elif profile[field] != value:
        profile["warnings"].append(f"conflict on {field}; kept earlier value")


def add_list_value(profile, field, value, source, method, confidence):
    if not value:
        return

    if value not in profile[field]:
        if profile[field]:
            profile["warnings"].append(f"extra {field} value found from {source}")
        profile[field].append(value)

    add_provenance(profile, field, source, method, confidence)


def add_experience(profile, csv_rows):
    seen = set()
    for row in csv_rows:
        company = row["current_company"]
        title = row["title"]
        if not company and not title:
            continue

        key = (company, title)
        if key in seen:
            continue

        seen.add(key)
        index = len(profile["experience"])
        profile["experience"].append(
            {
                "company": company,
                "title": title,
                "start": None,
                "end": None,
                "summary": "Current role from recruiter CSV",
            }
        )
        add_provenance(profile, f"experience[{index}]", csv_source(row), "csv company/title", 0.85)


def add_skills(profile, note):
    if not note:
        return

    for skill in note["skills"]:
        profile["skills"].append(
            {
                "name": skill,
                "confidence": 0.68,
                "sources": ["recruiter_notes"],
            }
        )
        add_provenance(profile, f"skills[{skill}]", notes_source(note), "skill keyword match", 0.68)


def add_provenance(profile, field, source, method, confidence):
    profile["provenance"].append(
        {
            "field": field,
            "source": source,
            "method": method,
            "confidence": round(confidence, 2),
        }
    )


def csv_source(row):
    return f"recruiter_csv row {row['row_number']}"


def notes_source(note):
    return f"recruiter_notes section {note['section_number']}"


def make_candidate_id(profile):
    key = profile["emails"][0] if profile["emails"] else profile["full_name"] or "unknown"
    return "cand_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def calculate_confidence(profile):
    scores = [item["confidence"] for item in profile["provenance"]]
    if not scores:
        return 0.0

    warning_penalty = min(0.20, len(profile["warnings"]) * 0.03)
    return round(max(0.0, sum(scores) / len(scores) - warning_penalty), 2)


def validate_profile(profile):
    required_fields = [
        "candidate_id",
        "full_name",
        "emails",
        "phones",
        "location",
        "links",
        "headline",
        "years_experience",
        "skills",
        "experience",
        "education",
        "provenance",
        "overall_confidence",
    ]

    errors = []
    for field in required_fields:
        if field not in profile:
            errors.append(f"missing field: {field}")

    if not isinstance(profile["emails"], list):
        errors.append("emails must be a list")
    if not isinstance(profile["phones"], list):
        errors.append("phones must be a list")
    if not 0 <= profile["overall_confidence"] <= 1:
        errors.append("overall_confidence must be between 0 and 1")

    return errors


def load_config(path):
    if not path:
        return None
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def project_profile(profile, config):
    if not config:
        return profile

    output = {}
    missing_rule = config.get("on_missing", "null")

    for field in config.get("fields", []):
        output_name = field["path"]
        source_path = field.get("from", output_name)
        value = get_value(profile, source_path)

        if value is None:
            if field.get("required") or missing_rule == "error":
                raise ValueError(f"missing required value: {source_path}")
            if missing_rule == "omit":
                continue

        set_value(output, output_name, value)

    if config.get("include_confidence"):
        output["overall_confidence"] = profile["overall_confidence"]
    if config.get("include_provenance"):
        output["provenance"] = profile["provenance"]

    return output


def get_value(data, path):
    if "[]" in path:
        list_name, child_key = path.split("[].", 1)
        items = data.get(list_name)
        if not isinstance(items, list):
            return None
        return [item.get(child_key) for item in items if isinstance(item, dict) and child_key in item]

    current = data
    for part in path.split("."):
        list_match = re.fullmatch(r"(\w+)\[(\d+)\]", part)
        if list_match:
            key = list_match.group(1)
            index = int(list_match.group(2))
            if not isinstance(current, dict) or key not in current or index >= len(current[key]):
                return None
            current = current[key][index]
        else:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
    return current


def set_value(data, path, value):
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def run_pipeline(csv_path, notes_path, config_path=None, all_candidates=False):
    csv_rows, csv_warnings = read_csv_rows(csv_path)
    notes, note_warnings = read_notes(notes_path)
    config = load_config(config_path)
    source_warnings = csv_warnings + note_warnings

    if all_candidates:
        profiles = []
        outputs = []
        for note in notes:
            profile = build_profile(csv_rows, note, source_warnings)
            errors = validate_profile(profile)
            if errors:
                raise ValueError("; ".join(errors))
            profiles.append(profile)
            outputs.append(project_profile(profile, config))
        return profiles, outputs

    first_note = notes[0] if notes else None
    profile = build_profile(csv_rows, first_note, source_warnings)
    errors = validate_profile(profile)
    if errors:
        raise ValueError("; ".join(errors))
    return profile, project_profile(profile, config)


def write_json(path, data):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Transform candidate CSV and notes into clean JSON.")
    parser.add_argument("--csv", required=True, help="Path to recruiter CSV file")
    parser.add_argument("--notes", required=True, help="Path to recruiter notes text file")
    parser.add_argument("--config", help="Optional output config JSON")
    parser.add_argument("--out", help="Where to write the final JSON")
    parser.add_argument("--canonical-out", help="Optional full canonical JSON output path")
    parser.add_argument("--all-candidates", action="store_true", help="Process every candidate in notes.txt")
    args = parser.parse_args()

    canonical, final_output = run_pipeline(
        args.csv,
        args.notes,
        args.config,
        all_candidates=args.all_candidates,
    )

    if args.canonical_out:
        write_json(args.canonical_out, canonical)

    if args.out:
        write_json(args.out, final_output)
        print(f"wrote {args.out}")
    else:
        print(json.dumps(final_output, indent=2))


if __name__ == "__main__":
    main()
