# ============================================================
# ranker.py — Core Candidate Ranking Engine
# INDIA RUNS Hiring Challenge | Hack2skill x Redrob
# Author: Er. Priya More
# ============================================================
# Scoring breakdown:
#   A) Skill Match Score     — 35%
#   B) Career Fit Score      — 35%
#   C) Behavioral Score      — 20%
#   D) Education Score       — 10%
# ============================================================

from utils import (
    get_skills_list, get_skill_proficiency, get_skill_duration,
    get_assessment_score, get_top_education, get_days_since_active,
    load_sample_candidates, filter_honeypots, apply_hard_filters
)

# ─────────────────────────────────────────────────────
# SECTION 1: JD REQUIREMENTS
# ─────────────────────────────────────────────────────

# Must-have skills from JD
CORE_SKILLS = [
    "embeddings", "sentence-transformers", "vector database",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus",
    "elasticsearch", "opensearch", "retrieval", "python",
    "ranking", "ndcg", "semantic search", "hybrid search",
    "information retrieval", "nlp", "transformers",
    "fine-tuning llms", "rag", "llm", "reranking"
]

# Good-to-have skills (bonus points)
BONUS_SKILLS = [
    "lora", "qlora", "peft", "xgboost", "learning to rank",
    "distributed systems", "spark", "kafka", "open source",
    "recommendation system", "a/b testing"
]

# Red flag titles — JD explicitly says these are NOT a fit
RED_FLAG_TITLES = [
    "marketing", "sales", "accountant", "graphic designer",
    "content writer", "civil engineer", "mechanical engineer",
    "customer support", "hr manager", "operations manager",
    "project manager"
]

# Pure consulting firms (JD says these are a bad fit)
CONSULTING_FIRMS = [
    "tcs", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "tech mahindra"
]

# Proficiency level → numeric value
PROFICIENCY_MAP = {
    "expert":       1.0,
    "advanced":     0.75,
    "intermediate": 0.5,
    "beginner":     0.25,
    "none":         0.0
}


# ─────────────────────────────────────────────────────
# SECTION 2: SKILL MATCH SCORE (35%)
# ─────────────────────────────────────────────────────

def compute_skill_score(candidate: dict) -> float:
    """
    Score how well the candidate's skills match the JD requirements.

    Considers:
    - How many core skills they have
    - Proficiency level (expert > advanced > intermediate > beginner)
    - Duration of skill usage (more months = more experience)
    - Redrob platform assessment scores
    - Bonus skills

    Returns: float between 0 and 100
    """
    score       = 0.0
    skills_list = get_skills_list(candidate)

    # Core skills matching
    for required_skill in CORE_SKILLS:
        matched = any(
            required_skill in s or s in required_skill
            for s in skills_list
        )

        if matched:
            # Get proficiency
            proficiency = "none"
            for s in skills_list:
                if required_skill in s or s in required_skill:
                    proficiency = get_skill_proficiency(candidate, s)
                    break
            prof_value = PROFICIENCY_MAP.get(proficiency, 0)

            # Get duration (cap at 48 months)
            duration = 0
            for s in skills_list:
                if required_skill in s or s in required_skill:
                    duration = get_skill_duration(candidate, s)
                    break
            duration_score = min(duration / 48, 1.0)

            # Get assessment score
            assessment = 0
            for s in skills_list:
                if required_skill in s or s in required_skill:
                    assessment = get_assessment_score(candidate, s)
                    break
            assessment_score = assessment / 100

            # Combine: proficiency 50% + duration 30% + assessment 20%
            skill_score = (
                prof_value       * 0.5 +
                duration_score   * 0.3 +
                assessment_score * 0.2
            )
            score += skill_score

    # Normalize core skills score to 0-80
    max_core   = len(CORE_SKILLS)
    core_score = (score / max_core) * 80 if max_core > 0 else 0

    # Bonus skills (max 20 points)
    bonus_hits  = sum(
        1 for b in BONUS_SKILLS
        if any(b in s or s in b for s in skills_list)
    )
    bonus_score = min(bonus_hits / len(BONUS_SKILLS), 1.0) * 20

    return round(min(core_score + bonus_score, 100), 2)


