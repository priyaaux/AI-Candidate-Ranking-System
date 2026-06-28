# ============================================================
# app.py — Streamlit Dashboard
# INDIA RUNS Hiring Challenge | Hack2skill x Redrob
# Author: Er. Priya More
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os

# ─────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="INDIA RUNS | Candidate Ranking",
    page_icon="🏆",
    layout="wide"
)

# ─────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────

@st.cache_data
def load_submission(filepath: str) -> pd.DataFrame:
    """Load the ranked submission CSV."""
    if not os.path.exists(filepath):
        return pd.DataFrame()
    return pd.read_csv(filepath)


@st.cache_data
def load_sample_candidates(filepath: str) -> dict:
    """Load sample candidates for detail view."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    return {c["candidate_id"]: c for c in candidates}


@st.cache_data
def load_full_candidates_top100(
    submission_df: pd.DataFrame,
    jsonl_path: str
) -> dict:
    """
    Load only the top 100 candidate records from the full JSONL file.
    Stops reading once all 100 are found.
    """
    top_ids = set(submission_df["candidate_id"].tolist())
    found   = {}

    if not os.path.exists(jsonl_path):
        return found

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if len(found) >= len(top_ids):
                break
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                if c["candidate_id"] in top_ids:
                    found[c["candidate_id"]] = c
            except Exception:
                continue

    return found


# ─────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────

def get_candidate_detail(cid: str, candidates: dict) -> dict:
    """Return candidate dict or empty dict."""
    return candidates.get(cid, {})


def proficiency_badge(level: str) -> str:
    """Return colored emoji badge for proficiency level."""
    badges = {
        "expert":       "🔴 Expert",
        "advanced":     "🟠 Advanced",
        "intermediate": "🟡 Intermediate",
        "beginner":     "🟢 Beginner"
    }
    return badges.get(level, "⚪ Unknown")


# ─────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────

def main():

    # Header
    st.title("🏆 INDIA RUNS — AI Candidate Ranking System")
    st.markdown(
        "**Hack2skill × Redrob** | Track 1: Data & AI | "
        "Built by **Er. Priya More**"
    )
    st.divider()

    # Load submission CSV
    submission_df = load_submission("submission.csv")

    if submission_df.empty:
        st.error("submission.csv not found! Please run ranker.py first.")
        return

    # Load candidate details
    JSONL_PATH   = "data/candidates.jsonl"
    SAMPLE_PATH  = "data/sample_candidates.json"

    # Try full JSONL first, fallback to sample
    with st.spinner("Loading candidate details..."):
        if os.path.exists(JSONL_PATH):
            candidates = load_full_candidates_top100(
                submission_df, JSONL_PATH
            )
        else:
            candidates = load_sample_candidates(SAMPLE_PATH)

    # ── METRICS ROW ──────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Ranked", len(submission_df))
    with col2:
        st.metric("Top Score", f"{submission_df['score'].max():.4f}")
    with col3:
        st.metric("Avg Score", f"{submission_df['score'].mean():.4f}")
    with col4:
        st.metric("Min Score", f"{submission_df['score'].min():.4f}")

    st.divider()

    # ── TABS ─────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "📋 Top 100 Candidates",
        "📊 Analytics",
        "👤 Candidate Detail"
    ])

    # ════════════════════════════════════════════════
    # TAB 1: TOP 100 TABLE
    # ════════════════════════════════════════════════
    with tab1:
        st.subheader("Top 100 Ranked Candidates")

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            min_score = st.slider(
                "Minimum Score", 0.0, 1.0,
                float(submission_df["score"].min()),
                0.01
            )
        with col2:
            search = st.text_input(
                "Search by Candidate ID or Reasoning",
                placeholder="e.g. ML Engineer or CAND_00077337"
            )

        # Apply filters
        filtered = submission_df[submission_df["score"] >= min_score]

        if search:
            filtered = filtered[
                filtered["candidate_id"].str.contains(
                    search, case=False, na=False
                ) |
                filtered["reasoning"].str.contains(
                    search, case=False, na=False
                )
            ]

        st.info(f"Showing {len(filtered)} candidates")

        # Display table
        st.dataframe(
            filtered[["rank", "candidate_id", "score", "reasoning"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "rank":         st.column_config.NumberColumn("Rank", width="small"),
                "candidate_id": st.column_config.TextColumn("Candidate ID"),
                "score":        st.column_config.NumberColumn("Score", format="%.4f"),
                "reasoning":    st.column_config.TextColumn("Reasoning", width="large"),
            }
        )

        # Download button
        csv_data = filtered.to_csv(index=False)
        st.download_button(
            label="⬇️ Download Filtered Results",
            data=csv_data,
            file_name="filtered_candidates.csv",
            mime="text/csv"
        )

    # ════════════════════════════════════════════════
    # TAB 2: ANALYTICS
    # ════════════════════════════════════════════════
    with tab2:
        st.subheader("Ranking Analytics")

        col1, col2 = st.columns(2)

        # Score Distribution
        with col1:
            fig1 = px.histogram(
                submission_df,
                x="score",
                nbins=20,
                title="Score Distribution",
                color_discrete_sequence=["#667eea"]
            )
            fig1.update_layout(
                xaxis_title="Score",
                yaxis_title="Count",
                showlegend=False
            )
            st.plotly_chart(fig1, use_container_width=True)

        # Score by Rank
        with col2:
            fig2 = px.line(
                submission_df,
                x="rank",
                y="score",
                title="Score vs Rank",
                color_discrete_sequence=["#f093fb"]
            )
            fig2.update_layout(
                xaxis_title="Rank",
                yaxis_title="Score"
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Extract job titles from reasoning
        if candidates:
            titles      = []
            experiences = []
            core_skills = []

            for cid, c in candidates.items():
                profile = c.get("profile", {})
                title   = profile.get("current_title", "Unknown")
                exp     = profile.get("years_of_experience", 0)

                # Simplify title
                title_lower = title.lower()
                if "ml engineer" in title_lower or "machine learning" in title_lower:
                    simple = "ML Engineer"
                elif "ai engineer" in title_lower or "ai specialist" in title_lower:
                    simple = "AI Engineer"
                elif "data scientist" in title_lower:
                    simple = "Data Scientist"
                elif "nlp" in title_lower:
                    simple = "NLP Engineer"
                elif "recommendation" in title_lower:
                    simple = "Recommendation Engineer"
                elif "software engineer" in title_lower:
                    simple = "Software Engineer"
                elif "backend" in title_lower:
                    simple = "Backend Engineer"
                elif "data engineer" in title_lower:
                    simple = "Data Engineer"
                else:
                    simple = "Other"

                titles.append(simple)
                experiences.append(exp)

            col1, col2 = st.columns(2)

            # Title distribution pie chart
            with col1:
                title_counts = pd.Series(titles).value_counts().reset_index()
                title_counts.columns = ["Title", "Count"]
                fig3 = px.pie(
                    title_counts,
                    values="Count",
                    names="Title",
                    title="Top 100 — Job Title Distribution"
                )
                st.plotly_chart(fig3, use_container_width=True)

            # Experience distribution
            with col2:
                fig4 = px.histogram(
                    x=experiences,
                    nbins=15,
                    title="Top 100 — Experience Distribution",
                    color_discrete_sequence=["#4facfe"]
                )
                fig4.update_layout(
                    xaxis_title="Years of Experience",
                    yaxis_title="Count"
                )
                st.plotly_chart(fig4, use_container_width=True)

        else:
            st.info(
                "Detailed analytics available when "
                "candidate data is loaded."
            )

    # ════════════════════════════════════════════════
    # TAB 3: CANDIDATE DETAIL
    # ════════════════════════════════════════════════
    with tab3:
        st.subheader("Candidate Detail View")

        # Select candidate
        candidate_ids = submission_df["candidate_id"].tolist()
        selected_id   = st.selectbox(
            "Select Candidate",
            candidate_ids,
            format_func=lambda x: (
                f"Rank {submission_df[submission_df['candidate_id']==x]['rank'].values[0]}"
                f" — {x}"
            )
        )

        if selected_id:
            row = submission_df[
                submission_df["candidate_id"] == selected_id
            ].iloc[0]

            # Score card
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rank", f"#{int(row['rank'])}")
            with col2:
                st.metric("Score", f"{row['score']:.4f}")
            with col3:
                st.metric("Candidate ID", selected_id)

            st.info(f"**Reasoning:** {row['reasoning']}")

            # Candidate details
            c = get_candidate_detail(selected_id, candidates)

            if c:
                profile = c.get("profile", {})
                career  = c.get("career_history", [])
                edu     = c.get("education", [])
                skills  = c.get("skills", [])
                signals = c.get("redrob_signals", {})

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 👤 Profile")
                    st.write(f"**Title:** {profile.get('current_title', 'N/A')}")
                    st.write(f"**Experience:** {profile.get('years_of_experience', 0)} years")
                    st.write(f"**Location:** {profile.get('location', 'N/A')}")
                    st.write(f"**Headline:** {profile.get('headline', 'N/A')}")

                    st.markdown("### 📊 Platform Signals")
                    st.write(f"**Response Rate:** {signals.get('recruiter_response_rate', 0):.0%}")
                    st.write(f"**Open to Work:** {'✅ Yes' if signals.get('open_to_work_flag') else '❌ No'}")
                    st.write(f"**Notice Period:** {signals.get('notice_period_days', 'N/A')} days")
                    st.write(f"**GitHub Score:** {signals.get('github_activity_score', 'N/A')}")
                    st.write(f"**Interview Rate:** {signals.get('interview_completion_rate', 0):.0%}")

                with col2:
                    st.markdown("### 🛠️ Skills")
                    for skill in skills[:10]:
                        name  = skill.get("name", "")
                        level = skill.get("proficiency", "")
                        dur   = skill.get("duration_months", 0)
                        st.write(
                            f"**{name}** — "
                            f"{proficiency_badge(level)} "
                            f"({dur} months)"
                        )

                    st.markdown("### 🎓 Education")
                    for e in edu:
                        st.write(
                            f"**{e.get('degree', 'N/A')}** — "
                            f"{e.get('institution', 'N/A')} "
                            f"({e.get('tier', 'N/A')})"
                        )

                st.markdown("### 💼 Career History")
                for job in career:
                    with st.expander(
                        f"{job.get('title', 'N/A')} @ "
                        f"{job.get('company', 'N/A')} "
                        f"({job.get('duration_months', 0)} months)"
                    ):
                        st.write(job.get("description", "No description"))

            else:
                st.warning(
                    "Detailed profile not available for this candidate. "
                    "Only top 50 sample candidates have full details."
                )

    # Footer
    st.divider()
    st.markdown(
        "Built with ❤️ by **Er. Priya More** | "
        "INDIA RUNS Challenge 2026 | Hack2skill × Redrob"
    )


if __name__ == "__main__":
    main()
