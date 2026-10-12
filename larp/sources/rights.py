"""Per-item rights filter (AC-D06): keep only the publisher's own permitted text.

Images, embedded media and attachment links are removed; paragraphs carrying third-party copyright or
permission notices are removed; an item whose header carries such a notice, or which states it is not covered
by the publisher's reuse terms, is rejected. Every removal is recorded so the audit shows what was excluded and why.
This is a conservative filter, not legal advice; a notice it does not recognise is not proof of permission.
"""

from html import unescape
import re

MEDIA = re.compile(r"<(?:img|figure|video|audio|iframe|object|embed|picture|svg)\b[^>]*?(?:/>|>.*?</(?:figure|video|audio|"
                   r"iframe|object|picture|svg)>|>)", re.I | re.S)
ATTACHMENT = re.compile(r"<a\b[^>]*href=[\"'][^\"']+\.(?:pdf|docx?|xlsx?|pptx?|zip|jpe?g|png|gif)(?:\?[^\"']*)?[\"'][^>]*>"
                        r".*?</a>", re.I | re.S)
NOTICE = re.compile(r"\u00a9|\(c\)\s*\d{4}|(?i:\bcopyright\s+(?:\u00a9\s*)?\d{4})|\b[Cc]opyright\s+[A-Z][\w&.-]+|"
                    r"(?i:\ball\s+rights\s+reserved\b|\breprinted\s+with\s+permission\b|\bused\s+(?:with\s+permission|"
                    r"under\s+licen[cs]e)\b|\blicensed\s+from\b|\bcourtesy\s+of\b|\bphoto(?:graph)?\s*(?:credit)?\s*:)")
NOT_COVERED = re.compile(r"\bnot\s+(?:covered|licensed)\s+(?:by|under)\b|\bmay\s+not\s+be\s+reproduced\b|"
                         r"\bunless\s+otherwise\s+(?:indicated|noted)\b.{0,80}\bthird[\s-]part", re.I | re.S)
PARAGRAPH = re.compile(r"(<p\b[^>]*>.*?</p>|<li\b[^>]*>.*?</li>|<blockquote\b[^>]*>.*?</blockquote>)", re.I | re.S)


def _visible(value: str) -> str:
    # Inline markup can split one word; block markup separates words. Normalize
    # entities and invisible formatting before applying the same rights predicates.
    value = unescape(value)
    value = re.sub(r"</?(?:p|li|div|br|h[1-6]|blockquote)\b[^>]*>", " ", value, flags=re.I)
    return re.sub(r"[\u200b-\u200d\ufeff]", "", re.sub(r"<[^>]+>", "", value))


def filter_item(title: str | None, body: str | None) -> tuple:
    """(permitted body or None, exclusions list, rejection reason or None)."""
    exclusions = []
    if title and NOTICE.search(_visible(title)):
        return None, ["TITLE_THIRD_PARTY_NOTICE"], "THIRD_PARTY_RIGHTS"
    if body is None:
        return None, exclusions, None
    first = PARAGRAPH.search(body)
    head = first.group(0) if first else body[:200]  # the item's header: its first paragraph
    if NOTICE.search(_visible(head)) or NOT_COVERED.search(_visible(body)):
        return None, ["ITEM_LEVEL_RIGHTS_NOTICE"], "THIRD_PARTY_RIGHTS"
    kept = body
    for pattern, label in ((MEDIA, "MEDIA_REMOVED"), (ATTACHMENT, "ATTACHMENT_REMOVED")):
        count = len(pattern.findall(kept))
        if count:
            kept = pattern.sub(" ", kept)
            exclusions.append(f"{label}:{count}")
    removed = 0

    def drop(match):
        nonlocal removed
        if NOTICE.search(_visible(match.group(0))):
            removed += 1
            return " "
        return match.group(0)

    kept = PARAGRAPH.sub(drop, kept)
    if removed:
        exclusions.append(f"THIRD_PARTY_PARAGRAPHS_REMOVED:{removed}")
    if NOTICE.search(_visible(kept)):
        return None, exclusions + ["UNSEPARABLE_THIRD_PARTY_NOTICE"], "THIRD_PARTY_RIGHTS"
    return kept, exclusions, None
