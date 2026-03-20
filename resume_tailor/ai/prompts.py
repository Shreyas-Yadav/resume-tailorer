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


def project_matching_prompt(job_posting_json: str, projects_json: str, existing_resume_projects: str) -> str:
    """Prompt to rank and select projects for the tailored resume."""
    return f"""You are a resume optimization expert. Given a job posting and a set of candidate projects (both from the existing resume and from a projects registry), select the TOP 3 projects that best align with the job requirements.

Also rewrite the professional summary tailored to this role.

Job Posting:
---
{job_posting_json}
---

Existing Resume Projects:
---
{existing_resume_projects}
---

Projects Registry (name, description, tech, key_features, languages):
---
{projects_json}
---

Return a JSON object with these exact keys:
- "selected_projects": list of exactly 3 objects, each with:
  - "name": project name (string)
  - "source": "existing" or "discovered" (string)
  - "relevance_score": 0.0 to 1.0 (number)
  - "reasoning": why this project is relevant (string)
  - "suggested_angle": how to frame this project for the role (string)
- "professional_summary": a rewritten 2-3 sentence professional summary tailored to this role. Use **bold** for key technologies and skills. Must be compelling and specific to the job. (string)
- "infrastructure_and_tools": a reordered comma-separated list of infrastructure, tools, frameworks, and platforms for the Technical Skills section. Put the most job-relevant ones first. You may add tools from the job posting that the candidate likely knows, but NEVER remove tools already listed. (string, no markdown formatting)

CRITICAL RULES:
- NEVER select two projects that are the same or overlapping. The "Existing Resume Projects" and "Discovered Projects" may contain different versions or subsets of the same project (e.g. a frontend and backend of the same app, or an existing project that was also discovered on disk). If an existing resume project and a discovered project refer to the same underlying work, pick only ONE of them — prefer the existing version since it already has polished content.
- Each selected project must be a genuinely distinct project.

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
- Use **bold** to highlight key technologies, metrics, and achievements
- Include quantifiable results where possible (percentages, counts, scale)
- Each bullet should demonstrate a different technical competency
- Naturally incorporate technologies from the job posting where genuinely applicable
- Keep each bullet to 1-2 lines (under 200 characters)

Example bullet format:
"**Distributed Processing:** Built a **Kafka**-based pipeline processing **10K events/sec** with **exactly-once** semantics and automatic partition rebalancing"
"""
