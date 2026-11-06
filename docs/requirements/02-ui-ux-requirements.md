# 02 - UI / UX Requirements

| | |
|---|---|
| **Audience** | UI/UX designer creating wireframes and visual designs; developers implementing them |
| **Related docs** | [00 Consolidated](00-consolidated-requirements.md) · [01 Features & Stories](01-product-features-user-stories.md) · [03 Non-functional](03-non-functional-requirements.md) |

> Demo / training app. Designs must be implementable in **Streamlit** (see section 10).

---

## 1. Vision

> "Professional, yet gamified. It should create curiosity to buy the course."

### 1.1 What the vision means

| Vision word | What it means for the design | What it does **not** mean |
|---|---|---|
| **Professional** | Clean layout, consistent spacing, clear typography, honest pricing, trustworthy look like a modern learning platform | Corporate and dull, walls of text |
| **Gamified** | Progress (XP, levels), collection (badges), maps (learning-path skill trees), rewards (celebrations) used to show the learner's growth | Arcade visuals, cartoon overload, gambling-like mechanics |
| **Curiosity to buy** | Show what can be unlocked: locked modules, locked badges, unfilled path nodes, "next in your path" | Pressure tactics, fake timers, fake scarcity, guilt |

### 1.2 Core idea: "Unlock your skill map"

The whole experience is built around one metaphor: **every course is a node on a skill map. Buying a course unlocks it.** The learner can always see:

1. **Where they are**: level, XP, owned courses.
2. **What's locked**: the rest of the path, locked modules, locked badges.
3. **What one step gets them**: "+100 XP · unlocks 6 modules · 2 of 4 in Data Analyst Path".

That visible gap between "owned" and "locked" is what drives curiosity.

### 1.3 Target users

| Persona | Description | Needs from the UI |
|---|---|---|
| **Learner (primary)** | Students and early-career professionals, some may be minors in training sessions | Clear guidance on where to start, sense of progress, easy purchase |
| **Career switcher** | Adult moving into data/AI | Learning paths, outcomes, level clarity |
| **Staff** | Manages courses and orders | Fast, plain, efficient admin screens (gamification not needed here) |
| **Owner** | Oversees business, manages staff | Dashboard summary, staff management |

## 2. Design principles

1. **Clarity before delight.** Price, level, duration, and the "Add to cart" button must be obvious on every course card and page. Gamification decorates, it never hides information.
2. **Show the next step.** Every screen answers "what can I unlock next?"
3. **Reward real progress only.** XP, levels, and badges come from real actions. Seat counts come from real data.
4. **Consistent game language.** Use the same words everywhere: *Unlock*, *XP*, *Level*, *Badge*, *Path*. Do not mix with "points", "coins", "rank".
5. **Two modes.** Storefront = gamified. Admin = plain and professional.
6. **Age-appropriate and inclusive.** Friendly tone, no violent or mature imagery, no gambling symbols (no loot boxes, slot machines, dice, chests with random rewards).

## 3. Visual direction

These are starting suggestions. The designer may refine them but should keep the contrast rules in section 8.

### 3.1 Mood

"Modern tech academy": a dark-navy or clean-light base with one energetic accent and small game-like touches (glowing progress bars, badge medallions, node maps).

### 3.2 Color tokens (suggested)

| Token | Use | Suggested value |
|---|---|---|
| `primary` | Buttons, links, active states | Indigo `#4F46E5` |
| `accent-xp` | XP bars, XP labels | Amber `#F59E0B` |
| `success` | Unlocked, owned, order confirmed | Emerald `#10B981` |
| `warning` | Few seats left | Orange `#F97316` |
| `danger` | Errors, sold out | Red `#DC2626` |
| `locked` | Locked nodes, locked badges | Slate `#94A3B8` |
| `bg` / `surface` | Page / cards | `#F8FAFC` / `#FFFFFF` (light theme) |
| `text` / `text-muted` | Body / secondary | `#0F172A` / `#475569` |

Level colors (used on course level tags):

| Level | Color |
|---|---|
| Beginner | Emerald |
| Intermediate | Indigo |
| Advanced | Purple `#7C3AED` |

Design a **light theme first** (Streamlit default), dark theme optional.

### 3.3 Typography

- One sans-serif family (e.g. Inter, or the Streamlit default "Source Sans").
- Scale: H1 32px, H2 24px, H3 20px, body 16px, small 14px. Minimum 14px anywhere.
- Numbers for XP and prices can use a bold/tabular style to feel like game stats.

### 3.4 Iconography and imagery

- Simple line icons (e.g. Material Symbols, which Streamlit supports natively).
- Each category has one icon (AI: brain/sparkle, ML: graph/network, Analytics: chart, Data Engineering: database/pipeline).
- Badges: flat medallion style, one color per badge family, a grey silhouette when locked.
- Course images: abstract tech illustrations or gradients, 16:9. No real people's photos or real brand logos.

## 4. Gamification in the UI

