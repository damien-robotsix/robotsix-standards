#!/usr/bin/env python3
"""Shared scaffolding for the docs CI gate scripts.

``check-doc-structure.py`` and ``check-toc-sync.py`` (the CI gates that run
against the ``docs/`` standards corpus) used to each load ``mkdocs.yml`` and
walk the ``nav`` themselves, but with inconsistent recursion depth: the
doc-structure gate recursed arbitrarily deep while the TOC-sync gate handled
only two levels (top-level sections → ``{title: page}`` entries).  If the nav
were ever nested deeper, the two gates would silently disagree about which
pages exist — one would see them, the other would miss them.  This module is
the single source of truth for that walk: the recursive nav-page extractor
lives here once and is imported by both gates, so the depth semantics cannot
drift.

The leading underscore marks this as an internal helper shared by sibling
scripts, not a public API.
"""

from __future__ import annotations


def extract_nav_pages(nav: list[object]) -> list[str]:
    """Return every page filename referenced anywhere in the *nav* (recursive).

    Walks the nav to arbitrary depth: a string entry is itself a page
    filename, a dict entry maps a title to either a page filename or a nested
    list of child entries, and a list entry recurses.  Both nav gates rely on
    this extractor so they see the same set of pages at every nesting depth.
    """
    pages: list[str] = []
    for item in nav:
        if isinstance(item, str):
            pages.append(item)
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    pages.append(value)
                elif isinstance(value, list):
                    pages.extend(extract_nav_pages(value))
    return pages
