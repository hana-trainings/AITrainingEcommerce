# AI Training E-commerce

A demo e-commerce web app built with **Streamlit** and **Supabase**, created for
training purposes. It also serves as a hands-on example for deploying to
**Streamlit Community Cloud** or **Vercel**.

> Demo/training project only. Not intended for real transactions.

## Status

Project skeleton only. Application code will be generated from the documents in
[`docs/requirements/`](docs/requirements/).

## Folder structure

```
.
├── app/                  # Streamlit application
│   ├── pages/            # Streamlit multipage screens
│   ├── components/       # Reusable UI pieces
│   ├── services/         # Supabase access / business logic
│   ├── models/           # Data models / schemas
│   ├── utils/            # Helpers
│   └── config/           # App settings
├── assets/               # Images and custom styles
├── docs/
│   ├── requirements/     # Requirement documents (input for code generation)
│   ├── architecture/     # Design notes and diagrams
│   ├── deployment/       # Deployment guides (Streamlit Cloud, Vercel)
│   └── planning/         # Team work division and sprint plan
├── supabase/
│   ├── migrations/       # SQL schema migrations
│   └── seed/             # Sample/demo data
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/              # Helper scripts (setup, seeding, etc.)
├── .streamlit/           # Streamlit config and secrets template
├── .env.example          # Environment variable template
└── requirements.txt      # Python dependencies (to be filled in)
```

## Configuration

Secrets are never committed. Copy the templates and fill in your Supabase values:

- `.env.example` → `.env`
- `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
