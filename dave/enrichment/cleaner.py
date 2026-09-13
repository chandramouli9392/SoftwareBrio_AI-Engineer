"""Robust HTML to clean Markdown/text pipeline for LLM extraction.

Strips raw HTML tags, styles, scripts, SVGs, cookie banners, navigation menus,
and boilerplate while preserving structural headings, lists, tables, and high-signal
business/contact/leadership content.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

# Elements that should be completely removed with all contents
_UNWANTED_TAGS = {
    "script", "style", "noscript", "svg", "path", "symbol", "canvas",
    "iframe", "link", "meta", "video", "audio", "form", "button", "input",
    "select", "textarea", "template", "picture", "source", "embed", "object"
}

# Regex for classes/ids indicating noise, modals, cookie notices, and ads
_NOISE_SELECTOR_PATTERN = re.compile(
    r"(cookie|consent|gdpr|banner-ad|advert|popup|modal|overlay|dialog|"
    r"newsletter-signup|subscribe-form|promo-bar|notification-bar|"
    r"skip-link|skip-to-content|breadcrumbs)",
    re.IGNORECASE,
)

# Regex to detect email addresses
_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Regex to detect LinkedIn URLs
_LINKEDIN_REGEX = re.compile(r"https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_-]+/?", re.IGNORECASE)


class ContentCleaner:
    """Cleans raw HTML into high-density Markdown text suitable for LLMs."""

    def clean(self, raw_html: str, *, preserve_links: bool = True) -> str:
        """Transform raw HTML or text into clean Markdown-formatted text."""
        if not raw_html or not raw_html.strip():
            return ""

        # If it doesn't contain HTML tags, treat as plain text
        if "<" not in raw_html and ">" not in raw_html:
            return self._normalize_whitespace(raw_html)

        soup = BeautifulSoup(raw_html, "html.parser")

        # 1. Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 2. Extract and preserve any mailto or linkedin links before structural removal
        discovered_contacts = self._extract_special_elements(soup)

        # 3. Strip unwanted tags completely
        for tag_name in _UNWANTED_TAGS:
            for el in soup.find_all(tag_name):
                el.decompose()

        # 4. Remove obvious noise elements (cookie notices, popups, ads)
        for el in soup.find_all(True):
            if not el.parent:  # already removed
                continue
            attrs = " ".join([
                str(el.get("class", "")),
                str(el.get("id", "")),
                str(el.get("role", "")),
                str(el.get("aria-label", "")),
            ])
            if _NOISE_SELECTOR_PATTERN.search(attrs):
                # Don't delete if it contains explicit email or linkedin link
                if not (_EMAIL_REGEX.search(el.get_text()) or _LINKEDIN_REGEX.search(str(el))):
                    el.decompose()

        # 5. Remove top-level header/nav unless containing contact/about links
        for el in soup.find_all(["nav", "header"]):
            text = el.get_text()
            if not (_EMAIL_REGEX.search(text) or "contact" in text.lower() or "about" in text.lower()):
                el.decompose()

        # 6. Convert body/main elements to Markdown
        body = soup.body or soup
        markdown_text = self._node_to_markdown(body, preserve_links=preserve_links)

        # 7. Append preserved special contact/social elements if not already present
        if discovered_contacts:
            contact_block = "\n".join(discovered_contacts)
            markdown_text = f"{markdown_text}\n\n## Discovered Contacts & Links\n{contact_block}"

        return self._normalize_whitespace(markdown_text)

    def _extract_special_elements(self, soup: BeautifulSoup) -> list[str]:
        """Find mailto links and LinkedIn URLs across the document before DOM pruning."""
        special: list[str] = []
        seen: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            text = a.get_text(strip=True)

            if href.lower().startswith("mailto:"):
                email = href[7:].split("?")[0].strip()
                if email and email not in seen:
                    seen.add(email)
                    label = f" ({text})" if text and text != email else ""
                    special.append(f"- Email: {email}{label}")

            elif "linkedin.com" in href.lower():
                match = _LINKEDIN_REGEX.search(href)
                if match:
                    clean_url = match.group(0)
                    if clean_url not in seen:
                        seen.add(clean_url)
                        label = f" ({text})" if text and text != clean_url else ""
                        special.append(f"- LinkedIn: {clean_url}{label}")

        return special

    def _node_to_markdown(self, element: Any, preserve_links: bool = True) -> str:
        """Recursively converts DOM nodes into Markdown equivalents."""
        if isinstance(element, NavigableString):
            return str(element)

        if not isinstance(element, Tag):
            return ""

        tag = element.name.lower()
        inner_content = "".join(self._node_to_markdown(child, preserve_links) for child in element.children)

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            heading_prefix = "#" * level
            clean_inner = " ".join(inner_content.split())
            return f"\n\n{heading_prefix} {clean_inner}\n\n" if clean_inner else ""

        if tag in {"p", "div", "section", "article", "main"}:
            clean_inner = inner_content.strip()
            return f"\n\n{clean_inner}\n\n" if clean_inner else ""

        if tag == "li":
            clean_inner = " ".join(inner_content.split())
            return f"\n- {clean_inner}" if clean_inner else ""

        if tag in {"ul", "ol"}:
            return f"\n\n{inner_content.strip()}\n\n"

        if tag == "blockquote":
            lines = [f"> {line.strip()}" for line in inner_content.splitlines() if line.strip()]
            return f"\n\n{chr(10).join(lines)}\n\n"

        if tag == "table":
            return self._table_to_markdown(element)

        if tag == "a":
            href = str(element.get("href", "")).strip()
            text = " ".join(inner_content.split())
            if not text:
                return ""
            if preserve_links and href and not href.startswith(("#", "javascript:")):
                # Retain useful links (mailto, linkedin, or relative/absolute URLs)
                if href.startswith("mailto:") or "linkedin.com" in href or len(text) > 2:
                    return f" [{text}]({href}) "
            return f" {text} "

        if tag in {"strong", "b"}:
            clean_inner = " ".join(inner_content.split())
            return f" **{clean_inner}** " if clean_inner else ""

        if tag in {"em", "i"}:
            clean_inner = " ".join(inner_content.split())
            return f" *{clean_inner}* " if clean_inner else ""

        if tag == "br":
            return "\n"

        if tag == "hr":
            return "\n\n---\n\n"

        return inner_content

    def _table_to_markdown(self, table: Tag) -> str:
        """Convert HTML tables to Markdown tables."""
        rows: list[list[str]] = []
        for tr in table.find_all("tr"):
            row = [
                " ".join(cell.get_text(strip=True).split())
                for cell in tr.find_all(["th", "td"])
            ]
            if any(row):
                rows.append(row)

        if not rows:
            return ""

        col_count = max(len(r) for r in rows)
        # Pad shorter rows
        for r in rows:
            while len(r) < col_count:
                r.append("")

        md_rows: list[str] = []
        # Header row
        header = rows[0]
        md_rows.append("| " + " | ".join(header) + " |")
        md_rows.append("| " + " | ".join(["---"] * col_count) + " |")

        for r in rows[1:]:
            md_rows.append("| " + " | ".join(r) + " |")

        return "\n\n" + "\n".join(md_rows) + "\n\n"

    def _normalize_whitespace(self, text: str) -> str:
        """Deduplicates newlines, removes excessive spacing, and trims trailing lines."""
        # Replace multiple spaces/tabs with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize linebreaks
        text = re.sub(r"\r\n", "\n", text)
        # Replace 3 or more newlines with 2 newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Split lines and strip trailing/leading spaces from each line
        lines = [line.strip() for line in text.splitlines()]
        # Remove consecutive duplicate lines (common in navigation / breadcrumbs)
        deduped: list[str] = []
        for line in lines:
            if not line:
                if deduped and deduped[-1] != "":
                    deduped.append("")
                continue
            if not deduped or line != deduped[-1]:
                deduped.append(line)

        return "\n".join(deduped).strip()


_CLEANER = ContentCleaner()


def clean_html(raw_html: str, *, preserve_links: bool = True) -> str:
    """Convenience helper to clean HTML to Markdown text."""
    return _CLEANER.clean(raw_html, preserve_links=preserve_links)