# ─────────────────────────────────────────────────────
# SECTION 3: CAREER FIT SCORE (35%)
# ─────────────────────────────────────────────────────

def compute_career_score(candidate: dict) -> float:
    """
    Score the candidate's career history against JD requirements.

    Considers:
    - Years of experience (5-9 yrs is ideal per JD)
    - Current job title relevance
    - Product company vs consulting experience
    - Career stability
    - Description mentions of relevant systems

    Returns: float between 0 and 100
    """
    score      = 0.0
    profile    = candidate.get("profile", {})
    career     = candidate.get("career_history", [])
    years_exp  = profile.get("years_of_experience", 0)
    curr_title = profile.get("current_title", "").lower()

    # Check red flag title first — immediate low score
    is_red_flag = any(flag in curr_title for flag in RED_FLAG_TITLES)
    if is_red_flag:
        return 5.0

    # Experience score (0-25 points)
    if 5 <= years_exp <= 9:
        score += 25
    elif 4 <= years_exp < 5:
        score += 20
    elif 9 < years_exp <= 12:
        score += 18
    elif 3 <= years_exp < 4:
        score += 12
    elif years_exp > 12:
        score += 10
    else:
        score += 5

    # Current title relevance (0-20 points)
    if any(t in curr_title for t in [
        "ml engineer", "machine learning", "ai engineer",
        "data scientist", "nlp engineer", "research engineer",
        "recommendation"
    ]):
        score += 20
    elif any(t in curr_title for t in [
        "data engineer", "software engineer", "backend",
        "platform engineer", "search engineer"
    ]):
        score += 14
    elif any(t in curr_title for t in [
        "analyst", "developer", "engineer"
    ]):
        score += 8
    else:
        score += 3

    # Career history quality
    product_co_count = 0
    relevant_roles   = 0
    company_count    = len(career)
    switch_penalty   = 0

    for job in career:
        company     = job.get("company", "").lower()
        title       = job.get("title", "").lower()
        duration    = job.get("duration_months", 0)
        description = job.get("description", "").lower()

        is_consulting = any(firm in company for firm in CONSULTING_FIRMS)
        if not is_consulting:
            product_co_count += 1

        if any(t in title for t in [
            "ml", "machine learning", "ai", "data scientist",
            "nlp", "search", "ranking", "retrieval", "recommendation"
        ]):
            relevant_roles += 1

        if duration < 12 and not job.get("is_current", False):
            switch_penalty += 1

        if any(kw in description for kw in [
            "embedding", "vector", "retrieval", "ranking",
            "search", "recommendation", "faiss", "nlp"
        ]):
            score += 2

    # Product company ratio score
    if company_count > 0:
        score += (product_co_count / company_count) * 20

    # Relevant roles bonus (max 15)
    score += min(relevant_roles * 5, 15)

    # Job-hopping penalty
    score -= switch_penalty * 3

    # Location fit (0-10 points)
    location = profile.get("location", "").lower()
    country  = profile.get("country", "").lower()
    willing  = candidate.get("redrob_signals", {}).get(
        "willing_to_relocate", False
    )

    PREFERRED_CITIES = [
        "pune", "noida", "delhi", "hyderabad",
        "mumbai", "bangalore", "bengaluru"
    ]

    if any(city in location for city in PREFERRED_CITIES):
        score += 10
    elif country == "india" and willing:
        score += 7
    elif country == "india":
        score += 4

    return round(min(max(score, 0), 100), 2)


# ─────────────────────────────────────────────────────
# SECTION 4: BEHAVIORAL SCORE (20%)
# ─────────────────────────────────────────────────────