| Element | Where it appears | Design requirement | Story |
|---|---|---|---|
| **XP bar + level chip** | Header (signed in), Profile | Small horizontal bar with current XP / next level XP, level name chip. Guests see "Sign up to start earning XP". | US-601, US-602 |
| **XP reward tag** | Course card, detail, cart, checkout | "+100 XP" pill in amber | US-601 |
| **Seat meter** | Course card, detail | "8 of 30 seats left" bar; orange style when few left; "Sold out" grey state | US-203 |
| **Locked module list** | Course detail | Module 1 visible, others with lock icon and blurred/greyed description | US-202 |
| **Skill tree / path map** | Home, Paths page, detail, profile | Horizontal or vertical chain of nodes. States: owned (filled, check), in cart (outlined, cart icon), locked (grey, lock). Shows "2 of 4 unlocked · +250 XP bonus" | US-604 |
| **Badge shelf** | Profile, order confirmation | Grid of medallions; locked ones show a hint on hover/tap or underneath | US-603 |
| **Celebration** | Order confirmation, level up, new badge | Balloons/confetti + summary card "You earned +200 XP, reached Explorer, unlocked First Unlock". Respects "Reduce motion". | US-605 |
| **Unlock preview** | Cart and checkout | "Placing this order unlocks: 2 courses, 14 modules, +200 XP, 1 badge" | US-402 |

**Not allowed** (US-606): countdown timers, "X people viewing", random rewards, public leaderboards, streak penalties.

## 5. Information architecture

### 5.1 Sitemap

```
Storefront (public)
├── Home
├── Courses (catalog + search + filters)
│   └── Course detail
├── Learning Paths
├── Cart
├── Sign in / Register
│
├── (Customer only)
│   ├── Checkout
│   ├── Order confirmation
│   ├── My Orders → Order detail (+ email preview)
│   └── Learner Passport (profile, XP, badges, paths)
│
└── Admin (Staff & Owner only)
    ├── Dashboard
    ├── Courses (list) → Create / Edit course
    ├── Categories & Paths
    ├── Orders → Order detail
    └── Staff management (Owner only)
```

### 5.2 Navigation

- **Header (all storefront pages):** logo/name, main links (Home, Courses, Learning Paths), search box, cart icon with count badge, account area (Sign in button, or avatar + level chip + XP bar + menu).
- **Account menu:** Learner Passport, My Orders, Admin (staff/owner only), Sign out.
- **Admin:** sidebar navigation with the admin sections and a "Back to store" link.
- A persistent "Demo store, no real payments" ribbon or footer note.

## 6. Key user flows

Designers should produce flow diagrams for these:

1. **Discover → Buy (guest):** Home → Course detail → Add to cart → Cart → Checkout → Sign in/Register → Checkout → Place order → Confirmation (+ celebration).
2. **Search:** Header search → Results with filters → Course detail.
3. **Path explorer:** Learning Paths → pick a path → node map → course detail → Add to cart.
4. **Returning customer:** Sign in → Passport shows progress → "Next in your path" → Buy.
5. **Staff adds a course:** Admin → Courses → New course → Save as draft → Preview → Publish.
6. **Owner promotes staff:** Admin → Staff management → find user → change role → confirm.
7. **Stock conflict:** Checkout → Place order → error "only 1 seat left for X" → back to cart with item highlighted.

## 7. Screen requirements

For each screen the designer should provide wireframes for **desktop (1280px)** and **mobile (390px)**, plus the listed states.

### S1 Home
- **Goal:** spark curiosity and guide to a starting point.
- **Content:** hero with headline (e.g. "Unlock your AI & Data skills"), short value line, CTA "Explore courses" and "Find your path"; learning path cards with mini node maps; featured courses row; "Almost full" row (real data); how-it-works strip (Pick a path → Unlock courses → Earn XP & badges); demo notice in footer.
- **Signed-in variant:** hero replaced by a welcome card: "Welcome back, [name] · Level 2 Explorer · 120 XP to Practitioner" + "Next in your path" card.

### S2 Course catalog / search results
- **Content:** search box, filter panel (sidebar on desktop, collapsible on mobile), active filter chips, sort dropdown, results count, course card grid (3-4 per row desktop, 1 per row mobile), pagination.
- **States:** loading (skeleton cards), results, no results (US-105), error.

### S3 Course card (component)
- Image, category icon + name, title (max 2 lines), level tag, duration, price, "+XP" pill, seat meter, "Add to cart" button. Owned courses show an "Unlocked" ribbon instead of Add to cart. Sold out shows a disabled button.

### S4 Course detail
- **Above the fold:** title, level, category, duration, instructor, price, "+100 XP", seat meter, primary "Add to cart", path position ("Course 2 of 4 in Data Analyst Path").
- **Below:** summary, "What you'll learn" checklist, prerequisites, syllabus with locked modules, path map, related courses.
- **States:** available, few seats, sold out, in cart ("In cart · View cart"), owned (all modules unlocked, "Unlocked" state), not found.

