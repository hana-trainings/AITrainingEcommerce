# 01 - Product Features & User Stories

| | |
|---|---|
| **Project** | AI Training E-commerce (demo / training app) |
| **Product sold** | AI and Data training courses |
| **Stack** | Streamlit (UI) + Supabase (Postgres, Auth, Storage) |
| **Related docs** | [00 Consolidated](00-consolidated-requirements.md) · [02 UI/UX](02-ui-ux-requirements.md) · [03 Non-functional](03-non-functional-requirements.md) |

> This app is for learning and demo purposes only. No real payments are taken and no real emails are sent.

---

## 1. Roles

| Role | Who | Can do |
|---|---|---|
| **Guest** | Anyone not signed in | Browse, search, view course details, add to cart (session only) |
| **Customer** | Registered learner | Everything a Guest can, plus persistent cart, checkout, order history, XP, badges |
| **Staff** | Employee account | Customer abilities, plus manage courses (create, edit, publish, adjust seats) and view all orders |
| **Owner** | Business owner | Staff abilities, plus manage staff accounts (promote/demote roles) and permanently delete courses |

Role is stored on the user's profile (`customer`, `staff`, `owner`). New registrations are always `customer`. Only an Owner can change roles.

## 2. Key domain terms

| Term | Meaning |
|---|---|
| **Course** | The product. Has title, summary, description, category, level, duration, price, image, modules (syllabus), and seat inventory. |
| **Seats** | The inventory of a course. Each seat purchased reduces `seats_available` by 1. |
| **Learning Path** | An ordered group of courses (e.g. "Data Analyst Path"). Drives the skill-tree and path-progress gamification. |
| **XP** | Experience points a customer earns for actions (register, complete profile, purchase). |
| **Level** | Rank derived from total XP. |
| **Badge** | Achievement awarded for milestones (first purchase, finishing a path, etc.). |
| **Outbox** | Folder (and table) where "sent" confirmation emails are written instead of being emailed. |

## 3. Epics overview

| Epic | Feature (from brief) | Priority |
|---|---|---|
| E1 | Product search & catalog | Must |
| E2 | Product detail | Must |
| E3 | Add to cart | Must |
| E4 | Checkout & order confirmation | Must |
| E5 | Customer register / sign in | Must |
| E6 | Gamification (supports the UI vision) | Should |
| E7 | Owner & staff product management | Must |

Priority uses MoSCoW: **Must**, **Should**, **Could**, **Won't (this release)**.

Story format: *As a [role], I want [goal], so that [benefit].* Acceptance criteria (AC) use Given / When / Then where it helps.

---

## E1 - Product Search & Catalog

### US-101 Browse the catalog · Must
As a **guest or customer**, I want to see all available courses as cards, so that I can quickly see what is on offer.

- AC1: Only courses with `is_published = true` are shown.
- AC2: Each card shows image, title, category, level, duration, price, seats-left indicator, and XP reward.
- AC3: Sold-out courses are shown with a "Sold out" state and cannot be added to cart.
- AC4: Catalog shows 12 courses per page with pagination (or "Load more").

### US-102 Keyword search · Must
As a **guest or customer**, I want to search by keyword, so that I can find a course on a topic I care about.

- AC1: Search matches title, summary, description, and tags, case-insensitive.
- AC2: Results update when the user presses Enter or the search button.
- AC3: The search term stays visible in the box and is shown above results ("12 results for 'python'").
- AC4: Leading/trailing spaces are ignored; an empty search shows the full catalog.

### US-103 Filter results · Must
As a **guest or customer**, I want to filter courses, so that I can narrow down to what fits me.

- AC1: Filters available: Category (multi-select), Level (Beginner / Intermediate / Advanced), Price range, Duration range, Learning Path, "Only show available" toggle.
- AC2: Filters combine with keyword search (AND logic).
- AC3: A "Clear filters" action resets all filters.
- AC4: Active filters are visible as removable chips.

### US-104 Sort results · Should
As a **guest or customer**, I want to sort results, so that I can see the most relevant courses first.

- AC1: Sort options: Featured (default), Newest, Price low-high, Price high-low, Fewest seats left.