def compute_behavioral_score(candidate: dict) -> float:
    """
    Score based on Redrob platform behavioral signals.

    Returns: float between 0 and 100
    """
    signals = candidate.get("redrob_signals", {})
    score   = 0.0

    # Recency: how recently active (0-25 points)
    days_inactive = get_days_since_active(candidate)
    if days_inactive <= 7:
        score += 25
    elif days_inactive <= 30:
        score += 20
    elif days_inactive <= 60:
        score += 14
    elif days_inactive <= 90:
        score += 8
    else:
        score += 2

    # Recruiter response rate (0-20 points)
    response_rate = signals.get("recruiter_response_rate", 0)
    score += response_rate * 20

    # Open to work flag (0-10 points)
    if signals.get("open_to_work_flag", False):
        score += 10

    # GitHub activity (0-15 points)
    github_score = signals.get("github_activity_score", -1)
    if github_score >= 0:
        score += (github_score / 100) * 15

    # Interview completion rate (0-10 points)
    interview_rate = signals.get("interview_completion_rate", 0)
    score += interview_rate * 10

    # Notice period (0-10 points)
    notice = signals.get("notice_period_days", 90)
    if notice <= 15:
        score += 10
    elif notice <= 30:
        score += 8
    elif notice <= 60:
        score += 5
    elif notice <= 90:
        score += 2

    # Profile completeness (0-5 points)
    completeness = signals.get("profile_completeness_score", 0)
    score += (completeness / 100) * 5

    # Verified profile bonus (0-5 points)
    if signals.get("verified_email", False):
        score += 2
    if signals.get("verified_phone", False):
        score += 2
    if signals.get("linkedin_connected", False):
        score += 1

    return round(min(score, 100), 2)


# ─────────────────────────────────────────────────────
# SECTION 5: EDUCATION SCORE (10%)
# ─────────────────────────────────────────────────────

def compute_education_score(candidate: dict) -> float:
    """
    Score based on highest degree and institution tier.

    Returns: float between 0 and 100
    """
    top_edu = get_top_education(candidate)

    if not top_edu:
        return 30.0

    score  = 0.0
    degree = top_edu.get("degree", "").lower()
    field  = top_edu.get("field_of_study", "").lower()
    tier   = top_edu.get("tier", "unknown")

    # Degree level (0-50 points)
    if any(d in degree for d in ["phd", "doctorate"]):
        score += 50
    elif any(d in degree for d in ["master", "m.tech", "m.e.", "mba", "m.sc"]):
        score += 40
    elif any(d in degree for d in ["bachelor", "b.tech", "b.e.", "b.sc"]):
        score += 30
    else:
        score += 15

    # Institution tier (0-30 points)
    TIER_SCORE = {
        "tier_1": 30,
        "tier_2": 22,
        "tier_3": 15,
        "tier_4": 8,
        "unknown": 10
    }
    score += TIER_SCORE.get(tier, 10)

    # Field of study relevance (0-20 points)
    RELEVANT_FIELDS = [
        "computer science", "artificial intelligence",
        "machine learning", "data science", "information technology",
        "electronics", "mathematics", "statistics"
    ]
    if any(f in field for f in RELEVANT_FIELDS):
        score += 20
    elif "engineering" in field:
        score += 12
    else:
        score += 5

    return round(min(score, 100), 2)


# ─────────────────────────────────────────────────────
# SECTION 6: FINAL RANKING
# ─────────────────────────────────────────────────────

def rank_candidates(candidates: list) -> list:
    """
    Compute final weighted score for every candidate and sort them.

    Final Score =
        skill_score     * 0.35 +
        career_score    * 0.35 +
        behavior_score  * 0.20 +
        education_score * 0.10

    Returns:
        List of candidates sorted by final_score descending.
    """
    if not candidates:
        print("No candidates to rank!")
        return []

    print(f"\nScoring {len(candidates)} candidates...")

    results = []

    for c in candidates:
        profile    = c.get("profile", {})
        curr_title = profile.get("current_title", "").lower()

        # Compute each component score
        skill_score    = compute_skill_score(c)
        career_score   = compute_career_score(c)
        behavior_score = compute_behavioral_score(c)
        edu_score      = compute_education_score(c)

        # Count core skill matches
        skills_list = get_skills_list(c)
        core_hits   = sum(
            1 for req in CORE_SKILLS
            if any(req in s or s in req for s in skills_list)
        )

        # Check red flag title
        is_red_flag = any(flag in curr_title for flag in RED_FLAG_TITLES)

        # Apply penalty rules
        if is_red_flag:
            # Red flag title → push to bottom
            final_score = 5.0
        elif core_hits == 0:
            # Zero core skills → cap score at 15
            final_score = min(
                skill_score    * 0.35 +
                career_score   * 0.35 +
                behavior_score * 0.20 +
                edu_score      * 0.10,
                15.0
            )
        else:
            # Normal weighted score
            final_score = (
                skill_score    * 0.35 +
                career_score   * 0.35 +
                behavior_score * 0.20 +
                edu_score      * 0.10
            )

        # Store all scores in candidate dict
        c["_scores"] = {
            "final":     round(final_score, 4),
            "skill":     skill_score,
            "career":    career_score,
            "behavior":  behavior_score,
            "education": edu_score,
            "core_hits": core_hits
        }

        results.append(c)

    # Sort highest score first
    results.sort(key=lambda x: x["_scores"]["final"], reverse=True)

    if results:
        print(f"Ranking complete!")
        print(f"Top score    : {results[0]['_scores']['final']}")
        print(f"Lowest score : {results[-1]['_scores']['final']}")

    return results


