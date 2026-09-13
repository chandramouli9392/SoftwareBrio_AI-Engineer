"""Goal-driven autonomous page discovery.

Intelligently scores and prioritizes internal candidate URLs based on missing
information goals (Leadership, Contact, Target Audience / ICP) instead of blind crawling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

from dave.crawl import extract_links


class InformationGoal(str, Enum):
    """Target category of information to acquire."""

    LEADERSHIP = "leadership"
    CONTACT = "contact"
    TARGET_AUDIENCE = "target_audience"
    GENERAL = "general"


# Keyword weights per information category (higher score = more relevant)
_GOAL_KEYWORDS: dict[InformationGoal, dict[str, float]] = {
    InformationGoal.LEADERSHIP: {
        "leadership": 12.0,
        "team": 11.0,
        "founders": 10.0,
        "founder": 9.0,
        "executives": 9.0,
        "management": 8.0,
        "our-team": 8.0,
        "people": 7.0,
        "about-us": 6.0,
        "about": 5.0,
        "company": 4.0,
    },
    InformationGoal.CONTACT: {
        "contact-us": 12.0,
        "contact": 11.0,
        "get-in-touch": 10.0,
        "sales": 8.0,
        "support": 7.0,
        "help": 5.0,
        "press": 5.0,
        "inquiries": 5.0,
    },
    InformationGoal.TARGET_AUDIENCE: {
        "pricing": 12.0,
        "plans": 10.0,
        "customers": 9.0,
        "case-studies": 8.0,
        "customer-stories": 8.0,
        "solutions": 8.0,
        "use-cases": 8.0,
        "product": 7.0,
        "platform": 6.0,
        "enterprise": 7.0,
        "integrations": 5.0,
        "industries": 6.0,
    },
}

# Paths to penalize as low signal for core company enrichment
_PENALIZED_PATH_SUBSTRINGS = (
    "/blog", "/posts", "/news", "/article", "/press-release",
    "/legal", "/privacy", "/terms", "/cookie", "/security",
    "/login", "/signin", "/signup", "/register", "/auth",
    "/cart", "/checkout", "/download", "/docs/api", "/changelog",
    "/status", "/tags", "/categories", "/author",
)


@dataclass(slots=True)
class CandidatePage:
    """A prioritized internal page candidate."""

    url: str
    goal: InformationGoal
    score: float
    reason: str
    matched_keywords: list[str] = field(default_factory=list)


def score_candidate_url(
    url: str,
    *,
    needed_goals: set[InformationGoal] | None = None,
) -> CandidatePage:
    """Score a candidate URL based on its path segments and targeted information goals."""
    parsed = urlparse(url)
    path_lower = parsed.path.lower().rstrip("/")
    query_lower = parsed.query.lower()
    full_target = f"{path_lower}?{query_lower}" if query_lower else path_lower

    best_goal = InformationGoal.GENERAL
    best_score = 0.5
    matched_words: list[str] = []
    primary_reason = "General internal page"

    # Evaluate each goal
    for goal, keywords in _GOAL_KEYWORDS.items():
        goal_score = 0.0
        words_found: list[str] = []
        for kw, weight in keywords.items():
            # Match boundary or dash or slash
            if f"/{kw}" in full_target or f"-{kw}" in full_target or f"_{kw}" in full_target or full_target.endswith(kw):
                goal_score += weight
                words_found.append(kw)

        # Boost score if this goal is explicitly missing / needed
        if needed_goals and goal in needed_goals:
            goal_score *= 1.8

        if goal_score > best_score:
            best_score = goal_score
            best_goal = goal
            matched_words = words_found
            priority_flag = " (needed goal)" if (needed_goals and goal in needed_goals) else ""
            primary_reason = f"Targets {goal.value}{priority_flag} via keywords: {', '.join(words_found)}"

    # Apply penalty for noise / blog / legal pages
    for penalty in _PENALIZED_PATH_SUBSTRINGS:
        if penalty in path_lower:
            best_score = max(0.1, best_score - 8.0)
            primary_reason += f" (penalized for {penalty})"
            break

    # Slight penalty for deeply nested paths (> 3 segments)
    segments = [s for s in path_lower.split("/") if s]
    if len(segments) > 3:
        best_score = max(0.1, best_score - (len(segments) - 3) * 1.5)

    return CandidatePage(
        url=url,
        goal=best_goal,
        score=round(best_score, 2),
        reason=primary_reason,
        matched_keywords=matched_words,
    )


def discover_relevant_pages(
    homepage_html: str,
    base_url: str,
    *,
    needed_goals: set[InformationGoal] | None = None,
    already_visited: set[str] | None = None,
    max_pages: int = 5,
    min_score: float = 3.0,
) -> list[CandidatePage]:
    """Extract and prioritize relevant internal links from page HTML according to information needs.

    Args:
        homepage_html: Raw or processed HTML of the root/referring page.
        base_url: Canonical base URL for relative link resolution and domain check.
        needed_goals: Specific goals that are currently missing (e.g. LEADERSHIP, CONTACT).
        already_visited: URLs to skip.
        max_pages: Maximum candidate pages to return.
        min_score: Minimum relevance score required to be selected.

    Returns:
        List of candidate pages sorted by score descending.
    """
    visited_clean = {u.rstrip("/").lower() for u in (already_visited or set())}
    # Reuse DAVE's battle-tested link extraction
    links = extract_links(homepage_html, base_url, same_domain=True)

    candidates: list[CandidatePage] = []
    seen_urls: set[str] = set()

    for link in links:
        clean_link = link.rstrip("/")
        if clean_link.lower() in visited_clean or clean_link.lower() in seen_urls:
            continue
        seen_urls.add(clean_link.lower())

        candidate = score_candidate_url(link, needed_goals=needed_goals)
        if candidate.score >= min_score:
            candidates.append(candidate)

    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)

    # Ensure diversity across goals if multiple exist
    selected: list[CandidatePage] = []
    goal_counts: dict[InformationGoal, int] = dict.fromkeys(InformationGoal, 0)

    # First pass: pick top scored page for each needed goal
    for c in candidates:
        if needed_goals and c.goal in needed_goals and goal_counts[c.goal] == 0:
            selected.append(c)
            goal_counts[c.goal] += 1
            if len(selected) >= max_pages:
                return selected

    # Second pass: fill up to max_pages with remaining top candidates
    for c in candidates:
        if c not in selected:
            selected.append(c)
            goal_counts[c.goal] += 1
            if len(selected) >= max_pages:
                break

    return selected
