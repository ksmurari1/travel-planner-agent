"""VoyageIQ - polished Streamlit interface for the CrewAI Travel Planner.

Run with: python -m streamlit run streamlit_app.py
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from travel_planner import DEFAULT_MODEL, CityInput, PlaceRecommendation, TravelPlan, plan_trip

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "search_history.json"
MAX_HISTORY = 15
PRESETS = ["Chennai", "Jaipur", "Kyoto", "Lisbon", "Florence"]
BADGES = ["#1 Must-visit", "#2 Cultural gem", "#3 Local favourite"]

st.set_page_config(
    page_title="VoyageIQ | CrewAI Travel Planner",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,500&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
.stApp { background:#FAF7F2; color:#1C1917; }
html, body, .stApp, .stMarkdown, .stTextInput input, .stButton button, p, label { font-family:'Plus Jakarta Sans',sans-serif; }
.block-container { padding-top:1.7rem; max-width:1300px; }
h1,h2,h3,.serif { font-family:'Playfair Display',Georgia,serif !important; letter-spacing:-.02em; }
#MainMenu, footer { visibility:hidden; }
.hero { position:relative; overflow:hidden; border-radius:22px; padding:2.8rem 2.5rem 2.3rem; color:#fff; margin-bottom:1.4rem;
 background:linear-gradient(115deg,rgba(28,25,23,.91) 5%,rgba(124,45,18,.82) 100%),url('https://images.unsplash.com/photo-1516483638261-f4dbaf036963?auto=format&fit=crop&w=1600&q=80') center/cover;
 box-shadow:0 18px 40px -18px rgba(28,25,23,.4); }
.hero .eyebrow { display:inline-block;font-size:.7rem;font-weight:700;letter-spacing:.17em;text-transform:uppercase;color:#FED7AA;border:1px solid rgba(254,215,170,.45);padding:.35rem .8rem;border-radius:999px;background:rgba(255,255,255,.06); }
.hero h1 { color:#fff!important;font-size:clamp(2.2rem,4vw,3.5rem);line-height:1.08;margin:.85rem 0 .65rem;padding:0;font-weight:800; }
.hero h1 em { color:#FDBA74;font-weight:500; }
.hero p { color:#E7DFD5;max-width:690px;font-size:1rem;line-height:1.65;margin:0; }
.hero .meta { display:flex;gap:1.5rem;margin-top:1.4rem;flex-wrap:wrap; }
.hero .meta div {font-size:.8rem;color:#E2D8CC}.hero .meta b {display:block;font-family:'Playfair Display',serif;font-size:1.35rem;color:#fff}
div[data-testid="stForm"] {background:rgba(255,255,255,.88);border:1px solid #E2D8CC;border-radius:18px;padding:1rem 1rem .25rem;box-shadow:0 10px 30px -18px rgba(28,25,23,.25)}
.stTextInput input {border-radius:11px!important;border:1px solid #E2D8CC!important;background:#fff!important;font-size:1rem!important;padding:.72rem .9rem!important}
.stTextInput input:focus {border-color:#C2410C!important;box-shadow:0 0 0 3px rgba(194,65,12,.14)!important}
.stButton>button,.stFormSubmitButton>button {border-radius:11px!important;font-weight:600!important;min-height:2.8rem;transition:all .18s ease!important}
.stFormSubmitButton>button,.stButton>button[kind="primary"] {background:#C2410C!important;color:white!important;border:none!important;box-shadow:0 6px 16px -6px rgba(194,65,12,.5)!important}
.stFormSubmitButton>button:hover,.stButton>button[kind="primary"]:hover {background:#9A3412!important;transform:translateY(-1px)}
.stButton>button[kind="secondary"] {background:white!important;color:#1C1917!important;border:1px solid #E2D8CC!important}
.stButton>button[kind="secondary"]:hover {background:#FFEDD5!important;border-color:#FDBA74!important;color:#9A3412!important}
section[data-testid="stSidebar"] {background:#F2EBE1;border-right:1px solid #E2D8CC}
.side-label {font-size:.7rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#78716C;margin:1.1rem 0 .5rem}
.status-pill {display:flex;align-items:center;gap:.55rem;padding:.6rem .75rem;border-radius:12px;background:#fff;border:1px solid #E2D8CC;font-size:.8rem;overflow-wrap:anywhere}
.dot {width:9px;height:9px;border-radius:50%;flex:none}.dot.ok {background:#15803D;box-shadow:0 0 0 4px rgba(21,128,61,.12)}.dot.warn {background:#D97706;box-shadow:0 0 0 4px rgba(217,119,6,.12)}
.persona {background:#fff;border:1px solid #E2D8CC;border-radius:14px;padding:.9rem 1rem;font-size:.84rem;color:#57534E;line-height:1.6}.persona b {color:#1C1917;font-family:'Playfair Display',serif;font-size:1rem}
.section-title {display:flex;align-items:baseline;justify-content:space-between;gap:1rem;margin:1.8rem 0 1rem}.section-title h2 {font-size:1.9rem!important;font-weight:700!important;margin:0;padding:0!important;color:#1C1917}.section-title .sub {color:#78716C;font-size:.8rem}
.place-card {background:#fff;border:1px solid #E2D8CC;border-radius:18px;padding:1.35rem 1.25rem 1.2rem;min-height:350px;height:100%;position:relative;overflow:hidden;box-shadow:0 4px 14px rgba(28,25,23,.04);transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease;animation:rise .45s ease-out both}
.place-card:hover {transform:translateY(-3px);box-shadow:0 18px 32px -14px rgba(194,65,12,.22);border-color:#FDBA74}.place-card .num {position:absolute;right:.7rem;top:.1rem;font-family:'Playfair Display',serif;font-size:4.8rem;font-weight:800;color:#F2EBE1;line-height:1;z-index:0}.place-card>* {position:relative;z-index:1}
.badge {display:inline-block;background:#FFEDD5;color:#9A3412;font-weight:700;font-size:.68rem;padding:.3rem .65rem;border-radius:999px}
.place-card h3 {font-size:1.35rem!important;font-weight:700!important;margin:.75rem 0 .55rem;padding:0;line-height:1.25;color:#1C1917}.place-card .desc {color:#44403C;font-size:.9rem;line-height:1.6;margin-bottom:.85rem}.place-card .row {border-top:1px dashed #E2D8CC;padding-top:.7rem;margin-top:.7rem}.place-card .row .k {font-size:.65rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#C2410C;margin-bottom:.25rem}.place-card .row .v {font-size:.86rem;color:#1C1917;line-height:1.55}
.log-box {background:#18181B;color:#E4E4E7;font-family:'JetBrains Mono',monospace;font-size:.78rem;border-radius:13px;padding:1rem;max-height:320px;overflow-y:auto;line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere}
.empty {border:1.5px dashed #E2D8CC;border-radius:18px;padding:2.3rem;text-align:center;color:#78716C;background:rgba(255,255,255,.5)}.empty .serif {font-size:1.5rem;color:#1C1917;margin-bottom:.35rem}
@keyframes rise {from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@media(max-width:700px){.hero{padding:1.6rem 1.3rem}.hero h1{font-size:2.15rem}.section-title{display:block}.place-card{min-height:unset}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(value: Any) -> str:
    return html.escape(str(value))


def load_history() -> list[dict[str, Any]]:
    try:
        raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        # Discard malformed history records instead of crashing the app.
        valid: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict) or not isinstance(item.get("city"), str):
                continue
            try:
                plan = TravelPlan.model_validate(item.get("plan", {}))
            except ValidationError:
                continue
            valid.append({
                "city": plan.city,
                "searched_at": str(item.get("searched_at", "Previous search")),
                "demo": bool(item.get("demo", False)),
                "plan": plan.model_dump(),
            })
        return valid[:MAX_HISTORY]
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def save_history(items: list[dict[str, Any]]) -> None:
    try:
        HISTORY_FILE.write_text(json.dumps(items[:MAX_HISTORY], indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        st.sidebar.warning("Search history could not be saved to disk.")


def add_to_history(plan: TravelPlan, demo: bool) -> None:
    existing = [item for item in st.session_state.history if item.get("city", "").casefold() != plan.city.casefold()]
    existing.insert(0, {
        "city": plan.city,
        "searched_at": datetime.now().strftime("%d %b %Y, %H:%M"),
        "demo": demo,
        "plan": plan.model_dump(),
    })
    st.session_state.history = existing[:MAX_HISTORY]
    save_history(st.session_state.history)


def demo_plan(city: str) -> TravelPlan:
    """Clearly-labelled illustrative data used only to preview the UI offline."""
    cleaned = CityInput(city=city).city
    # These are intentionally generic placeholders, not factual recommendations.
    return TravelPlan(city=cleaned, places=[
        PlaceRecommendation(
            name=f"Historic district of {cleaned}",
            description=f"A sample suggestion to explore the historic streets and architecture of {cleaned}.",
            why_visit="This placeholder demonstrates how a cultural walking stop can be presented.",
            best_time="Demo content only; check local travel guidance before planning a visit.",
        ),
        PlaceRecommendation(
            name=f"Cultural museum in {cleaned}",
            description=f"A sample museum idea for learning about the people, art, and history of {cleaned}.",
            why_visit="Museums can provide useful context for the places you visit around a city.",
            best_time="Demo content only; verify the venue and opening hours independently.",
        ),
        PlaceRecommendation(
            name=f"Local market in {cleaned}",
            description=f"A sample idea for exploring local food, crafts, and everyday city life in {cleaned}.",
            why_visit="Markets can be an enjoyable way to experience local flavours and crafts.",
            best_time="Demo content only; check market days and local conditions before visiting.",
        ),
    ])


def render_cards(plan: TravelPlan) -> None:
    st.markdown(
        f'<div class="section-title"><h2>Three places in {esc(plan.city)}</h2>'
        '<span class="sub">Curated by your CrewAI Travel Planner</span></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3, gap="medium")
    for index, (column, place) in enumerate(zip(cols, plan.places)):
        with column:
            st.markdown(
                f'<div class="place-card"><div class="num">0{index + 1}</div>'
                f'<span class="badge">{BADGES[index]}</span>'
                f'<h3>{esc(place.name)}</h3><div class="desc">{esc(place.description)}</div>'
                f'<div class="row"><div class="k">Why visit</div><div class="v">{esc(place.why_visit)}</div></div>'
                f'<div class="row"><div class="k">Best time to go</div><div class="v">{esc(place.best_time)}</div></div></div>',
                unsafe_allow_html=True,
            )


def pick_preset(city: str) -> None:
    st.session_state.city_input = city
    st.session_state.pending_city = city


def load_saved(index: int) -> None:
    item = st.session_state.history[index]
    st.session_state.plan = TravelPlan.model_validate(item["plan"])
    st.session_state.city_input = item["city"]
    st.session_state.pending_city = None
    st.session_state.execution_log = [f"Loaded saved plan for {item['city']} from local history."]
    st.session_state.plan_is_demo = bool(item.get("demo", False))


def clear_history() -> None:
    st.session_state.history = []
    save_history([])


# Initialize state once per browser session.
st.session_state.setdefault("history", load_history())
st.session_state.setdefault("plan", None)
st.session_state.setdefault("execution_log", [])
st.session_state.setdefault("pending_city", None)
st.session_state.setdefault("city_input", "")
st.session_state.setdefault("plan_is_demo", False)

has_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
model_name = os.getenv("OPENAI_MODEL_NAME", os.getenv("MODEL", DEFAULT_MODEL))

with st.sidebar:
    st.markdown("### 🧭 VoyageIQ")
    st.caption("A CrewAI travel-planning agent")
    st.markdown('<div class="side-label">Connection</div>', unsafe_allow_html=True)
    if has_key:
        st.markdown(
            f'<div class="status-pill"><span class="dot ok"></span><span>OPENAI_API_KEY found · {esc(model_name)}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-pill"><span class="dot warn"></span><span>OPENAI_API_KEY not set</span></div>',
            unsafe_allow_html=True,
        )
    demo_mode = st.toggle(
        "Demo mode (sample data, no API calls)",
        value=not has_key,
        key="demo_mode",
        help="Preview the design without calling an LLM. Sample destinations are illustrative, not factual travel advice.",
    )
    st.markdown('<div class="side-label">Your agent</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="persona"><b>Senior Travel Planner</b><br>One CrewAI agent, one task, one crew. '
        'Returns exactly three places with descriptions, reasons to visit, and timing guidance.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">Search history</div>', unsafe_allow_html=True)
    if not st.session_state.history:
        st.caption("Cities you search will appear here.")
    else:
        for idx, item in enumerate(st.session_state.history):
            label = f"📍 {item['city']} · {item['searched_at']}" + (" (demo)" if item.get("demo") else "")
            st.button(label, key=f"history_{idx}", use_container_width=True, on_click=load_saved, args=(idx,))
        st.button("Clear history", key="clear_history", use_container_width=True, on_click=clear_history)

st.markdown(
    '<div class="hero"><span class="eyebrow">CrewAI · Travel Planner Agent</span>'
    '<h1>Where to next? <em>Pick a city.</em></h1>'
    '<p>Enter a city and let your travel planner curate three places worth your time, '
    'with why they matter and a suggested time to go.</p>'
    '<div class="meta"><div><b>1</b>Agent</div><div><b>1</b>Task</div><div><b>3</b>Places</div></div></div>',
    unsafe_allow_html=True,
)

with st.form("travel_search", clear_on_submit=False, border=False):
    input_col, button_col = st.columns([5, 1.4], vertical_alignment="bottom")
    with input_col:
        city_value = st.text_input("City", key="city_input", placeholder="e.g. Chennai, Paris, Jaipur, Rome", label_visibility="collapsed")
    with button_col:
        submitted = st.form_submit_button("Plan my trip →", use_container_width=True)

preset_cols = st.columns([0.5, 1, 1, 1, 1, 1])
preset_cols[0].caption("Try:")
for idx, preset in enumerate(PRESETS, start=1):
    preset_cols[idx].button(preset, key=f"preset_{preset}", use_container_width=True, on_click=pick_preset, args=(preset,))

pending = st.session_state.pending_city
target = pending or (city_value if submitted else None)
if target:
    st.session_state.pending_city = None
    try:
        validated_city = CityInput(city=target).city
        execution_log = [f"{datetime.now().strftime('%H:%M:%S')} · Preparing a plan for {validated_city}."]
        with st.status(f"Planning {validated_city}…", expanded=True) as status:
            if demo_mode:
                execution_log.append("Demo mode enabled: no API calls will be made.")
                execution_log.append("Creating clearly-labelled sample content for the UI preview.")
                plan = demo_plan(validated_city)
            else:
                if not has_key:
                    raise ValueError("OPENAI_API_KEY is missing. Add it to .env and restart Streamlit, or enable Demo mode.")
                execution_log.append(f"Starting CrewAI with model {model_name}.")
                execution_log.append("Running one agent and one task; validating structured output.")
                plan = plan_trip(validated_city)
                execution_log.append("CrewAI completed; Pydantic validation passed.")
            status.update(label=f"Plan ready for {plan.city}", state="complete", expanded=False)
        st.session_state.plan = plan
        st.session_state.plan_is_demo = demo_mode
        st.session_state.execution_log = execution_log
        add_to_history(plan, demo_mode)
    except ValidationError as exc:
        st.warning("Please enter a valid city name. City cannot be blank and must be 100 characters or fewer.")
        st.session_state.execution_log = [f"Input validation failed: {exc.errors()[0].get('msg', 'invalid input')}"]
    except ValueError as exc:
        st.error(str(exc))
        st.session_state.execution_log = [f"Configuration/input error: {exc}"]
    except RuntimeError as exc:
        st.error(str(exc))
        st.session_state.execution_log = [f"Planning error: {exc}"]
    except Exception:
        st.error("Something unexpected went wrong while planning. Check the terminal for details and try again.")
        st.session_state.execution_log = ["Unexpected error. Details were intentionally not shown in the browser."]
elif submitted and not city_value.strip():
    st.warning("Please enter a city name before planning your trip.")

if st.session_state.plan is not None:
    if st.session_state.plan_is_demo:
        st.info("Demo preview: these are illustrative placeholders, not verified recommendations for this city.")
    render_cards(st.session_state.plan)
    with st.expander("🧠 Agent execution log", expanded=False):
        st.markdown('<div class="log-box">' + "<br>".join(esc(line) for line in st.session_state.execution_log) + "</div>", unsafe_allow_html=True)
    st.download_button(
        "Download plan (JSON)",
        data=st.session_state.plan.model_dump_json(indent=2),
        file_name=f"{st.session_state.plan.city.lower().replace(' ', '_')}_travel_plan.json",
        mime="application/json",
        key="download_plan",
    )
else:
    st.markdown('<div class="empty"><div class="serif">Your itinerary starts here</div>Enter a city above or pick one of the suggestions.</div>', unsafe_allow_html=True)

st.caption("Travel suggestions are AI-generated. Verify current opening hours, prices, and local conditions before travelling.")
