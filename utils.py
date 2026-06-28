# ============================================================
# utils.py — Helper Functions
# INDIA RUNS Hiring Challenge | Hack2skill x Redrob
# Author: Er. Priya More
# ============================================================
# This file handles:
# 1. Loading candidates from candidates.jsonl
# 2. Detecting honeypot (fake) candidates
# 3. Applying hard filters based on JD rules
# 4. Helper functions to extract candidate data
# ============================================================

import json
import os
from datetime import datetime
from dateutil import parser as date_parser
from tqdm import tqdm


# ─────────────────────────────────────────────────────
# SECTION 1: DATA LOADING
# ─────────────────────────────────────────────────────

def load_candidates(filepath: str, max_candidates: int = None) -> list:
    """
    Load candidates from a JSONL file.
    JSONL format: each line is a separate JSON object.

    Args:
        filepath: Path to candidates.jsonl
        max_candidates: Limit how many to load (None = load all)
                        Use 100 for quick testing
    Returns:
        List of candidate dictionaries
    """
    candidates = []

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return []

    print(f"Loading candidates from: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(tqdm(f, desc="Loading candidates")):

            if max_candidates and i >= max_candidates:
                break

            line = line.strip()
            if not line:
                continue

            try:
                candidate = json.loads(line)
                candidates.append(candidate)
            except json.JSONDecodeError:
                continue

    print(f"Successfully loaded {len(candidates)} candidates!")
    return candidates


def load_sample_candidates(filepath: str) -> list:
    """
    Load sample_candidates.json (50 candidates for testing).
    This is a pretty-printed JSON array, not JSONL.
    """
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    print(f"Successfully loaded {len(candidates)} sample candidates!")
    return candidates


# ─────────────────────────────────────────────────────
# SECTION 2: HONEYPOT DETECTION
# ─────────────────────────────────────────────────────
# Honeypots are fake/impossible profiles planted by organizers as traps.
# If top 100 contains more than 10 honeypots -> DISQUALIFIED!

def is_honeypot(candidate: dict) -> tuple:
    """
    Check whether a candidate profile is fake or impossible.

    Returns:
        (True, reason)  if honeypot detected
        (False, "")     if candidate looks genuine
    """
    flags = []

    profile   = candidate.get("profile", {})
    career    = candidate.get("career_history", [])
    education = candidate.get("education", [])
    skills    = candidate.get("skills", [])
    signals   = candidate.get("redrob_signals", {})

    stated_exp = profile.get("years_of_experience", 0)

    # Check 1: Career history longer than stated experience
    if career:
        total_months = sum(job.get("duration_months", 0) for job in career)
        total_years  = total_months / 12
        if total_years > stated_exp + 3:
            flags.append(
                f"Career history ({total_years:.1f} yrs) exceeds "
                f"stated experience ({stated_exp} yrs) by 3+ years"
            )

    # Check 2: Impossible education dates
    for edu in education:
        start = edu.get("start_year", 0)
        end   = edu.get("end_year",   0)

        if start and end and (end - start) > 10:
            flags.append(f"Education duration too long: {end - start} years")

        if end and end > 2026:
            flags.append(f"Education end year is in the future: {end}")

        if start and start < 1970:
            flags.append(f"Education start year too old: {start}")

    # Check 3: Experience out of human range
    if stated_exp > 40:
        flags.append(f"Experience unrealistically high: {stated_exp} years")

    # Check 4: Fresher with too many expert skills
    if stated_exp <= 1:
        expert_skills = [
            s for s in skills
            if s.get("proficiency") in ["advanced", "expert"]
        ]
        if len(expert_skills) > 15:
            flags.append(
                f"Fresher with {len(expert_skills)} advanced/expert skills"
            )

    # Check 5: Invalid signal values
    response_rate  = signals.get("recruiter_response_rate", 0)
    interview_rate = signals.get("interview_completion_rate", 0)

    if not (0 <= response_rate <= 1):
        flags.append(f"Invalid recruiter_response_rate: {response_rate}")

    if not (0 <= interview_rate <= 1):
        flags.append(f"Invalid interview_completion_rate: {interview_rate}")

    # Check 6: Last active date before signup date
    signup_str      = signals.get("signup_date", "")
    last_active_str = signals.get("last_active_date", "")

    if signup_str and last_active_str:
        try:
            signup_dt = date_parser.parse(signup_str)
            active_dt = date_parser.parse(last_active_str)
            if active_dt < signup_dt:
                flags.append(
                    f"Last active ({last_active_str}) is before "
                    f"signup date ({signup_str})"
                )
        except Exception:
            pass

    if flags:
        return True, " | ".join(flags)
    return False, ""


def filter_honeypots(candidates: list) -> tuple:
    """
    Remove all honeypot candidates from the pool.

    Returns:
        (clean_candidates, honeypot_candidates)
    """
    clean     = []
    honeypots = []

    for c in tqdm(candidates, desc="Detecting honeypots"):
        is_fake, reason = is_honeypot(c)
        if is_fake:
            c["_honeypot_reason"] = reason
            honeypots.append(c)
        else:
            clean.append(c)

    print(f"Clean candidates  : {len(clean)}")
    print(f"Honeypots removed : {len(honeypots)}")
    return clean, honeypots


# ─────────────────────────────────────────────────────
# SECTION 3: HARD FILTERS
# ─────────────────────────────────────────────────────
# The JD explicitly states certain disqualifiers.
# Remove these candidates before scoring to save time.

def apply_hard_filters(candidates: list) -> tuple:
    """
    Apply JD-based hard filters to remove clearly unsuitable candidates.

    Filters:
    - Inactive for more than 6 months
    - Entire career only in pure consulting firms
    - Not open to work AND response rate below 5%

    Returns:
        (passed_candidates, filtered_out_candidates)
    """
    passed   = []
    filtered = []

    PURE_CONSULTING = {
        "tcs", "infosys", "wipro", "accenture",
        "cognizant", "capgemini", "hcl", "tech mahindra"
    }

    today = datetime.now().date()

    for c in tqdm(candidates, desc="Applying hard filters"):
        signals = c.get("redrob_signals", {})
        career  = c.get("career_history", [])

        # Filter 1: Inactive for more than 6 months
        last_active_str = signals.get("last_active_date", "")
        if last_active_str:
            try:
                last_active   = date_parser.parse(last_active_str).date()
                days_inactive = (today - last_active).days
                if days_inactive > 180:
                    c["_filter_reason"] = f"Inactive for {days_inactive} days"
                    filtered.append(c)
                    continue
            except Exception:
                pass

        # Filter 2: Entire career in pure consulting firms
        if career:
            companies = [job.get("company", "").lower() for job in career]
            is_pure_consulting = all(
                any(firm in company for firm in PURE_CONSULTING)
                for company in companies if company
            )
            if is_pure_consulting and len(companies) > 0:
                c["_filter_reason"] = "Entire career in pure consulting firms"
                filtered.append(c)
                continue

        # Filter 3: Not open to work + near-zero response rate
        open_to_work  = signals.get("open_to_work_flag", False)
        response_rate = signals.get("recruiter_response_rate", 0)

        if not open_to_work and response_rate < 0.05:
            c["_filter_reason"] = "Not open to work + response rate < 5%"
            filtered.append(c)
            continue

        passed.append(c)

    print(f"Candidates passed filters : {len(passed)}")
    print(f"Candidates filtered out   : {len(filtered)}")
    return passed, filtered


# ─────────────────────────────────────────────────────
# SECTION 4: DATA EXTRACTION HELPERS
# ─────────────────────────────────────────────────────

def get_skills_list(candidate: dict) -> list:
    """Return a lowercase list of all skill names for a candidate."""
    return [s.get("name", "").lower() for s in candidate.get("skills", [])]


def get_skill_proficiency(candidate: dict, skill_name: str) -> str:
    """
    Return proficiency level for a given skill.
    Returns: 'expert' | 'advanced' | 'intermediate' | 'beginner' | 'none'
    """
    for s in candidate.get("skills", []):
        if s.get("name", "").lower() == skill_name.lower():
            return s.get("proficiency", "none")
    return "none"


def get_skill_duration(candidate: dict, skill_name: str) -> int:
    """Return how many months a candidate has used a specific skill."""
    for s in candidate.get("skills", []):
        if s.get("name", "").lower() == skill_name.lower():
            return s.get("duration_months", 0)
    return 0


def get_assessment_score(candidate: dict, skill_name: str) -> float:
    """
    Return the Redrob platform assessment score for a skill (0-100).
    Returns 0.0 if no assessment was taken.
    """
    assessments = candidate.get("redrob_signals", {}).get(
        "skill_assessment_scores", {}
    )
    for key, value in assessments.items():
        if key.lower() == skill_name.lower():
            return value
    return 0.0


def get_top_education(candidate: dict) -> dict:
    """Return the highest degree education entry for a candidate."""
    education = candidate.get("education", [])
    if not education:
        return {}

    DEGREE_RANK = {
        "phd": 4, "doctorate": 4,
        "m.tech": 3, "m.e.": 3, "master": 3, "mba": 3, "m.sc": 3,
        "b.tech": 2, "b.e.": 2, "bachelor": 2, "b.sc": 2,
        "diploma": 1
    }

    best      = education[0]
    best_rank = 0

    for edu in education:
        degree = edu.get("degree", "").lower()
        for key, rank in DEGREE_RANK.items():
            if key in degree and rank > best_rank:
                best      = edu
                best_rank = rank

    return best


def get_days_since_active(candidate: dict) -> int:
    """
    Return how many days ago the candidate was last active.
    Lower is better. Returns 999 if date is unknown.
    """
    last_active_str = candidate.get("redrob_signals", {}).get(
        "last_active_date", ""
    )
    if not last_active_str:
        return 999

    try:
        last_active = date_parser.parse(last_active_str).date()
        return (datetime.now().date() - last_active).days
    except Exception:
        return 999


def get_candidate_summary(candidate: dict) -> str:
    """Return a one-line summary string for quick display."""
    profile = candidate.get("profile", {})
    name    = profile.get("anonymized_name", "Unknown")
    title   = profile.get("current_title", "N/A")
    exp     = profile.get("years_of_experience", 0)
    loc     = profile.get("location", "N/A")
    return f"{name} | {title} | {exp} yrs | {loc}"


# ─────────────────────────────────────────────────────
# SECTION 5: QUICK TEST
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Testing utils.py with sample_candidates.json")
    print("=" * 55)

    candidates = load_sample_candidates("data/sample_candidates.json")

    if candidates:
        print("\n--- Honeypot Detection ---")
        clean, honeypots = filter_honeypots(candidates)

        print("\n--- Hard Filters ---")
        passed, filtered_out = apply_hard_filters(clean)

        if passed:
            c = passed[0]
            print(f"\nFirst clean candidate:")
            print(f"  Summary   : {get_candidate_summary(c)}")
            print(f"  Skills    : {get_skills_list(c)[:5]}")
            print(f"  Days idle : {get_days_since_active(c)}")
            print(f"  Education : {get_top_education(c).get('degree', 'N/A')}")

    print("\nutils.py test complete!")