def generate_reasoning(candidate: dict, rank: int) -> str:
    """
    Generate a short reasoning string for the submission CSV.

    Returns: str
    """
    profile  = candidate.get("profile", {})
    signals  = candidate.get("redrob_signals", {})
    title    = profile.get("current_title", "N/A")
    exp      = profile.get("years_of_experience", 0)
    skills   = get_skills_list(candidate)

    core_hits     = sum(
        1 for req in CORE_SKILLS
        if any(req in s or s in req for s in skills)
    )
    response_rate = signals.get("recruiter_response_rate", 0)
    days_idle     = get_days_since_active(candidate)
    notice        = signals.get("notice_period_days", 90)

    return (
        f"{title} with {exp} yrs experience; "
        f"{core_hits} core AI/ML skills matched; "
        f"response rate {response_rate:.0%}; "
        f"active {days_idle}d ago; "
        f"{notice}d notice period."
    )


def build_submission(ranked_candidates: list, top_n: int = 100) -> list:
    """
    Build the final submission list with rank, score, and reasoning.

    Returns: List of dicts ready to write to CSV
    """
    if not ranked_candidates:
        print("ERROR: No ranked candidates to build submission from!")
        return []

    submission = []
    top        = ranked_candidates[:top_n]

    max_score   = top[0]["_scores"]["final"]
    min_score   = top[-1]["_scores"]["final"]
    score_range = max_score - min_score if max_score != min_score else 1

    for rank, candidate in enumerate(top, start=1):
        raw_score  = candidate["_scores"]["final"]
        normalized = 0.20 + ((raw_score - min_score) / score_range) * 0.79

        submission.append({
            "candidate_id": candidate.get("candidate_id", ""),
            "rank":         rank,
            "score":        round(normalized, 4),
            "reasoning":    generate_reasoning(candidate, rank)
        })

    return submission


# ─────────────────────────────────────────────────────
# SECTION 7: QUICK TEST
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Testing ranker.py with sample_candidates.json")
    print("=" * 55)

    # Step 1: Load
    # Step 1: Load full dataset
    from utils import load_candidates
    candidates = load_candidates("data/candidates.jsonl")

    # Step 2: Clean
    clean, _  = filter_honeypots(candidates)
    passed, _ = apply_hard_filters(clean)

    # Step 3: Rank
    ranked = rank_candidates(passed)

    # Step 4: Build submission
    submission = build_submission(ranked, top_n=100)

    # Step 5: Show results
    print(f"\nTop 10 Candidates:")
    print("-" * 80)
    for row in submission:
        print(f"Rank {row['rank']:>3} | Score {row['score']:.4f} | "
              f"{row['candidate_id']} | {row['reasoning'][:60]}...")

    print("\nranker.py test complete!")
    # Step 6: Save submission CSV
    import csv
    import os

    os.makedirs("output", exist_ok=True)
    output_path = "output/submission.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f,
            fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        writer.writerows(submission)

    print(f"\nSubmission saved to: {output_path}")
    print(f"Total candidates ranked: {len(submission)}")