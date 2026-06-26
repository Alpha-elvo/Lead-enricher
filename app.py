"""
app.py — Streamlit UI for Lead Enrichment & Competitor Alerts
Thin presentation layer; all logic lives in scraper.py.
"""

import os
import streamlit as st
from scraper import scrape_lead, save_lead_to_db, send_lead_email

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Lead Enricher",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS — minimal, purposeful overrides
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Base palette ── */
:root {
    --indigo:   #6366f1;
    --violet:   #8b5cf6;
    --slate-50: #f8fafc;
    --slate-100:#f1f5f9;
    --slate-300:#cbd5e1;
    --slate-500:#64748b;
    --slate-700:#334155;
    --slate-900:#0f172a;
}

/* ── App background ── */
.stApp { background: var(--slate-50); }

/* ── Card wrapper ── */
.card {
    background: #fff;
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 20px;
    box-shadow: 0 2px 16px rgba(0,0,0,.06);
    border: 1px solid var(--slate-100);
}

/* ── Section label above widgets ── */
.field-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.6px;
    text-transform: uppercase;
    color: var(--slate-500);
    margin-bottom: 4px;
}

/* ── Social pill badges ── */
.pill {
    display: inline-block;
    background: #ede9fe;
    color: #5b21b6;
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 600;
    margin: 3px 4px 3px 0;
    text-decoration: none;
}
.pill:hover { background: #ddd6fe; }

/* ── Primary button ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, var(--indigo), var(--violet));
    border: none;
    border-radius: 8px;
    color: #fff;
    font-weight: 600;
    padding: 10px 28px;
    width: 100%;
    font-size: 15px;
    letter-spacing: .3px;
    transition: opacity .15s;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { opacity: .88; }

/* ── Metric cards ── */
div[data-testid="stMetric"] {
    background: var(--slate-50);
    border-radius: 10px;
    padding: 16px;
    border: 1px solid var(--slate-100);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "lead" not in st.session_state:
    st.session_state.lead = None
if "db_saved" not in st.session_state:
    st.session_state.db_saved = False
if "email_sent" not in st.session_state:
    st.session_state.email_sent = False


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div style="padding:8px 0 24px;">
  <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:2.5px;
            text-transform:uppercase;color:#6366f1;">Automated Intelligence</p>
  <h1 style="margin:4px 0 6px;font-size:32px;font-weight:800;color:#0f172a;
             letter-spacing:-.5px;">Lead Enricher</h1>
  <p style="margin:0;font-size:15px;color:#64748b;max-width:480px;line-height:1.5;">
    Drop in a competitor or prospect URL. Get the company name, description,
    and social profiles — saved to your database and delivered to your inbox.
  </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------
st.markdown('<p class="field-label">Target URL</p>', unsafe_allow_html=True)
target_url = st.text_input(
    label="Target URL",
    placeholder="https://example.com",
    label_visibility="collapsed",
)

st.markdown('<p class="field-label" style="margin-top:16px;">Destination Email</p>',
            unsafe_allow_html=True)
dest_email = st.text_input(
    label="Destination Email",
    placeholder="you@yourcompany.com",
    label_visibility="collapsed",
)

st.markdown("<br>", unsafe_allow_html=True)
run_button = st.button("Enrich Lead →", type="primary", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main enrichment flow
# ---------------------------------------------------------------------------
if run_button:
    # ── Input validation ──────────────────────────────────────────────────
    errors = []
    if not target_url.strip():
        errors.append("Please enter a target URL.")
    elif not target_url.strip().startswith(("http://", "https://")):
        errors.append("URL must start with `http://` or `https://`.")
    if not dest_email.strip() or "@" not in dest_email:
        errors.append("Please enter a valid email address.")

    if errors:
        for err in errors:
            st.error(err)
        st.stop()

    # Reset state for a fresh run
    st.session_state.lead = None
    st.session_state.db_saved = False
    st.session_state.email_sent = False

    # ── Step 1: Scrape ────────────────────────────────────────────────────
    with st.spinner("Fetching and analysing the page…"):
        lead = scrape_lead(target_url.strip())

    if not lead.success:
        st.error(f"**Scrape failed:** {lead.error}")
        st.stop()

    st.session_state.lead = lead
    st.success("Page scraped successfully.")

    # ── Step 2: Save to Supabase ──────────────────────────────────────────
    with st.spinner("Saving lead to database…"):
        try:
            row = save_lead_to_db(lead)
            st.session_state.db_saved = True
            st.success(f"Saved to Supabase (row id: `{row.get('id', '—')}`).")
        except EnvironmentError as exc:
            st.warning(f"**Database skipped** — credentials not configured: {exc}")
        except RuntimeError as exc:
            st.warning(f"**Database write failed:** {exc}")

    # ── Step 3: Send email ────────────────────────────────────────────────
    with st.spinner("Sending enrichment email…"):
        try:
            msg_id = send_lead_email(lead, dest_email.strip())
            st.session_state.email_sent = True
            st.success(f"Email dispatched via Resend (id: `{msg_id}`).")
        except EnvironmentError as exc:
            st.warning(f"**Email skipped** — credentials not configured: {exc}")
        except RuntimeError as exc:
            st.warning(f"**Email failed:** {exc}")

# ---------------------------------------------------------------------------
# Results panel — rendered from session state so it persists across reruns
# ---------------------------------------------------------------------------
lead = st.session_state.get("lead")

if lead and lead.success:
    st.divider()

    st.markdown("""
    <p style="font-size:11px;font-weight:700;letter-spacing:2px;
              text-transform:uppercase;color:#6366f1;margin-bottom:16px;">
      Enrichment Results
    </p>
    """, unsafe_allow_html=True)

    # ── Key metrics ────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("Company", lead.company_name[:26] + ("…" if len(lead.company_name) > 26 else ""))
    col2.metric("Social Profiles Found", len(lead.social_links))
    col3.metric("Scraped At", lead.scraped_at[11:16] + " UTC")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Page title ────────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="field-label">Page Title</p>', unsafe_allow_html=True)
        st.write(lead.page_title)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Description ───────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="field-label">Meta Description</p>', unsafe_allow_html=True)
        st.write(lead.description)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Social links ──────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="field-label">Social Profiles</p>', unsafe_allow_html=True)
        if lead.social_links:
            pills_html = " ".join(
                f'<a class="pill" href="{link}" target="_blank" rel="noopener">{platform}</a>'
                for platform, link in lead.social_links.items()
            )
            st.markdown(pills_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            for platform, link in lead.social_links.items():
                st.caption(f"**{platform}** — {link}")
        else:
            st.caption("No social profiles detected on this page.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Raw data expander ─────────────────────────────────────────────────
    with st.expander("View raw JSON payload"):
        import json
        payload = {
            "url":          lead.url,
            "company_name": lead.company_name,
            "page_title":   lead.page_title,
            "description":  lead.description,
            "social_links": lead.social_links,
            "scraped_at":   lead.scraped_at,
        }
        st.code(json.dumps(payload, indent=2), language="json")

# ---------------------------------------------------------------------------
# Sidebar — environment variable status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Config Status")
    st.caption("Variables read from environment:")

    checks = {
        "SUPABASE_URL":  bool(os.environ.get("SUPABASE_URL")),
        "SUPABASE_KEY":  bool(os.environ.get("SUPABASE_KEY")),
        "RESEND_API_KEY": bool(os.environ.get("RESEND_API_KEY")),
    }
    for var, ok in checks.items():
        icon = "✅" if ok else "❌"
        st.markdown(f"{icon} `{var}`")

    st.divider()
    st.caption(
        "Set secrets in **Settings → Secrets** on Streamlit Community Cloud, "
        "or export them in your local shell before running `streamlit run app.py`."
    )
