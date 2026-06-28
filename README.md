# 🏆 INDIA RUNS — AI Candidate Ranking System
**Hack2skill × Redrob | Track 1: Data & AI**
Built by **Er. Priya More**

---

## 🎯 Problem Statement
Recruiters go through hundreds of profiles and still miss the right person —
because keyword filters can't see what actually matters.

This system ranks candidates **the way a great recruiter would** — not by
matching keywords, but by actually understanding who fits the role.

---

## 🧠 Approach

### Pipeline Overview
100,000 Candidates (candidates.jsonl)

↓

[Stage 1] Honeypot Detection     → 7,515 fake profiles removed

↓

[Stage 2] Hard Filters (JD-based) → 32,162 unsuitable removed

↓

[Stage 3] 4-Component Scoring    → 60,323 candidates scored

↓

Top 100 → submission.csv

### Scoring Breakdown

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| Skill Match Score | 35% | Core AI/ML skills, proficiency, duration, assessments |
| Career Fit Score | 35% | Title relevance, experience range, product companies |
| Behavioral Score | 20% | Platform activity, response rate, GitHub, notice period |
| Education Score | 10% | Degree level, institution tier, field of study |

---

## 🪤 Honeypot Detection
The dataset contains ~80 impossible/fake profiles planted as traps.
Our system detects them using 6 checks:

1. Career history longer than stated experience by 3+ years
2. Impossible education dates (future graduation, 10+ year degree)
3. Unrealistic experience (40+ years)
4. Freshers with 15+ expert-level skills
5. Invalid platform signal values (response rate > 1)
6. Last active date before signup date

**Result: 7,515 honeypots detected and removed ✅**

---

## 🚫 Hard Filters (JD-Based)
Based on the job description, these candidates are filtered out:

- Inactive for more than 6 months
- Entire career only in pure consulting firms (TCS, Infosys, Wipro etc.)
- Not open to work AND recruiter response rate below 5%
- Red flag titles: Marketing, Civil Engineer, HR Manager, Project Manager etc.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.14 | Core language |
| pandas | Data processing |
| Streamlit | Interactive dashboard |
| Plotly | Charts & visualizations |
| anthropic | Claude API (JD parsing) |
| tqdm | Progress tracking |

---

## 📁 Project Structure

INDIARUNS_PROJECT/

├── data/

│   ├── candidates.jsonl        ← 100,000 candidates (475 MB)

│   ├── sample_candidates.json  ← 50 candidates for testing

│   └── job_description.docx    ← Senior AI Engineer JD

├── output/

│   └── submission.csv          ← Final top 100 ranked candidates

├── app.py                      ← Streamlit dashboard

├── ranker.py                   ← Core scoring & ranking engine

├── utils.py                    ← Helper functions

├── requirements.txt            ← Dependencies

├── validate_submission.py      ← Submission validator

└── README.md                   ← This file

---

## 🚀 How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the ranking pipeline
```bash
python ranker.py
```

### 3. Validate submission
```bash
python validate_submission.py output/submission.csv
```

### 4. Launch dashboard
```bash
streamlit run app.py
```

---

## 📊 Results

| Metric | Value |
|--------|-------|
| Total candidates processed | 1,00,000 |
| Honeypots removed | 7,515 |
| Filtered out (JD rules) | 32,162 |
| Candidates scored | 60,323 |
| Final top candidates | 100 |
| Top candidate score | 0.9900 |
| Submission validated | ✅ PASSED |

### Top 5 Candidates
| Rank | Title | Experience | Core Skills |
|------|-------|-----------|-------------|
| #1 | Staff ML Engineer | 7.0 yrs | 11 matched |
| #2 | Senior ML Engineer | 7.2 yrs | 7 matched |
| #3 | Senior AI Engineer | 7.8 yrs | 9 matched |
| #4 | Senior AI Engineer | 5.9 yrs | 9 matched |
| #5 | ML Engineer | 7.2 yrs | 8 matched |

---

## 💡 Key Design Decisions

**Why rule-based scoring instead of LLM for all candidates?**
- 1,00,000 API calls = expensive & slow
- Rule-based is fast, transparent, and explainable
- LLM used only for JD parsing (1 call) + reasoning (100 calls)

**Why honeypot detection first?**
- Disqualification risk if 10+ honeypots in top 100
- Must be done before scoring, not after

**Why career score equals skill score (both 35%)?**
- A keyword stuffer with wrong title should rank LOW
- Career history proves real-world application of skills

---

## 👩‍💻 Author

**Er. Priya More**
Data Analyst & Software Developer
Skills: Python, SQL, ML, Power BI, Tableau, Streamlit, Flask, Azure

---

*Built for INDIA RUNS Hiring Challenge 2026 | Hack2skill × Redrob*