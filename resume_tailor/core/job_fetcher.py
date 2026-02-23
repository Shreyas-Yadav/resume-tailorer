"""Fetch and parse job postings from URLs or files."""

from typing import Optional
from rich.console import Console

HTTP_FETCH_TIMEOUT = 30  # seconds

from ..ai.llm_client import LLMClient
from ..ai.prompts import job_extraction_prompt
from ..ai.schemas import JobPostingResponse
from ..models.data_models import JobPosting


def fetch_job_page(url: str) -> str:
    """Scrape a job posting URL and return raw text."""
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=HTTP_FETCH_TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script/style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Collapse multiple newlines
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def load_job_from_file(filepath: str) -> str:
    """Load job posting text from a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def parse_job_posting(
    raw_text: str,
    url: str,
    llm: LLMClient,
    console: Optional[Console] = None,
) -> JobPosting:
    """Use LLM to extract structured data from raw job posting text."""
    if console:
        console.print("[dim]Extracting job details with LLM...[/dim]")

    prompt = job_extraction_prompt(raw_text)
    data = llm.generate_structured(prompt, JobPostingResponse, temperature=0.3)

    return JobPosting(
        url=url,
        title=data.title or "Unknown",
        company=data.company or "Unknown",
        responsibilities=data.responsibilities,
        required_qualifications=data.required_qualifications,
        preferred_qualifications=data.preferred_qualifications,
        tech_stack=data.tech_stack,
    )


def fetch_and_parse_job(
    url: Optional[str],
    job_file: Optional[str],
    llm: LLMClient,
    console: Optional[Console] = None,
) -> JobPosting:
    """Full pipeline: fetch or load job posting, then parse with LLM."""
    if job_file:
        if console:
            console.print(f"[dim]Loading job posting from {job_file}...[/dim]")
        raw_text = load_job_from_file(job_file)
        display_url = job_file
    elif url:
        if console:
            console.print(f"[dim]Fetching job posting from {url}...[/dim]")
        raw_text = fetch_job_page(url)
        display_url = url
    else:
        raise ValueError("Either --job-url or --job-file must be provided.")

    return parse_job_posting(raw_text, display_url, llm, console)
