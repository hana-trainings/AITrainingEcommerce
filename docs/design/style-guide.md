# SkillForge Academy style guide (D-01)

Short reference for anyone building a page. The color values come from
`docs/requirements/02-ui-ux-requirements.md` section 3 (those win) and are set
once in `.streamlit/config.toml`. `assets/styles/tokens.css` lists the same
values for designers. Pages never write hex colors or CSS: they use the
components below and the named colors of `st.badge`.

## 1. Color tokens

| Token | Value | `st.badge` color | Used for |
|---|---|---|---|
| primary | `#4F46E5` indigo | `blue` / `primary` | Buttons, links, active states, Intermediate level |
| accent-xp | `#F59E0B` amber (text `#78350F`) | `yellow` | XP pills, XP bonus |
| success | `#10B981` emerald (text `#065F46`) | `green` | Unlocked, owned, confirmed, Beginner level |
| warning | `#F97316` orange (text `#9A3412`) | `orange` | Few seats left |
| danger | `#DC2626` red | `red` | Errors |
| locked | `#94A3B8` slate (text `#475569`) | `gray` | Locked nodes and badges, sold out, neutral facts |
| advanced | `#7C3AED` purple | `violet` | Advanced level, level chip, badge preview |
| bg / surface | `#F8FAFC` / `#FFFFFF` | - | Page / cards |
| text / text-muted | `#0F172A` / `#475569` | - | Body / captions |

Contrast: tinted badges use the darker text colors above, so every label meets
WCAG AA (4.5:1). Amber is never used for plain text on white.

## 2. Typography and spacing

- Streamlit's default sans-serif, base 16px. Nothing smaller than 14px (`st.caption`).
- `st.title` (H1) once per page, `st.header` for sections, `st.subheader` inside a section.
- Prices: `#### $49.00` on cards, `## $49.00` on the detail buy box.
- Sentence case everywhere ("Add to cart", not "Add To Cart").
- Spacing comes from containers (`gap="small"` / `"medium"`), never from empty `st.write("")`.

## 3. Icons

Material Symbols only (`:material/name:`). One meaning per icon:

| Meaning | Icon |
|---|---|
| Course / catalog | `school` |
| Learning path | `route` |
| XP | `bolt` |
| Level | `military_tech` |
| Unlocked / owned | `lock_open`, `check_circle` |
| Locked | `lock` |
| In cart | `shopping_cart` |
| Few seats | `event_seat` |
| Sold out | `block` |
| Badge | `workspace_premium` |

Emoji are allowed only where they are data (category icons from the database).

## 4. Components (`app/components`)

| Component | Function | States |
|---|---|---|
| Course card | `course_card(course, owned=, in_cart=, key_prefix=)` | available, few seats, sold out (disabled button), in cart ("In cart · View cart"), owned ("Unlocked") |
| Course image | `course_image(course)` | real image, or a neutral 16:9 gradient per level (no people, no logos) |
| Level tag | `level_tag(level)` | Beginner green, Intermediate indigo, Advanced purple, each with the word |
| Seat meter | `seat_meter(available, total)` | bar + "8 of 30 seats left"; badge "Few seats left" (orange) or "Sold out" (grey) |
| XP pill | `xp_pill(points)` | "+100 XP" amber |
| Level chip + XP bar | `level_chip(level, name)`, `xp_bar(...)` | "Level 2 · Explorer", "120 / 400 XP" |
| Path map | `path_node_map(name, nodes, bonus_xp=)` | chain of steps: Unlocked (check), In cart (cart), Locked (lock); "2 of 4 unlocked · +250 XP bonus" |
| Badge medallion | `badge_medallion(...)` | earned (green) or "Locked" (grey + hint) |
| System states | `states.py` | empty, error, not found, store unavailable, access denied, sign-in prompt, loading skeleton, toast |
| Header | `render_header(user)` | guest: "Sign up to start earning XP", Cart (n), Sign in; signed in: level chip, XP bar, Cart (n), account menu |

Layouts: card walls use `st.grid(3 or 4, min_column_width=240..260)` so they
drop to one card per row on a 390px phone. Toolbars and chips use
`st.container(horizontal=True)`, which wraps.

## 5. Do and don't

Do:
- Show price, level, duration and the main button on every card and detail page.
- Pair every color with a word and an icon (Locked, Unlocked, In cart, Few seats left, Sold out).
- Escape database text with `escape_markdown` before it goes into Markdown, labels or badges.
- Use real numbers only: seats, XP and levels come from the database.
- Give every input a visible label; use `alt=` on images.
- Show the demo notice on buying pages and in the Home footer.

Don't:
- No countdown timers, "X people are viewing", random rewards, leaderboards, streaks or penalties (US-606).
- No "Almost full" label unless the seat meter really says "Few seats left".
- No `unsafe_allow_html` with user or database text; no custom CSS selectors.
- No hover-only information (it does not work on phones).
- No gambling symbols (dice, chests, slot machines) or mature imagery.
