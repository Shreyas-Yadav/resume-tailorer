"""Prompt templates for the resume tailor pipeline."""


def job_extraction_prompt(raw_text: str) -> str:
    """Prompt to extract structured job posting data from raw text."""
    return f"""Analyze the following job posting text and extract structured information.

Return a JSON object with these exact keys:
- "title": job title (string)
- "company": company name (string)
- "responsibilities": list of key responsibilities (list of strings)
- "required_qualifications": list of required qualifications (list of strings)
- "preferred_qualifications": list of preferred/nice-to-have qualifications (list of strings)
- "tech_stack": list of specific technologies, languages, frameworks, and tools mentioned (list of strings)

Be thorough in extracting the tech stack — include programming languages, frameworks, cloud services, databases, tools, and methodologies.

Job posting text:
---
{raw_text}
---"""


def project_summary_prompt(project_name: str, readme_content: str, dir_tree: str, dependency_contents: str, source_code: str) -> str:
    """Prompt to summarize a discovered project into a ProjectProfile."""
    return f"""Analyze this software project and provide a structured summary.

Project directory name: {project_name}

Directory structure:
---
{dir_tree}
---

README content:
---
{readme_content}
---

Dependency / build files (actual contents):
---
{dependency_contents}
---

Source code (entry-point files first, then remaining files up to budget):
---
{source_code}
---

Return a JSON object with these exact keys:
- "name": descriptive project name (string)
- "description": 2-3 sentence description of what the project does and its significance (string)
- "tech_stack": list of technologies, frameworks, and tools used (list of strings)
- "key_features": list of 3-5 notable technical features or achievements (list of strings)
- "languages": list of programming languages used (list of strings)"""


def project_enrichment_prompt(project_json: str, deep_context: str, job_posting_json: str) -> str:
    """Prompt to enrich a registry project with evidence grounded in source material."""
    return f"""You are enriching a software project profile for targeted resume tailoring.

Job Posting:
---
{job_posting_json}
---

Registry Project:
---
{project_json}
---

Deep Context:
---
{deep_context}
---

Return a JSON object with these exact keys:
- "name": project name
- "description": 2-3 sentence evidence-grounded description
- "tech": list of technologies clearly supported by the registry/deep context
- "key_features": list of 3-5 supported technical features
- "languages": list of languages clearly supported
- "architecture_signals": list of supported architecture/system design signals
- "outcomes": list of supported outcomes or impact statements; qualitative is fine
- "explicit_metrics": list of explicit quantitative metrics found verbatim or near-verbatim in the source material
- "evidence_summary": compact summary of why this project matters for the job
- "requirement_tags": list of job-relevant requirement themes this project supports

Rules:
- Stay grounded in the provided evidence.
- Do not invent metrics.
- Only include technologies and outcomes supported by the provided material.
- Requirement tags should be short phrases like "backend APIs", "cloud infrastructure", "distributed systems", "data pipelines", "security", "frontend UX", "testing", "databases"."""


def project_matching_prompt(job_posting_json: str, projects_json: str, max_projects: int) -> str:
    """Prompt to rank and select registry projects for the tailored resume."""
    return f"""You are a resume optimization expert. Given a job posting and a set of enriched registry projects, select the smallest high-quality set of projects that covers the role's most important requirements.

Also rewrite the professional summary tailored to this role.
Also propose a tightly targeted skills section.

Job Posting:
---
{job_posting_json}
---

Enriched Projects:
---
{projects_json}
---

Return a JSON object with these exact keys:
- "selected_projects": list of 2 to {max_projects} objects, each with:
  - "name": project name (string)
  - "relevance_score": 0.0 to 1.0 (number)
  - "reasoning": why this project is relevant (string)
  - "suggested_angle": how to frame this project for the role (string)
- "requirement_buckets": list of the 4-8 most important requirement themes for the job, each with:
  - "name": short theme name (string)
  - "evidence": short evidence snippets from the posting (list of strings)
- "professional_summary": a rewritten 2-3 sentence professional summary tailored to this role. Use **bold** for key technologies and skills. Must be compelling and specific to the job. (string)
- "languages": list of the most relevant languages to keep in the resume skills section
- "infrastructure_and_tools": list of the most relevant infrastructure, tools, frameworks, and platforms for this role
- "coursework": list of the most relevant coursework items to keep, if any

CRITICAL RULES:
- You MUST ONLY select projects explicitly listed in "Projects Registry" above. Do NOT invent, fabricate, or suggest any project name that is not present in that list.
- Select 2 to {max_projects} projects, choosing the smallest set that still covers the most important requirement buckets well.
- NEVER select two projects that are the same or overlapping. If multiple registry entries refer to the same underlying work, pick only one.
- Each selected project must be a genuinely distinct project.
- Optimize for requirement coverage across the set, not just per-project strength.

Prioritize projects that:
1. Directly use technologies mentioned in the job posting
2. Demonstrate relevant system design or architecture skills
3. Show measurable impact or scale
4. Are most impressive and differentiated"""


