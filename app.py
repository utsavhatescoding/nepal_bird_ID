import base64
import hashlib
import html
import io
from pathlib import Path

import streamlit as st
from PIL import Image, UnidentifiedImageError

from bird_guide import render_bird_guide
from model_utils import (
    MODEL_PATH,
    build_and_load_model,
    load_class_names,
    make_gradcam_images,
    predict_top_k,
    split_class_name,
)


APP_DIR = Path(__file__).resolve().parent
HERO_PATH = APP_DIR / "assets" / "nepal-bird-hero.webp"
LOGO_PATH = APP_DIR / "assets" / "nepal-bird-mark.svg"

st.set_page_config(
    page_title="Nepal Bird ID — Identify birds of Nepal",
    page_icon=str(LOGO_PATH),
    layout="centered",
    initial_sidebar_state="collapsed",
)


@st.cache_resource(show_spinner="Preparing the bird model…")
def get_model():
    return build_and_load_model()


def confidence_details(confidence):
    if confidence >= 0.75:
        return "Strong match", "The model sees a clear resemblance within its 85 known species."
    if confidence >= 0.50:
        return "Possible match", "Compare the alternatives and visible field marks."
    return "Uncertain", "Try a closer, sharper photograph before relying on this suggestion."


def clear_identification():
    st.session_state.upload_version += 1
    st.session_state.prediction_key = None
    st.session_state.prediction_results = None
    st.session_state.gradcam_key = None
    st.session_state.gradcam_images = None


def footer():
    st.markdown(
        """
        <footer class="site-footer">
          <div><strong>Nepal Bird ID</strong><br><span>An independent bird ecology and conservation-learning prototype.</span></div>
          <div class="footer-note-right">85 species · Responsible observation · Built for Nepal</div>
        </footer>
        """,
        unsafe_allow_html=True,
    )


