import logging
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# f_TPR: r86400 = ultimas 24h, r604800 = ultimos 7 dias
TIME_FILTER = "r86400"
# f_WT: 1 = presencial, 2 = remoto, 3 = hibrido
REMOTE_WT = "2"

JOB_URN_RE = re.compile(r"jobPosting:(\d+)")
JOB_ID_RE = re.compile(r"/(\d+)(?:\?|&|$)")


@dataclass
class Job:
    job_id: str
    title: str
    company: str
    location: str
    posted: str
    url: str


def _fetch_page(keywords, location, remote, start, time_filter):
    params = {
        "keywords": keywords,
        "f_TPR": time_filter,
        "start": str(start),
    }
    if location:
        params["location"] = location
    if remote:
        params["f_WT"] = REMOTE_WT

    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return resp.text


def _parse(html):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    for card in soup.select("div.base-card"):
        link_el = card.select_one("a.base-card__full-link")
        title_el = card.select_one("h3.base-search-card__title")
        company_el = card.select_one("h4.base-search-card__subtitle")
        location_el = card.select_one("span.job-search-card__location")
        date_el = card.select_one(
            "time.job-search-card__listdate, "
            "time.job-search-card__listdate--new, "
            "span.job-search-card__listdate"
        )

        href = link_el.get("href") if link_el else None
        if not href:
            continue

        job_id = None
        urn = card.get("data-entity-urn") or ""
        urn_match = JOB_URN_RE.search(urn)
        if urn_match:
            job_id = urn_match.group(1)
        else:
            url_match = JOB_ID_RE.search(href)
            if url_match:
                job_id = url_match.group(1)
        if not job_id:
            continue

        title = title_el.get_text(strip=True) if title_el else ""
        company = company_el.get_text(strip=True) if company_el else ""
        location = location_el.get_text(strip=True) if location_el else ""
        posted = date_el.get_text(strip=True) if date_el else ""

        if not title:
            continue

        jobs.append(
            Job(
                job_id=job_id,
                title=title,
                company=company,
                location=location,
                posted=posted,
                url=href,
            )
        )

    return jobs


def search_jobs(
    keywords,
    location=None,
    remote=False,
    time_filter=TIME_FILTER,
    max_results=25,
):
    jobs = []
    start = 0
    while len(jobs) < max_results:
        try:
            page = _fetch_page(keywords, location, remote, start, time_filter)
        except requests.exceptions.RequestException as exc:
            logger.warning(
                "Error obteniendo pagina de %s (start=%s): %s",
                keywords, start, exc,
            )
            break

        parsed = _parse(page)
        if not parsed:
            break

        jobs.extend(parsed)
        start += 25
        if len(parsed) < 25:
            break

    seen = set()
    unique = []
    for job in jobs:
        if job.job_id not in seen:
            seen.add(job.job_id)
            unique.append(job)
        if len(unique) >= max_results:
            break

    return unique


def format_job(job):
    lines = [f"<b>{job.title}</b>"]
    if job.company:
        lines.append(f"Empresa: {job.company}")
    if job.location:
        lines.append(f"Ubicacion: {job.location}")
    if job.posted:
        lines.append(f"Publicado: {job.posted}")
    lines.append(f'<a href="{job.url}">Ver oferta</a>')
    return "\n".join(lines)