### S5 Learning Paths
- List of paths, each with description, node map, courses count, total price, completion bonus XP and badge preview.

### S6 Cart
- Line items (image, title, price, quantity stepper 1-5, line total, remove), subtotal/total, "Unlock preview" summary, "Checkout" button.
- **States:** empty, has items, item unavailable (flagged row with message), guest (Checkout button leads to sign-in).

### S7 Checkout
- Order review (read-only list), email the confirmation goes to, demo notice, required "I understand this is a demo order" checkbox, "Place order" button with loading state.
- **States:** ready, submitting, stock conflict error, general error.

### S8 Order confirmation
- Success header with check icon, order number, items, total, "Confirmation email saved" note, celebration summary card (XP, level, badges), "Next in your path" recommendations, buttons "View my orders" and "Keep exploring".

### S9 Sign in / Register
- Tabs or two linked pages. Fields per US-501/502, password rules visible under the field, show/hide password toggle, error messages inline.
- Register side shows the reward: "Join and earn your first badge + 50 XP".

### S10 Learner Passport (profile)
- Identity card (avatar, name, level, XP bar), editable details, interests picker, badge shelf, path progress list, owned courses, settings (Reduce motion).

### S11 My Orders / Order detail
- Order table/list and detail view with an embedded preview of the saved confirmation email.

### S12 Admin dashboard
- KPI cards (orders, revenue, seats sold, customers), orders-per-day chart, top courses, low-seat list. Plain styling, no gamification.

### S13 Admin course list & course form
- Data table with search/filter, "New course" button, row actions (Edit, Publish/Unpublish, Adjust seats).
- Form grouped into sections: Basics, Pricing & seats, Content (outcomes, prerequisites, modules), Organization (category, tags, paths), Media, Visibility. Validation messages next to fields. "Save draft" and "Publish" actions. Preview link.

### S14 Admin orders
- Filterable table, order detail panel, cancel order action with confirmation (if US-408 is in scope).

### S15 Staff management (Owner)
- User table (name, email, role, joined), role dropdown with confirm dialog, guard message when trying to remove the last owner.

### S16 System states (all screens)
- Access denied, not found, generic error ("Something went wrong, please try again"), loading spinners/skeletons, toasts for success.

## 8. Accessibility & responsiveness

- Meet **WCAG 2.1 AA** contrast (4.5:1 text, 3:1 large text and UI elements). Check amber XP text on white especially; use dark text on amber pills.
- Never use color alone for state: locked/owned/in cart also need an icon and a label.
- All interactive elements reachable by keyboard; visible focus state.
- Images have alt text; badges have text names.
- "Reduce motion" setting disables celebrations and animations.
- Responsive breakpoints: mobile 390px, tablet 768px, desktop 1280px. Streamlit columns stack on narrow screens; designs should expect that.
- Touch targets at least 44 x 44px on mobile.

## 9. Content and tone

- Voice: encouraging, clear, short. Example: "Nice! You unlocked SQL for Analysts." rather than "CONGRATULATIONS!!!".
- Buttons are verbs: "Add to cart", "Place order", "Explore path".
- Errors say what happened and what to do: "Only 1 seat left for SQL for Analysts. Update the quantity to continue."
- Every page that involves buying shows the demo notice.
- All sample copy and imagery must be suitable for younger learners.

## 10. Streamlit constraints for the designer

Streamlit is not a pixel-perfect web framework. Designs must work within these limits:

| Constraint | Impact on design |
|---|---|
| Layout is built from rows, `columns`, `containers`, `tabs`, `expanders`, `sidebar`, `dialog` | Use grid/column layouts; avoid overlapping elements and complex absolute positioning |
| Theme is set in `.streamlit/config.toml` (primary color, background, text, font) plus limited custom CSS | Keep the design system small: one primary color, a few accent colors, consistent cards |
| Hover effects and custom animations are limited | Don't rely on hover to reveal key info (also bad on mobile); celebrations use built-in effects |
| Every interaction reruns the script | Prefer explicit buttons over live-as-you-type interactions |
| Native widgets (buttons, inputs, selects) have fixed shapes | Design around standard widgets; custom-styled cards/pills can be rendered with HTML/CSS |
| Built-in icons: Material Symbols and emoji | Choose icons from Material Symbols |
| Data tables use `st.dataframe` / `st.data_editor` | Admin tables should be simple tabular layouts |
| Skill tree / node map | Must be achievable with columns + styled HTML, or a simple chart; keep it linear (chain) rather than a complex graph |

## 11. Designer deliverables

1. Style guide: color tokens, typography, spacing, icon set, level colors, badge set (6 badges, earned + locked states).
2. Component sheet: header, course card (all states), seat meter, XP bar, level chip, XP pill, path node map, badge medallion, toasts, empty states, admin table, form sections.
3. Wireframes for screens S1-S16 at desktop and mobile widths, including the states listed.
4. Flow diagrams for the flows in section 6.
5. Clickable prototype of flow 1 (Discover → Buy) for training demos (optional).