### US-105 No results state · Must
As a **guest or customer**, when nothing matches, I want helpful guidance, so that I am not stuck.

- AC1: Given no results, show a friendly message, a "Clear filters" button, and 3 suggested/featured courses.

### US-106 Featured & "Trending" sections on home · Should
As a **guest**, I want the home page to highlight featured courses and learning paths, so that I get curious and start exploring.

- AC1: Owner/Staff can mark a course as `is_featured`.
- AC2: Home shows featured courses, learning paths, and a "Almost full" strip (courses with the fewest seats left, based on real data only).

---

## E2 - Product Detail

### US-201 View course details · Must
As a **guest or customer**, I want to open a course page, so that I can decide whether to buy it.

- AC1: Shows title, image, category, level, duration, price, seats left, instructor name, summary, full description, learning outcomes ("What you'll learn"), prerequisites, and syllabus modules.
- AC2: Shows the XP the learner will earn by purchasing.
- AC3: Shows which Learning Path(s) the course belongs to and its position in the path.
- AC4: Unpublished courses return a "Course not found" page for guests and customers (staff can preview).

### US-202 Locked syllabus preview ("sneak peek") · Should
As a **guest or customer**, I want to see the first module in full and the rest as locked teasers, so that I get a taste and want to unlock the rest.

- AC1: Module 1 shows its title and short description.
- AC2: Remaining modules show title only with a lock icon and "Unlock with this course".
- AC3: After purchase, the customer sees all modules unlocked on the detail page.

### US-203 Seat availability indicator · Must
As a **guest or customer**, I want to see how many seats are left, so that I know if I need to act.

- AC1: Shows "X of Y seats left" with a progress bar.
- AC2: When seats left is 10% or less of total (or 5 or fewer), the indicator switches to a "Few seats left" style.
- AC3: Counts must come from the database. No fake scarcity or fake countdown timers.

### US-204 Add to cart from detail · Must
As a **guest or customer**, I want an "Add to cart" button on the detail page, so that I can buy right away. (See E3.)

### US-205 Related courses / next in path · Should
As a **guest or customer**, I want to see related courses and the next course in the path, so that I keep exploring.

- AC1: Shows up to 4 courses from the same path or category, excluding the current one.

---

## E3 - Add to Cart

### US-301 Add a course to the cart · Must
As a **guest or customer**, I want to add a course to my cart, so that I can buy it later in one checkout.

- AC1: Given seats are available, when I click "Add to cart", the item is added with quantity 1 and a confirmation toast appears.
- AC2: Adding a course already in the cart increases the quantity by 1 (up to the limit in US-303).
- AC3: The cart badge in the header updates immediately with the item count.
- AC4: The button is disabled for sold-out courses.

### US-302 View the cart · Must
As a **guest or customer**, I want to view my cart, so that I can review what I'm buying.

- AC1: Lists each item with image, title, unit price, quantity (seats), line total.
- AC2: Shows subtotal, total, and total XP to be earned.
- AC3: Empty cart shows an empty state with a link to the catalog.

### US-303 Change quantity (seats) · Must
As a **customer**, I want to change how many seats I buy (e.g. for a friend or team), so that I can buy more than one.

- AC1: Quantity is between 1 and 5.
- AC2: Quantity can't exceed current `seats_available`; if it would, show a message and cap it.

### US-304 Remove an item · Must
As a **guest or customer**, I want to remove an item, so that my cart contains only what I want.

### US-305 Persistent cart for signed-in customers · Must
As a **customer**, I want my cart saved to my account, so that it is still there when I sign in again.

- AC1: Signed-in carts are stored in the `cart_items` table.
- AC2: Guest carts are stored in the browser session only.

### US-306 Merge guest cart on sign-in · Should
As a **guest who signs in**, I want items I added before signing in to be kept, so that I don't lose them.

- AC1: On sign-in, session cart items are merged into the saved cart (quantities added, capped by US-303 rules).

### US-307 Cart price check · Must
As a **customer**, I want the cart to reflect current prices and availability, so that there are no surprises at checkout.

