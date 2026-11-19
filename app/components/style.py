"""Storefront styles in ONE place (doc 02 sections 3 and 4).

Streamlit draws standard widgets; this adds the "modern tech academy" color on top:
a gradient hero, tinted "how it works" steps, colored path steps, an accent stripe
on course cards and the seat meter bar.

How it works: a container created with `key="hero"` gets the CSS class `st-key-hero`.
The CSS below only targets those keyed classes (and our own `sf-` classes), never
Streamlit's private class names, so a Streamlit update can't break it.
Colors are the tokens from doc 02 section 3.2. Text keeps WCAG AA contrast (section 8).
Admin pages use no keyed containers, so they stay plain (design principle 5).
"""

import streamlit as st

_CSS = """
<style>
/* ---------- hero (home page) ---------- */
.st-key-hero {
  background: linear-gradient(135deg, #4F46E5 0%, #6D28D9 60%, #7C3AED 100%);
  border-radius: 1rem;
  padding: 2rem 1.5rem;
}
.st-key-hero h1, .st-key-hero p { color: #FFFFFF; }
/* White buttons on the gradient keep dark indigo text (contrast, doc 02 section 8). */
.st-key-hero button p { color: #312E81; font-weight: 600; }

/* ---------- welcome card (home page, signed in) ---------- */
.st-key-welcome {
  background: linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%);
  border: 1px solid #C7D2FE;
  border-radius: 1rem;
  padding: 1.25rem;
}

/* ---------- "how it works" steps ---------- */
.st-key-how_path, .st-key-how_unlock, .st-key-how_xp {
  border-radius: 0.75rem;
  padding: 1rem;
  height: 100%;
}
.st-key-how_path   { background: #EEF2FF; border-left: 6px solid #4F46E5; }
.st-key-how_unlock { background: #ECFDF5; border-left: 6px solid #10B981; }
.st-key-how_xp     { background: #FFFBEB; border-left: 6px solid #F59E0B; }

/* ---------- learning path map ---------- */
[class*="st-key-pathmap-"] {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-top: 4px solid #4F46E5;
  border-radius: 0.75rem;
  padding: 1rem;
}
[class*="st-key-node-"] { border-radius: 0.75rem; padding: 0.75rem; }
[class*="st-key-node-owned-"]   { background: #ECFDF5; border: 2px solid #10B981; }
[class*="st-key-node-in_cart-"] { background: #EEF2FF; border: 2px solid #4F46E5; }
[class*="st-key-node-locked-"]  { background: #F1F5F9; border: 2px dashed #94A3B8; }

/* ---------- course card: colored stripe by level ---------- */
[class*="st-key-card-"] {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 0.75rem;
  padding: 0.75rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}
[class*="st-key-card-beginner-"]     { border-top: 5px solid #10B981; }
[class*="st-key-card-intermediate-"] { border-top: 5px solid #4F46E5; }
[class*="st-key-card-advanced-"]     { border-top: 5px solid #7C3AED; }

/* ---------- seat meter ---------- */
.sf-seat-track { height: 8px; background: #E2E8F0; border-radius: 999px; overflow: hidden; }
.sf-seat-fill  { height: 100%; border-radius: 999px; background: #10B981; }
.sf-seat-fill.sf-few      { background: #F97316; }
.sf-seat-fill.sf-sold_out { background: #94A3B8; }
.sf-seat-text { font-size: 14px; color: #475569; margin: 0 0 4px 0; }

/* ---------- store header ---------- */
.st-key-site_header {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-bottom: 3px solid #4F46E5;
  border-radius: 0.75rem;
  padding: 0.5rem 1rem;
}

/* Prices and XP read like game stats (doc 02 section 3.3). */
.sf-price { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; }
</style>
"""


def apply_storefront_style() -> None:
    """Add the storefront CSS to the page. Called once per run by the header."""
    st.html(_CSS)