for key, default in {
    "upload_version": 0,
    "prediction_key": None,
    "prediction_results": None,
    "gradcam_key": None,
    "gradcam_images": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


hero_data = base64.b64encode(HERO_PATH.read_bytes()).decode("ascii") if HERO_PATH.exists() else ""
logo_data = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii") if LOGO_PATH.exists() else ""

st.markdown(
    f"""
    <style>
    :root {{
      --pine-950:#062d23; --pine-900:#0b3b2e; --pine-800:#17513d;
      --leaf:#4e9b58; --leaf-bright:#8fc55a; --sky:#2f8194;
      --ink:#14372c; --muted:#64746e; --mist:#eef4ef;
      --line:#dce6df; --paper:#ffffff; --canvas:#f7f8f4;
      --warning:#a65c1b;
    }}
    .stApp {{background:var(--canvas); color:var(--ink);}}
    .block-container {{max-width:1040px; padding:0 1.15rem 4rem;}}
    header[data-testid="stHeader"] {{height:0; background:transparent;}}
    #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], [data-testid="stSidebarCollapsedControl"] {{display:none !important;}}
    h1,h2,h3 {{color:var(--ink); letter-spacing:-.035em;}}
    p {{line-height:1.58;}}

    .site-header {{height:74px; display:flex; align-items:center; justify-content:space-between; gap:1rem;}}
    .site-brand {{display:flex; align-items:center; gap:.75rem;}}
    .site-brand img {{width:42px; height:42px; display:block;}}
    .brand-name {{display:block; font-size:1rem; font-weight:800; letter-spacing:-.02em; color:var(--pine-950);}}
    .brand-sub {{display:block; margin-top:.08rem; font-size:.68rem; color:#71817a; letter-spacing:.09em; text-transform:uppercase; font-weight:700;}}
    .header-badge {{display:flex; align-items:center; gap:.45rem; color:var(--pine-800); font-size:.76rem; font-weight:700;}}
    .live-dot {{width:8px; height:8px; border-radius:50%; background:var(--leaf); box-shadow:0 0 0 4px rgba(78,155,88,.13);}}

    .hero-shell {{height:310px; border-radius:24px; overflow:hidden; position:relative; display:flex; align-items:center;
      background-image:linear-gradient(90deg,rgba(5,43,33,.98) 0%,rgba(5,43,33,.92) 38%,rgba(5,43,33,.38) 65%,rgba(5,43,33,.04) 100%),url("data:image/webp;base64,{hero_data}");
      background-size:cover; background-position:center 46%; box-shadow:0 14px 38px rgba(12,53,40,.12);}}
    .hero-copy {{width:56%; padding:2.2rem 2.4rem; color:white; position:relative; z-index:1;}}
    .hero-eyebrow {{display:flex; align-items:center; gap:.5rem; color:#cde6bf; font-size:.7rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase;}}
    .hero-eyebrow svg {{width:16px; height:16px; stroke:#9bd168;}}
    .hero-copy h1 {{font-size:clamp(2.45rem,5.4vw,4rem); line-height:.98; margin:.75rem 0 .75rem; color:white; max-width:520px;}}
    .hero-copy p {{max-width:500px; margin:0; color:rgba(255,255,255,.86); font-size:.98rem;}}
    .hero-proof {{display:flex; gap:.6rem; flex-wrap:wrap; margin-top:1.1rem;}}
    .proof-pill {{padding:.34rem .62rem; border-radius:999px; color:#dce9e3; background:rgba(255,255,255,.09); border:1px solid rgba(255,255,255,.14); font-size:.69rem; font-weight:700;}}

    [data-testid="stSegmentedControl"] {{margin:.7rem 0 0; position:relative; z-index:20;}}
    [data-testid="stSegmentedControl"] > div {{width:100%; justify-content:center; background:var(--paper); border:1px solid var(--line); border-radius:14px; padding:.25rem; box-shadow:0 5px 20px rgba(13,53,41,.05);}}
    [data-testid="stSegmentedControl"] button {{flex:1; border:0 !important; border-radius:10px !important; min-height:2.7rem; font-size:.82rem; font-weight:780; color:#52665d;}}
    [data-testid="stSegmentedControl"] button[aria-pressed="true"] {{background:var(--pine-900) !important; color:white !important;}}

    .section-head {{margin:2.25rem 0 1rem;}}
    .section-kicker {{display:flex; align-items:center; gap:.45rem; color:var(--leaf); font-size:.69rem; font-weight:850; letter-spacing:.13em; text-transform:uppercase; margin-bottom:.35rem;}}
    .section-kicker:before {{content:""; width:20px; height:2px; border-radius:2px; background:var(--leaf);}}
    .section-head h2 {{font-size:clamp(1.7rem,3.7vw,2.45rem); margin:0 0 .35rem;}}
    .section-head p {{color:var(--muted); margin:0; max-width:640px;}}
    .compact-head {{margin-top:1.8rem;}}

    .upload-shell {{display:grid; grid-template-columns:1fr auto; align-items:center; gap:1rem; padding:1rem 1.1rem; margin-bottom:.65rem; background:var(--mist); border-radius:16px;}}
    .upload-shell strong {{display:block; color:var(--pine-900); font-size:.86rem;}}
    .upload-shell span {{display:block; color:var(--muted); font-size:.75rem; margin-top:.12rem;}}
    .step-chip {{padding:.36rem .6rem; border-radius:999px; color:var(--pine-800); background:white; border:1px solid var(--line); font-size:.68rem; font-weight:800;}}
    [data-testid="stFileUploader"] {{background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:.55rem .75rem .2rem; box-shadow:0 8px 28px rgba(12,53,40,.05);}}
    [data-testid="stFileUploaderDropzone"] {{min-height:132px; border:1.5px dashed #a6b9ad; border-radius:13px; background:#fbfcfa;}}
    [data-testid="stFileUploaderDropzone"] button {{border-radius:999px; border-color:var(--pine-800); color:var(--pine-800); font-weight:750;}}

    .tip-grid {{display:grid; grid-template-columns:repeat(3,1fr); gap:.65rem; margin-top:.75rem;}}
    .tip-card {{display:flex; gap:.65rem; align-items:flex-start; padding:.8rem; border-radius:14px; background:white; border:1px solid var(--line);}}
    .line-icon {{width:32px; height:32px; min-width:32px; display:grid; place-items:center; border-radius:10px; background:#e8f2e8; color:var(--pine-800);}}
    .line-icon svg {{width:17px; height:17px; fill:none; stroke:currentColor; stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round;}}
    .tip-card strong {{display:block; font-size:.76rem; color:var(--ink);}}
    .tip-card span {{display:block; font-size:.68rem; color:var(--muted); margin-top:.12rem; line-height:1.35;}}

    [data-testid="stImage"] img {{border-radius:16px;}}
    .action-panel {{background:white; border:1px solid var(--line); border-radius:17px; padding:1rem; margin-bottom:.75rem;}}
    .action-panel .line-icon {{margin-bottom:.7rem;}}
    .action-panel h3 {{font-size:1.06rem; margin:0 0 .35rem;}}
    .action-panel p {{font-size:.79rem; color:var(--muted); margin:0;}}
    .stButton > button {{border-radius:12px; min-height:3rem; font-weight:790; border-width:1px;}}
    .stButton > button[kind="primary"] {{background:var(--leaf); border-color:var(--leaf); color:white; box-shadow:0 7px 18px rgba(78,155,88,.2);}}
    .stButton > button[kind="primary"]:hover {{background:#43894c; border-color:#43894c; color:white;}}

    .result-card {{display:grid; grid-template-columns:1fr auto; gap:1.25rem; align-items:center; background:var(--pine-900); color:white; padding:1.4rem 1.5rem; border-radius:20px; margin:.25rem 0 1rem; box-shadow:0 12px 30px rgba(8,48,36,.13);}}
    .result-label {{font-size:.66rem; font-weight:850; letter-spacing:.13em; text-transform:uppercase; color:#a9d4ad;}}
    .result-card h2,.profile-card h2 {{font-size:clamp(1.8rem,4vw,2.65rem); line-height:1; margin:.45rem 0 .28rem; color:white;}}
    .result-latin {{font-style:italic; color:#c8d8d1;}}
    .score-block {{min-width:132px; text-align:right; padding-left:1.1rem; border-left:1px solid rgba(255,255,255,.15);}}
    .score-number {{display:block; font-size:2rem; line-height:1; font-weight:850; color:#b9dd83;}}
    .score-status {{display:block; font-size:.73rem; font-weight:750; margin-top:.32rem;}}
    .score-note {{grid-column:1/-1; font-size:.77rem; color:#c4d4cd; border-top:1px solid rgba(255,255,255,.12); padding-top:.75rem;}}
    .alt-card {{display:grid; grid-template-columns:1fr auto; gap:.75rem; padding:.82rem .9rem; background:white; border:1px solid var(--line); border-radius:13px; margin:.5rem 0 .25rem;}}
    .alt-name {{font-weight:790; color:var(--ink); font-size:.86rem;}}
    .alt-latin {{display:block; font-style:italic; color:var(--muted); font-size:.73rem; margin-top:.12rem;}}
    .alt-score {{color:var(--pine-800); font-size:.8rem; font-weight:820;}}
    [data-testid="stProgress"] {{margin-bottom:.55rem;}}
    [data-testid="stProgress"] > div > div > div > div {{background-color:var(--leaf);}}
    .notice {{background:#edf4ed; border:1px solid #d9e7d9; border-radius:13px; padding:.82rem .9rem; color:#435a4f; font-size:.78rem; line-height:1.48;}}

    .eco-grid {{display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin-top:.9rem;}}
    .eco-card {{background:white; border:1px solid var(--line); border-radius:16px; padding:1rem;}}
    .eco-card .line-icon {{margin-bottom:.75rem;}}
    .eco-card h3 {{font-size:.93rem; margin:0 0 .25rem;}}
    .eco-card p {{font-size:.75rem; color:var(--muted); margin:0; line-height:1.48;}}
    [data-testid="stMetric"] {{background:white; border:1px solid var(--line); border-radius:14px; padding:.75rem .9rem;}}
    .profile-card {{background:var(--pine-900); color:white; padding:1.2rem; border-radius:18px;}}
    .taxonomy {{display:flex; justify-content:space-between; gap:1rem; border-top:1px solid rgba(255,255,255,.14); padding:.58rem 0; font-size:.79rem;}}
    .taxonomy span {{color:#b9cbc4;}}
    .status-row {{display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.65rem;}}
    .status-pill {{border-radius:999px; padding:.3rem .52rem; font-size:.66rem; font-weight:800;}}
    .status-cr {{background:#ffd7d2;color:#8c2016}} .status-en {{background:#ffe6b6;color:#714600}}
    .status-vu {{background:#fff3ba;color:#665100}} .status-none {{background:#dce8df;color:#345246}}
    .species-list {{display:grid; grid-template-columns:1fr 1fr; gap:.48rem; margin:.7rem 0 2rem;}}
    .species-row {{display:grid; grid-template-columns:2rem 1fr auto auto; align-items:center; gap:.65rem; padding:.72rem; background:white; border:1px solid var(--line); border-radius:12px;}}
    .species-number {{display:grid; place-items:center; width:1.8rem; height:1.8rem; border-radius:9px; background:#e7f1e7; color:var(--pine-800); font-size:.66rem; font-weight:850;}}
    .species-row strong {{display:block; color:var(--ink); font-size:.8rem; line-height:1.2;}}
    .species-row small {{display:block; color:var(--muted); font-size:.67rem; font-style:italic; margin-top:.1rem;}}
    .species-order {{color:#728279; font-size:.61rem;}} .mini-threat {{background:#ffebcb; color:#77470e; border-radius:999px; padding:.17rem .36rem; font-size:.61rem; font-weight:850;}}
    .purpose-panel {{background:var(--pine-900); color:white; border-radius:20px; padding:1.5rem; margin-top:.8rem;}}
    .purpose-panel h2,.purpose-panel h3 {{color:white;}} .purpose-panel p {{color:#d5e1dc;}}
    .site-footer {{display:flex; justify-content:space-between; gap:1rem; align-items:flex-end; border-top:1px solid var(--line); margin-top:2.5rem; padding:1.2rem 0 .4rem; color:var(--muted); font-size:.72rem;}}
    .site-footer strong {{color:var(--pine-900); font-size:.82rem;}} .footer-note-right {{text-align:right;}}

    @media (max-width:900px) and (min-width:701px) {{
      .block-container {{padding-left:1rem; padding-right:1rem;}}
      .hero-shell {{height:290px; background-position:58% center;}}
      .hero-copy {{width:64%; padding:1.8rem;}}
      .hero-copy h1 {{font-size:3rem;}}
      .species-row {{grid-template-columns:1.9rem 1fr auto;}}
      .species-order {{display:none;}}
    }}

    @media (max-width:700px) {{
      .block-container {{padding:0 .8rem 5.7rem;}}
      .site-header {{height:62px;}} .site-brand img {{width:36px;height:36px;}} .brand-sub,.header-badge {{display:none;}}
      .hero-shell {{height:365px; align-items:flex-end; border-radius:18px; background-position:61% center;
        background-image:linear-gradient(0deg,rgba(5,43,33,.98) 0%,rgba(5,43,33,.83) 45%,rgba(5,43,33,.06) 78%),url("data:image/webp;base64,{hero_data}");}}
      .hero-copy {{width:100%; padding:1.35rem;}} .hero-copy h1 {{font-size:2.45rem; max-width:340px;}} .hero-copy p {{font-size:.86rem; max-width:330px;}}
      .hero-proof {{margin-top:.8rem;}} .proof-pill {{font-size:.61rem;}}
      [data-testid="stSegmentedControl"] {{position:fixed; left:.7rem; right:.7rem; bottom:.65rem; z-index:9999; margin:0;}}
      [data-testid="stSegmentedControl"] > div {{box-shadow:0 10px 32px rgba(7,44,34,.2); border-color:#cfdcd3;}}
      .section-head {{margin:1.75rem 0 .85rem;}} .section-head h2 {{font-size:1.85rem;}}
      .tip-grid,.eco-grid,.species-list {{grid-template-columns:1fr;}}
      [data-testid="stHorizontalBlock"] {{flex-direction:column; gap:.45rem;}}
      [data-testid="column"] {{width:100% !important; flex:1 1 100% !important;}}
      .result-card {{grid-template-columns:1fr;}} .score-block {{text-align:left; padding:.75rem 0 0; border-left:0; border-top:1px solid rgba(255,255,255,.15);}}
      .score-note {{grid-column:1;}} .species-order {{display:none;}} .footer-note-right {{display:none;}}
    }}
    @media (max-width:420px) {{
      .block-container {{padding-left:.65rem; padding-right:.65rem;}}
      .hero-shell {{height:342px; border-radius:16px;}}
      .hero-copy {{padding:1.05rem;}}
      .hero-copy h1 {{font-size:2.18rem;}}
      .hero-copy p {{font-size:.8rem; line-height:1.45;}}
      .proof-pill {{padding:.28rem .45rem;}}
      .proof-pill:nth-child(3) {{display:none;}}
      [data-testid="stSegmentedControl"] {{left:.5rem; right:.5rem; bottom:.5rem;}}
      [data-testid="stSegmentedControl"] button {{font-size:.75rem; min-height:2.85rem;}}
      .upload-shell {{grid-template-columns:1fr; gap:.5rem;}}
      .step-chip {{justify-self:start;}}
      .site-footer {{align-items:flex-start;}}
    }}
    @media (max-height:560px) and (orientation:landscape) {{
      .hero-shell {{height:230px;}}
      .hero-copy h1 {{font-size:2.15rem;}}
      .hero-proof {{display:none;}}
    }}
    </style>
    <header class="site-header">
      <div class="site-brand">
        <img src="data:image/svg+xml;base64,{logo_data}" alt="Nepal Bird ID">
        <div><span class="brand-name">Nepal Bird ID</span><span class="brand-sub">Birds · Habitats · Nepal</span></div>
      </div>
      <div class="header-badge"><span class="live-dot"></span>For learning &amp; conservation</div>
    </header>
    <section class="hero-shell">
      <div class="hero-copy">
        <div class="hero-eyebrow">
          <svg viewBox="0 0 24 24"><path d="M12 3c-1 5-4 8-9 9 5 1 8 4 9 9 1-5 4-8 9-9-5-1-8-4-9-9Z"/></svg>
          Photo identification for Nepal
        </div>
        <h1>Know the bird.<br>Care for its habitat.</h1>
        <p>Upload one photograph for a first clue, then explore 85 birds and the living landscapes around them.</p>
        <div class="hero-proof"><span class="proof-pill">85 selected species</span><span class="proof-pill">Responsible identification</span><span class="proof-pill">Visible model attention</span></div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

page = st.segmented_control(
    "Site section",
    ["Identify", "Explore", "Mission"],
    default="Identify",
    label_visibility="collapsed",
)

if page == "Explore":
    render_bird_guide()
    footer()
    st.stop()

if page == "Mission":
    st.markdown(
        """
        <div class="section-head compact-head">
          <div class="section-kicker">Technology with a reason</div>
          <h2>Recognition can begin a relationship</h2>
          <p>This project makes ecological AI approachable without pretending that software can replace field knowledge.</p>
        </div>
        <div class="purpose-panel">
          <div class="result-label">Our purpose</div>
          <h2>From a photograph to deeper attention</h2>
          <p>The research behind this prototype studied fine-grained classification across 85 bird species and used explainable AI to make model attention visible. The website turns that technical work into a simple public learning experience.</p>
          <h3>Learn a name. Notice a habitat. Share responsibility.</h3>
          <p>A useful result should encourage observation—not end it.</p>
        </div>
        <div class="eco-grid">
          <div class="eco-card"><div class="line-icon"><svg viewBox="0 0 24 24"><path d="M3 11a8 8 0 0 1 15-4l3 4-3 4a8 8 0 0 1-15-4Z"/><circle cx="11" cy="11" r="2"/></svg></div><h3>Transparent</h3><p>Alternatives, limitations and Grad-CAM keep uncertainty visible.</p></div>
          <div class="eco-card"><div class="line-icon"><svg viewBox="0 0 24 24"><rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 18h4"/></svg></div><h3>Accessible</h3><p>A mobile-first experience brings ecological learning closer to everyday life.</p></div>
          <div class="eco-card"><div class="line-icon"><svg viewBox="0 0 24 24"><path d="M12 21c5-3 8-7 8-12-4 0-7-2-8-6-1 4-4 6-8 6 0 5 3 9 8 12Z"/><path d="M12 8v8M8.5 12H12"/></svg></div><h3>Responsible</h3><p>Conservation decisions still require current data and expert verification.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    footer()
    st.stop()

st.markdown(
    """
    <div class="section-head compact-head">
      <div class="section-kicker">Identify a bird</div>
      <h2>What did you see?</h2>
      <p>Choose a clear photograph. One visible bird and a simple background usually give the strongest clue.</p>
    </div>
    <div class="upload-shell"><div><strong>Start with a photograph</strong><span>JPG, PNG or WebP · your image is not added to the training set</span></div><div class="step-chip">Step 1 of 2</div></div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a bird photograph",
    type=["jpg", "jpeg", "png", "webp"],
    help="Clear side views with the bird filling the frame usually work best.",
    key=f"bird_upload_{st.session_state.upload_version}",
    label_visibility="collapsed",
)

if uploaded_file is None:
    st.markdown(
        """
        <div class="tip-grid">
          <div class="tip-card"><div class="line-icon"><svg viewBox="0 0 24 24"><path d="M4 7h4l2-2h4l2 2h4v12H4Z"/><circle cx="12" cy="13" r="4"/></svg></div><div><strong>One bird</strong><span>A single, visible subject works best.</span></div></div>
          <div class="tip-card"><div class="line-icon"><svg viewBox="0 0 24 24"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/></svg></div><div><strong>Fill the frame</strong><span>Crop distractions when possible.</span></div></div>
          <div class="tip-card"><div class="line-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/></svg></div><div><strong>Good light</strong><span>Sharp feather detail improves the clue.</span></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    image_bytes = uploaded_file.getvalue()
    image_key = hashlib.sha256(image_bytes).hexdigest()
    if st.session_state.prediction_key != image_key:
        st.session_state.prediction_key = None
        st.session_state.prediction_results = None
        st.session_state.gradcam_key = None
        st.session_state.gradcam_images = None

    try:
        uploaded_image = Image.open(io.BytesIO(image_bytes))
        uploaded_image.load()
    except (UnidentifiedImageError, OSError):
        st.error("This file could not be read as an image. Try a different JPG, PNG or WebP.")
    else:
        photo_col, action_col = st.columns([1.45, 1], gap="medium")
        with photo_col:
            st.image(uploaded_image, caption="Your observation", use_container_width=True)
        with action_col:
            st.markdown(
                """
                <div class="action-panel"><div class="line-icon"><svg viewBox="0 0 24 24"><path d="M4 7h4l2-2h4l2 2h4v12H4Z"/><circle cx="12" cy="13" r="4"/></svg></div><h3>Ready to identify</h3><p>The trained model compares visual patterns and returns its three closest classes.</p></div>
                """,
                unsafe_allow_html=True,
            )
            identify = st.button(
                "Identify this bird",
                type="primary",
                icon=":material/photo_camera:",
                use_container_width=True,
            )

        if identify:
            if not Path(MODEL_PATH).exists():
                st.error("The model weights file is missing from the deployed repository.")
            else:
                try:
                    with st.spinner("Comparing shape, colour and texture…"):
                        st.session_state.prediction_results = predict_top_k(
                            get_model(), uploaded_image, load_class_names(), k=3
                        )
                        st.session_state.prediction_key = image_key
                except Exception as error:
                    st.error("The model could not make a prediction.")
                    with st.expander("Technical details"):
                        st.exception(error)

        results = st.session_state.prediction_results if st.session_state.prediction_key == image_key else None
        if results:
            best = results[0]
            _, common_name, scientific_name = split_class_name(best["raw_name"])
            status, note = confidence_details(best["confidence"])
            confidence_percent = best["confidence"] * 100

            st.markdown(
                '<div class="section-head"><div class="section-kicker">Your result</div><h2>Closest visual match</h2></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <article class="result-card">
                  <div><div class="result-label">Top suggestion</div><h2>{html.escape(common_name)}</h2><div class="result-latin">{html.escape(scientific_name)}</div></div>
                  <div class="score-block"><span class="score-number">{confidence_percent:.1f}%</span><span class="score-status">{status}</span></div>
                  <div class="score-note">{note} This is a model score, not a guaranteed real-world probability.</div>
                </article>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("#### Also compare")
            for result in results[1:]:
                _, other_common, other_scientific = split_class_name(result["raw_name"])
                st.markdown(
                    f'<div class="alt-card"><div><span class="alt-name">{html.escape(other_common)}</span><span class="alt-latin">{html.escape(other_scientific)}</span></div><span class="alt-score">{result["confidence"] * 100:.1f}%</span></div>',
                    unsafe_allow_html=True,
                )
                st.progress(result["confidence"])

            st.markdown(
                '<div class="notice"><strong>Keep field judgment in the loop.</strong> The model must choose among 85 classes, even for an unsupported species or a non-bird image.</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="section-head"><div class="section-kicker">Explain the clue</div><h2>What influenced the model?</h2><p>Grad-CAM highlights the regions that contributed most to the top suggestion.</p></div>',
                unsafe_allow_html=True,
            )
            explain = st.toggle(
                "Show attention map",
                value=False,
                help="An attention map helps inspect the model but does not prove the identification is correct.",
            )
            if explain:
                if st.session_state.gradcam_key != image_key:
                    try:
                        with st.spinner("Tracing visual attention…"):
                            heatmap, overlay, _ = make_gradcam_images(
                                get_model(), uploaded_image, class_index=best["index"]
                            )
                            st.session_state.gradcam_images = (heatmap, overlay)
                            st.session_state.gradcam_key = image_key
                    except Exception as error:
                        st.error("The attention map could not be generated for this image.")
                        with st.expander("Technical details"):
                            st.exception(error)
                if st.session_state.gradcam_images:
                    heatmap, overlay = st.session_state.gradcam_images
                    heat_col, overlay_col = st.columns(2, gap="medium")
                    with heat_col:
                        st.image(heatmap, caption="Model activation", use_container_width=True)
                    with overlay_col:
                        st.image(overlay, caption="Attention on your photo", use_container_width=True)
                    st.caption("Warmer colours indicate stronger influence. They do not confirm that the model used biologically meaningful field marks.")

            st.write("")
            st.button(
                "Identify another bird",
                icon=":material/refresh:",
                on_click=clear_identification,
                use_container_width=True,
            )

st.markdown(
    """
    <div class="section-head">
      <div class="section-kicker">Birds and landscapes</div>
      <h2>Identification is only the beginning</h2>
      <p>Good identification leads back to the living landscape: where the bird was, what it was doing, and what changed around it.</p>
    </div>
    <div class="eco-grid">
      <div class="eco-card"><div class="line-icon"><svg viewBox="0 0 24 24"><path d="M12 21V10M12 14c-5 0-8-3-8-8 5 0 8 3 8 8ZM12 11c4 0 7-2.5 7-7-4 0-7 2.5-7 7Z"/></svg></div><h3>Notice habitat</h3><p>Record forest, farmland, river or wetland—not only the species name.</p></div>
      <div class="eco-card"><div class="line-icon"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5M8 11h6M11 8v6"/></svg></div><h3>Look closer</h3><p>Compare shape, bill, plumage, behaviour and season before deciding.</p></div>
      <div class="eco-card"><div class="line-icon"><svg viewBox="0 0 24 24"><path d="M4 13c3-5 7-8 14-9-1 7-4 11-9 13"/><path d="M4 20c2-5 6-9 12-12"/></svg></div><h3>Leave no disturbance</h3><p>Keep distance, protect nests and let wild birds remain wild.</p></div>
    </div>
    """,
    unsafe_allow_html=True,
)
footer()