- AC1: Prices and seats are re-read from the database whenever the cart page loads.
- AC2: If an item became unavailable or unpublished, it is flagged and excluded from checkout until removed.

---

## E4 - Checkout & Order Confirmation

### US-401 Checkout requires sign-in · Must
As a **guest**, when I click "Checkout", I want to be asked to sign in or register, so that the order is linked to my account.

- AC1: After sign-in or registration, the user returns to checkout with the cart intact.

### US-402 Review and place order (no payment) · Must
As a **customer**, I want to review my order and place it without a credit card, so that I can complete a demo purchase.

- AC1: The checkout page shows items, quantities, total, XP to earn, and the email the confirmation will go to.
- AC2: A clear notice says "Demo store: no payment is taken."
- AC3: The customer must tick "I understand this is a demo order" before "Place order" is enabled.
- AC4: The "Place order" button is disabled after one click to prevent double orders.

### US-403 Deduct inventory on order · Must
As the **business**, I want seats to be deducted when an order is placed, so that we never sell more seats than exist.

- AC1: Placing the order, deducting seats, creating order items, and clearing the cart happen in **one database transaction** (Supabase RPC / Postgres function).
- AC2: `seats_available` can never go below 0 (database constraint).
- AC3: If any item doesn't have enough seats, the whole order fails and nothing is deducted.

### US-404 Handle stock conflict · Must
As a **customer**, if a course sells out while I'm checking out, I want a clear message, so that I can adjust my cart.

- AC1: Message names the course(s) and the seats now available.
- AC2: The customer is returned to the cart with the problem items highlighted.

### US-405 Order confirmation page · Must
As a **customer**, after placing an order, I want a confirmation page, so that I know it worked.

- AC1: Shows order number (format `ORD-YYYYMMDD-XXXX`), date, items, total, and the email address used.
- AC2: Shows XP earned, any new level reached, and any badges unlocked, with a celebration animation.
- AC3: Shows "Next in your path" recommendations.

### US-406 Confirmation email written to outbox · Must
As a **customer**, I want an order confirmation email, so that I have a record of my order. (Demo: the email is saved, not sent.)

- AC1: An HTML email file is written to `outbox/` named `order_<order_number>_<yyyymmddHHMMSS>.html`.
- AC2: The email contains: To, Subject ("Your order ORD-... is confirmed"), greeting, order number, date, items with quantity and price, total, XP earned, and a "This is a demo" footer.
- AC3: The same email content is also saved to an `email_outbox` table so it can be viewed on cloud deployments where the file system is temporary. (See NFR-DEP-04.)
- AC4: No email is actually sent. No SMTP or email service is configured.
- AC5: If writing the file fails, the order still succeeds and the error is logged.

### US-407 Order history · Must
As a **customer**, I want to see my past orders, so that I can check what I bought.

- AC1: "My Orders" lists orders newest first with number, date, total, item count, status.
- AC2: Clicking an order shows its details and a "View confirmation email" preview.

### US-408 Order status · Could
As **staff**, I want orders to have a status, so that we can show order lifecycle in the demo.

- AC1: Statuses: `confirmed` (default on placement), `cancelled`.
- AC2: Staff can cancel an order; cancelling returns seats to inventory.

---

## E5 - Customer Register / Sign In

### US-501 Register · Must
As a **guest**, I want to create an account with my name, email, and password, so that I can buy courses.

- AC1: Fields: Display name, Email, Password, Confirm password.
- AC2: Password rules per NFR-SEC-03; inline errors explain what's wrong.
- AC3: Duplicate email shows "An account with this email already exists" (without revealing other info).
- AC4: On success the user is signed in, gets the "First Step" badge and +50 XP, and is returned to where they were.
- AC5: Email confirmation is turned off for the demo (no emails are sent). See doc 03.

### US-502 Sign in · Must
As a **customer, staff, or owner**, I want to sign in with email and password, so that I can access my account.

- AC1: Wrong email or password shows a generic "Email or password is incorrect".
- AC2: After sign-in, the header shows the user's name, level, and XP bar.
- AC3: Staff and Owner see an "Admin" link in navigation.