def linkedin_message_prompt(
    job_title: str,
    company: str,
    tech_stack: list,
    top_project_name: str,
    top_project_bullets: list,
    professional_summary: str,
    recruiter_name_or_placeholder: str = "[Recruiter Name]",
    graduation_or_placeholder: str = "May 2026",
    limit: int = 300,
) -> str:
    """Prompt to generate a conversational LinkedIn cold outreach message."""
    tech_str = ", ".join(tech_stack)
    bullets_str = "\n".join(f"- {b}" for b in top_project_bullets)
    return f"""You are writing a cold outreach LinkedIn connection note from a CS student to someone at a company they want to work at.

Context about the sender:
- Graduating: {graduation_or_placeholder}
- Background: {professional_summary}
- Most relevant project: {top_project_name}
- What they built / impact:
{bullets_str}

Context about the recipient:
- Works at: {company}
- Role the sender is applying to: {job_title}
- Tech the team works with: {tech_str}

Your goal:
- Make the message feel personal and genuine, like it was written by a real person who did their research
- Focus on 1 specific project and why it connects to what {company} does — don't list multiple projects or skills
- If you mention tech, weave 1–2 names naturally into a sentence — never enumerate them like a list
- Show real interest in {company} specifically, not just the job opening
- End with a subtle dual ask: a quick chat or intro, and gently leave the door open for a referral (e.g. "if you think it could be a fit, I'd love to be considered or just hear your take")

Avoid:
- Generic openers like "I came across your opening" or "I noticed you're hiring"
- Listing tech or skills like a resume (e.g. "AWS Lambda, SQS, and RDS MySQL" reads like a bullet point)
- Sounding stiff, corporate, or robotic
- Flattery that feels hollow

Tone: warm, direct, conversational — like a smart student who knows what they're doing and respects the reader's time.

Greeting: "Hi {recruiter_name_or_placeholder},"
If the recruiter name is "[Recruiter Name]", keep that placeholder exactly as-is.

CHARACTER LIMIT: {limit} characters total (including spaces). Use as much of this space as you need to sound complete and natural — don't cut off abruptly, but don't pad either.

Plain text only — no markdown, no asterisks, no bullet points, no numbered lists.

Return a JSON object with exactly one key:
{{"message": "the full message text"}}"""


def bullet_generation_prompt(project_name: str, project_description: str, project_tech: str, job_title: str, job_tech: str, suggested_angle: str, key_features=None) -> str:
    """Prompt to generate tailored bullet points for a selected project."""
    features_section = (
        "\n".join(f"- {f}" for f in key_features) if key_features else "(none provided)"
    )
    return f"""Generate resume bullet points for this project, tailored to a {job_title} role.

Project: {project_name}
Description: {project_description}
Technologies used: {project_tech}
Job's key technologies: {job_tech}
Suggested framing angle: {suggested_angle}
Key features / achievements:
{features_section}

Return a JSON object with these exact keys:
- "display_name": concise project name for the resume heading (string)
- "tech_stack_display": comma-separated technologies for the resume heading, ordered by relevance to the job (string)
- "bullet_points": list of exactly 3 strings, each a resume bullet point

Bullet point format rules:
- Start each bullet with a **Bold Heading:** followed by a description
- Each bullet MUST follow compressed STAR structure within 1-2 lines:
  S (Situation): 3-5 words of context or scale — why it mattered or what the challenge was
  T (Task): implied by the action — what needed to be built or solved
  A (Action): what you built/did, with **bold** on key technologies and design choices
  R (Result): a quantified outcome — latency reduction, throughput, accuracy, users, cost, etc.
- Each bullet should highlight a different technical competency (e.g. architecture, optimization, reliability)
- Naturally incorporate technologies from the job posting where genuinely applicable
- Keep each bullet to 1-2 lines (under 220 characters)
- Include quantifiable metrics only when explicitly supported by the provided project description or key features
- If no metric is supported, use a truthful qualitative outcome instead
- Do not introduce technologies or outcomes not grounded in the provided project context

Example STAR-compressed bullet:
"**Real-time Ingestion:** Replaced legacy batch jobs with a **Kafka**-based pipeline using consumer groups and exactly-once semantics, cutting latency by **95%** and scaling to **10K events/sec**"
"""


