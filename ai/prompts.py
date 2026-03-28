"""
All prompt templates for ApplyCopilot's AI pipeline.
Keeping prompts centralised makes them easy to tune without
touching business logic files.
"""


EMAIL_CLASSIFICATION_PROMPT = """\
You are an email classifier for a job application tracker.

Classify the following email and respond with ONLY a JSON object — no explanation, no markdown.

Categories:
- cold_email         : User sent a cold email to a professor or HR
- professor_reply    : Reply from a professor or researcher
- application_confirmation : Automated confirmation that an application was received
- rejection          : Rejection email from a company or institution
- oa                 : Online assessment or coding challenge invitation
- interview          : Interview invitation or scheduling
- offer              : Job or internship offer
- opportunity        : Job posting or internship opportunity sent to user
- other              : Not job-related

Email:
{email_snippet}

Respond with exactly this JSON structure:
{{
  "is_job_related": true or false,
  "category": "<one of the categories above>",
  "confidence": <float 0.0 to 1.0>,
  "company": "<company or institution name, or null>",
  "role": "<job title or role, or null>"
}}"""


JOB_EXTRACTION_PROMPT = """\
Extract structured job information from the following email text.
Respond with ONLY a JSON object — no explanation, no markdown.

Email:
{email_snippet}

Respond with exactly this JSON structure:
{{
  "company": "<company name>",
  "role": "<job title>",
  "location": "<location or null>",
  "remote": true or false,
  "type": "<research | industry | fellowship | ra | open_source>",
  "domain": "<AI | ML | SWE | Data Science | Research | Other>",
  "deadline": "<YYYY-MM-DD or null>",
  "url": "<application URL or null>"
}}"""


RESUME_TAILOR_PROMPT = """\
You are an expert resume writer helping a student tailor their resume for a specific job.

Job Description:
{job_description}

Candidate Profile:
- Name: {name}
- Degree: {degree} in {branch} from {university}
- CGPA: {cgpa}
- Skills: {skills}
- Projects: {projects}

Rewrite the following resume section to better match the job description.
Highlight relevant skills and experience. Be concise and ATS-friendly.
Use strong action verbs. Keep bullet points under 15 words each.

Section to rewrite ({section_name}):
{current_content}

Respond with ONLY the rewritten section text — no explanation, no JSON."""


MATCH_SCORE_PROMPT = """\
You are evaluating how well a candidate's profile matches a job description.
Score each dimension from 0 to 100 and provide a brief explanation.
Respond with ONLY a JSON object — no explanation, no markdown.

Job Description:
{job_description}

Candidate Profile:
Skills: {skills}
Projects: {projects}
Degree: {degree} — {branch}
CGPA: {cgpa}

Respond with exactly this JSON structure:
{{
  "overall_score": <0-100>,
  "skill_score": <0-100>,
  "experience_score": <0-100>,
  "keyword_score": <0-100>,
  "project_score": <0-100>,
  "analysis": "<2-3 sentence explanation of the match>"
}}"""


SKILL_INFERENCE_PROMPT = """\
Analyse this project description and infer the technical skills demonstrated.
Respond with ONLY a JSON array — no explanation, no markdown.

Project: {project_name}
Description: {description}
Files found: {file_extensions}
README content: {readme_snippet}

Respond with exactly this JSON structure:
[
  {{
    "name": "<skill name>",
    "category": "<programming | ml | devops | research | tools | other>",
    "level": "<beginner | intermediate | expert>",
    "confidence": <float 0.0 to 1.0>
  }}
]"""