### US-503 Sign out · Must
As a **signed-in user**, I want to sign out, so that others using this device can't access my account.

- AC1: Sign-out clears session state (tokens, cart in memory, role) and returns to home.

### US-504 My profile ("Learner Passport") · Should
As a **customer**, I want a profile page, so that I can see my progress and edit my details.

- AC1: Shows display name, email, level, XP, badges (earned and locked), learning path progress, and owned courses.
- AC2: Customer can edit display name and pick an avatar from a preset list (no photo uploads).
- AC3: Completing the profile (name + avatar + selecting 1-3 interests) awards +25 XP once.

### US-505 Password reset · Could
As a **customer**, I want to reset a forgotten password, so that I can get back in.

- AC1: For the demo, this is **out of scope** unless the trainer enables Supabase's built-in reset email. The sign-in page shows "Forgot password? Ask your trainer." when disabled.

---

## E6 - Gamification

These stories support the UI vision of "professional but gamified, creating curiosity to buy". See doc 02 for how they look.

### US-601 Earn XP · Should
As a **customer**, I want to earn XP for actions, so that I feel progress and want to keep going.

| Action | XP | Limit |
|---|---|---|
| Register | +50 | once |
| Complete profile (US-504) | +25 | once |
| Purchase a course | +100 per course (not per seat) | once per course |
| Complete a learning path (own all its courses) | +250 bonus | once per path |

- AC1: XP changes are recorded in an `xp_events` table (user, action, points, created_at) and the profile total is updated.
- AC2: XP is only awarded server-side (in the database function), never from client input.

### US-602 Levels · Should
As a **customer**, I want to level up, so that I have a goal to work toward.

| Level | Name | XP needed |
|---|---|---|
| 1 | Novice | 0 |
| 2 | Explorer | 150 |
| 3 | Practitioner | 400 |
| 4 | Expert | 800 |
| 5 | Master | 1500 |

- AC1: The header XP bar shows progress to the next level.
- AC2: Reaching a new level triggers a "Level up!" celebration once.

### US-603 Badges · Should
As a **customer**, I want to collect badges, so that I'm curious about what else I can unlock.

| Badge | Rule |
|---|---|
| First Step | Register |
| Identity Set | Complete profile |
| First Unlock | First purchase |
| Path Starter | Own 1 course in any learning path |
| Path Master: *[Path name]* | Own every course in a path |
| Collector | Own 5 or more courses |

- AC1: Locked badges are visible as silhouettes with a hint ("Buy your first course to unlock").
- AC2: Newly earned badges show a popup/toast the first time.

### US-604 Learning path skill tree · Should
As a **guest or customer**, I want to see each learning path as a map of courses, so that I can see what I've unlocked and what's next.

- AC1: Each path shows its courses in order as nodes: owned (unlocked), in cart, or locked.
- AC2: Shows "X of Y unlocked" and the XP bonus for completing the path.
- AC3: Clicking a node opens the course detail.

### US-605 Celebration feedback · Should
As a **customer**, I want a celebration when I complete an order or earn something, so that the moment feels rewarding.

- AC1: Use Streamlit's built-in effects (`balloons`) or a lightweight animation on order confirmation and level-up.
- AC2: Celebrations can be turned off in profile settings ("Reduce motion").

### US-606 Ethical gamification · Must
As the **business**, I want gamification that is honest and suitable for all ages, so that the app is appropriate for training audiences including minors.

- AC1: No fake timers, fake "X people are viewing", or fake scarcity. All numbers come from real data.
- AC2: No penalties, lost streaks, or guilt messages.
- AC3: No leaderboards that expose other users' names or data.

---

## E7 - Owner & Staff Product Management

### US-701 Admin area access · Must
As **staff or owner**, I want an Admin area, so that I can manage the store.

- AC1: Admin pages are only shown in navigation for Staff and Owner.
- AC2: Direct access by any other user shows "You don't have access" and no data.
- AC3: Database Row Level Security enforces the same rules even if the UI is bypassed (NFR-SEC-05).

### US-702 Course list (admin) · Must
As **staff**, I want a table of all courses, so that I can see everything at a glance.