def experience_tailoring_prompt(job_posting_json: str, experience_json: str) -> str:
    """Prompt to tailor existing experience bullets for the target role."""
    return f"""Rewrite the resume experience bullets to better target the job while staying truthful to the original experience.

Job Posting:
---
{job_posting_json}
---

Existing Experience:
---
{experience_json}
---

Return a JSON object with exactly one key:
- "entries": list of objects, each with:
  - "company": exact company name from the input
  - "role": exact role name from the input
  - "bullet_points": list of 2-3 rewritten bullets

Rules:
- Preserve company and role names exactly.
- Keep bullets grounded in the original bullets; do not invent projects or metrics.
- Reorder emphasis toward the target job's most important requirements.
- Use the same compact resume style with **bold** for the key technical phrases.
- Do not repeat the same competency across every bullet."""


def additional_experience_bullet_prompt(job_posting_json: str, experience_entry_json: str) -> str:
    """Prompt to add one more truthful, relevant experience bullet."""
    return f"""Write one additional resume bullet for this experience entry to improve targeted-job relevance while staying truthful to the source material.

Job Posting:
---
{job_posting_json}
---

Experience Entry:
---
{experience_entry_json}
---

Return a JSON object with exactly one key:
- "bullet_point": one additional bullet

Rules:
- Keep the bullet grounded in the provided source bullets.
- Do not invent metrics, projects, or technologies.
- Add a different competency from the existing tailored bullets.
- Use compact resume style with **bold** emphasis on the key technical phrase."""


def skills_tailoring_prompt(job_posting_json: str, skills_json: str, available_project_skills: str) -> str:
    """Prompt to tailor the technical skills section."""
    return f"""Curate a one-page resume skills section for the target role.

Job Posting:
---
{job_posting_json}
---

Existing Skills:
---
{skills_json}
---

Skills supported by selected projects:
---
{available_project_skills}
---

Return a JSON object with these exact keys:
- "languages": ordered list of languages to keep
- "infrastructure_and_tools": ordered list of infrastructure/tools/frameworks/platforms to keep
- "coursework": ordered list of coursework items to keep

Rules:
- Keep the section compact and ATS-friendly.
- Prioritize job-relevant items and items supported by the resume/projects.
- Remove weak, repetitive, or irrelevant tools.
- Do not add unsupported skills."""


def resume_review_prompt(job_posting_json: str, resume_json: str) -> str:
    """Prompt to review the final tailored resume draft."""
    return f"""Review this tailored resume draft for quality against the target job posting.

Job Posting:
---
{job_posting_json}
---

Tailored Resume Draft:
---
{resume_json}
---

Return a JSON object with these exact keys:
- "passed": boolean
- "underfilled": boolean indicating whether the resume likely leaves too much empty space on a one-page layout
- "missing_requirements": list of important job requirement themes not covered well
- "duplicated_themes": list of themes repeated too much across summary/experience/projects
- "unsupported_claims": list of suspicious claims, metrics, or technologies that may not be grounded
- "trim_suggestions": list of content that should be shortened or removed to improve one-page quality
- "page_fill_recommendations": list of specific suggestions to use empty space with higher-signal content
- "issues": list of objects with:
  - "severity": one of "high", "medium", "low"
  - "message": concise issue description

Rules:
- Focus on relevance, coverage, unsupported claims, and repetition.
- Mark underfilled=true when the draft appears noticeably short for a one-page resume and there is room for more high-signal content.
- Mark passed=true only if the resume is strong for the target role without obvious unsupported claims or major gaps."""