- AC1: Columns: image thumbnail, title, category, level, price, seats available / total, published, featured, last updated.
- AC2: Search by title and filter by published status and category.
- AC3: Includes unpublished courses.

### US-703 Create course · Must
As **staff**, I want to add a new course, so that it can be sold.

- AC1: Fields: title*, slug (auto from title, editable), summary* (max 200 chars), description*, category*, level*, duration in hours*, price* (0 - 9,999), total seats* (1 - 10,000), instructor name, learning outcomes (list), prerequisites (list), modules (ordered list of title + description), tags, learning path(s) and position, image upload, featured flag, published flag.
- AC2: Required fields (*) are validated before saving with clear messages.
- AC3: Image upload accepts JPG/PNG/WebP up to 2 MB, stored in Supabase Storage.
- AC4: New courses default to unpublished.
- AC5: On save, `seats_available` = total seats.

### US-704 Edit course · Must
As **staff**, I want to edit a course, so that I can keep information correct.

- AC1: All create fields are editable.
- AC2: Changing price does not affect existing orders (orders store the price paid).
- AC3: Shows "Last updated by X at time".

### US-705 Publish / unpublish · Must
As **staff**, I want to publish or unpublish a course, so that I control what customers see.

- AC1: Unpublishing hides the course from the catalog and search, and flags it in carts (US-307).
- AC2: Orders containing the course are not affected.

### US-706 Adjust seats · Must
As **staff**, I want to add or remove seats, so that I can manage capacity.

- AC1: Staff enters an adjustment (+/-) and a reason.
- AC2: `seats_available` can't go below 0, and total seats can't go below seats already sold.
- AC3: Each adjustment is recorded in the audit log.

### US-707 View orders · Must
As **staff**, I want to see all orders, so that I can support customers.

- AC1: Table with order number, customer email, date, total, items, status.
- AC2: Filter by date range and status; search by order number or email.
- AC3: Open an order to see items and the confirmation email preview.

### US-708 Admin dashboard · Should
As **staff or owner**, I want a summary dashboard, so that I can see how the store is doing.

- AC1: Cards: total orders, total revenue (demo), seats sold, number of customers.
- AC2: Charts: orders per day (last 30 days), top 5 courses by seats sold, low-seat courses.

### US-709 Manage staff · Must
As the **owner**, I want to promote customers to staff or demote staff, so that I control who can manage the store.

- AC1: Owner sees a user list with role and can change a user's role between `customer` and `staff`.
- AC2: The owner role cannot be removed from the last owner.
- AC3: Staff cannot see or use this page.
- AC4: Every role change is recorded in the audit log.

### US-710 Delete course · Should
As the **owner**, I want to permanently delete a course, so that test data can be cleaned up.

- AC1: Only allowed if the course has no orders; otherwise suggest unpublishing.
- AC2: Requires typing the course title to confirm.

### US-711 Manage categories & learning paths · Should
As **staff**, I want to create and edit categories and learning paths, so that the catalog stays organized.

- AC1: Categories: name, icon, sort order.
- AC2: Learning paths: name, description, ordered list of courses, completion badge name.

---

## 4. Seed data (for demos)

The project should include seed data so the app looks complete on first run:

- 4 categories: Artificial Intelligence, Machine Learning, Data Analytics, Data Engineering.
- 12 to 16 fictional courses across levels (e.g. "Python for Data Beginners", "Prompt Engineering Fundamentals", "SQL for Analysts", "Intro to Neural Networks").
- 3 learning paths: Data Analyst Path, ML Engineer Path, AI Builder Path.
- 1 owner, 1 staff, and 2 customer demo accounts (passwords documented in the trainer guide, not in the repo README).

All seed content must be fictional, age-appropriate, and must not use real people's names or real company branding.

## 5. Out of scope (this release)

- Real payments, refunds, invoices, taxes, coupons.
- Sending real emails (including Supabase auth emails).
- Delivering course content / video player / LMS features.
- Product reviews and ratings.
- Social login (Google, GitHub).
- Multi-language and multi-currency.
