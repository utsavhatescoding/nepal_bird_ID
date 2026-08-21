import base64
import hashlib
import html
import io
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    if hasattr(pillow_heif, "register_avif_opener"):
        pillow_heif.register_avif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False

from bird_guide import fetch_commons_photo, render_bird_guide
from model_utils import (
    MODEL_PATH,
    build_and_load_model,
    centre_focus_crop,
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
    page_icon="🐦",
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


def navigate(section):
    st.session_state.site_page = section


def open_uploaded_image(image_bytes):
    """Decode supported formats, respect phone orientation and return RGB."""
    image = Image.open(io.BytesIO(image_bytes))
    image.seek(0)
    image.load()
    image = ImageOps.exif_transpose(image)
    if image.width * image.height > 50_000_000:
        raise ValueError("The image is too large. Please use a photo under 50 megapixels.")
    return image.convert("RGB")


def prediction_photo_card(rank, result):
    _, common_name, scientific_name = split_class_name(result["raw_name"])
    photo = fetch_commons_photo(scientific_name, common_name)
    confidence = result["confidence"] * 100
    rank_label = "Top match" if rank == 1 else f"Alternative {rank}"
    card_class = "prediction-card prediction-card-best" if rank == 1 else "prediction-card"

    if photo and photo.get("url"):
        source_url = html.escape(photo.get("source_url") or photo.get("licence_url") or "#", quote=True)
        image_html = (
            f'<a class="prediction-photo-link" href="{source_url}" target="_blank" rel="noopener">'
            f'<img class="prediction-photo" src="{html.escape(photo["url"], quote=True)}" '
            f'alt="{html.escape(common_name)}"></a>'
        )
        credit_html = (
            f'<a href="{source_url}" target="_blank" rel="noopener">'
            f'{html.escape(photo["artist"])} · {html.escape(photo["licence"])}</a>'
        )
    else:
        image_html = '<div class="prediction-photo prediction-photo-empty"><span>Photo unavailable</span></div>'
        credit_html = "Wikimedia Commons photo unavailable"

    return f"""
      <article class="{card_class}">
        <div class="prediction-image-wrap">{image_html}<span class="rank-chip">{rank_label}</span></div>
        <div class="prediction-body">
          <div class="prediction-confidence">{confidence:.1f}% model score</div>
          <h3>{html.escape(common_name)}</h3>
          <div class="prediction-latin">{html.escape(scientific_name)}</div>
          <div class="prediction-credit">Photo: {credit_html}</div>
        </div>
      </article>
    """


def contributor_card(name, role, initials, image_stem):
    image_path = next(
        (path for suffix in (".webp", ".jpg", ".jpeg", ".png")
         if (path := APP_DIR / "assets" / "contributors" / f"{image_stem}{suffix}").exists()),
        None,
    )
    if image_path:
        mime = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else f"image/{image_path.suffix.lower()[1:]}"
        image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        portrait = f'<img src="data:{mime};base64,{image_data}" alt="{html.escape(name)}">'
    else:
        portrait = f'<div class="contributor-placeholder">{html.escape(initials)}</div>'
    return (
        f'<article class="contributor-card"><div class="contributor-portrait">{portrait}</div>'
        f'<h3>{html.escape(name)}</h3><p>{html.escape(role)}</p></article>'
    )


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
    "site_page": "Identify",
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
    .stApp * {{scroll-behavior:smooth;}}
    .block-container {{max-width:1040px; padding:0 1.15rem 4rem;}}
    header[data-testid="stHeader"] {{height:0; background:transparent;}}
    #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], [data-testid="stSidebarCollapsedControl"],
    [data-testid="stLogo"],[aria-label="streamlitApp"],img[alt="streamlitApp"] { display: none !important;}
    h1,h2,h3 {{color:var(--ink); letter-spacing:-.035em;}}
    p {{line-height:1.58;}}

    .site-header {{height:74px; display:flex; align-items:center; justify-content:space-between; gap:1rem;}}
    .site-brand {{display:flex; align-items:center; gap:.75rem;}}
    .site-brand img {{width:42px; height:42px; display:block;}}
    .brand-name {{display:block; font-size:1rem; font-weight:800; letter-spacing:-.02em; color:var(--pine-950);}}
    .brand-sub {{display:block; margin-top:.08rem; font-size:.68rem; color:#71817a; letter-spacing:.09em; text-transform:uppercase; font-weight:700;}}
    .header-badge {{display:flex; align-items:center; gap:.45rem; color:var(--pine-800); font-size:.76rem; font-weight:700;}}
    .live-dot {{width:8px; height:8px; border-radius:50%; background:var(--leaf); box-shadow:0 0 0 4px rgba(78,155,88,.13);}}

    .hero-shell {{min-height:350px; border-radius:22px; overflow:hidden; position:relative; display:flex; align-items:center;
      background-image:linear-gradient(90deg,rgba(5,43,33,.98) 0%,rgba(5,43,33,.92) 38%,rgba(5,43,33,.38) 65%,rgba(5,43,33,.04) 100%),url("data:image/webp;base64,{hero_data}");
      background-size:cover; background-position:center 46%; box-shadow:0 14px 38px rgba(12,53,40,.12);}}
    .hero-copy {{width:52%; padding:2.6rem 2.7rem; color:white; position:relative; z-index:1;}}
    .hero-eyebrow {{display:flex; align-items:center; gap:.5rem; color:#cde6bf; font-size:.7rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase;}}
    .hero-eyebrow svg {{width:16px; height:16px; stroke:#9bd168;}}
    .hero-copy h1 {{font-size:clamp(2.15rem,4vw,3rem); line-height:1.04; margin:.72rem 0 .8rem; color:white; max-width:480px;}}
    .hero-copy p {{max-width:500px; margin:0; color:rgba(255,255,255,.86); font-size:.98rem;}}

    .st-key-site_nav {{max-width:520px; margin:1rem auto 0; padding:.25rem; background:transparent; border:0; position:relative; z-index:30;}}
    .st-key-site_nav [data-testid="stHorizontalBlock"] {{gap:.3rem;}}
    .st-key-site_nav .stButton > button {{min-height:2.65rem; border:0; border-radius:999px; box-shadow:none; font-size:.78rem; letter-spacing:.005em; transition:background .18s ease,color .18s ease,transform .18s ease,box-shadow .18s ease;}}
    .st-key-site_nav .stButton > button p {{font-weight:780;}}
    .st-key-site_nav .stButton > button svg {{display:none;}}
    .st-key-site_nav .stButton > button[kind="tertiary"] {{background:transparent; color:#566a60;}}
    .st-key-site_nav .stButton > button[kind="tertiary"]:hover {{background:#edf4ed; color:var(--pine-900); transform:translateY(-1px);}}
    .st-key-site_nav .stButton > button[kind="primary"] {{background:#e3eee5; color:var(--pine-900); box-shadow:inset 0 0 0 1px #cadbce;}}

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
    .prediction-grid {{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.8rem; margin:.75rem 0 1rem;}}
    .prediction-card {{overflow:hidden; background:white; border:1px solid var(--line); border-radius:17px; box-shadow:0 9px 25px rgba(12,53,40,.06); transition:transform .2s ease,box-shadow .2s ease;}}
    .prediction-card:hover {{transform:translateY(-3px); box-shadow:0 14px 30px rgba(12,53,40,.1);}}
    .prediction-card-best {{border-color:#9fc6a4; box-shadow:0 12px 30px rgba(44,116,61,.12);}}
    .prediction-image-wrap {{height:180px; position:relative; overflow:hidden; background:#e8efea;}}
    .prediction-photo-link {{display:block; width:100%; height:100%;}}
    .prediction-photo {{display:block; width:100%; height:100%; object-fit:cover; border-radius:0 !important; transition:transform .35s ease;}}
    .prediction-card:hover .prediction-photo {{transform:scale(1.025);}}
    .prediction-photo-empty {{display:grid; place-items:center; color:#6c7d74; font-size:.72rem;}}
    .rank-chip {{position:absolute; top:.65rem; left:.65rem; padding:.27rem .5rem; border-radius:999px; background:rgba(6,45,35,.9); color:white; font-size:.61rem; font-weight:820; letter-spacing:.04em;}}
    .prediction-body {{padding:.9rem;}}
    .prediction-confidence {{color:var(--leaf); font-size:.67rem; font-weight:850; letter-spacing:.04em; text-transform:uppercase;}}
    .prediction-body h3 {{font-size:1rem; line-height:1.15; margin:.35rem 0 .15rem;}}
    .prediction-latin {{font-size:.72rem; color:var(--muted); font-style:italic; min-height:2.1em;}}
    .prediction-credit {{font-size:.57rem; color:#829088; margin-top:.62rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}
    .prediction-credit a {{color:inherit; text-decoration:none;}}
    .prediction-credit a:hover {{text-decoration:underline;}}
    [data-testid="stProgress"] {{margin-bottom:.55rem;}}
    [data-testid="stProgress"] > div > div > div > div {{background-color:var(--leaf);}}
    .notice {{background:#edf4ed; border:1px solid #d9e7d9; border-radius:13px; padding:.82rem .9rem; color:#435a4f; font-size:.78rem; line-height:1.48;}}

    .eco-grid {{display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin-top:.9rem;}}
    .eco-card {{background:white; border:1px solid var(--line); border-radius:16px; padding:1rem;}}
    .eco-card .line-icon {{margin-bottom:.75rem;}}
    .eco-card h3 {{font-size:.93rem; margin:0 0 .25rem;}}
    .eco-card p {{font-size:.75rem; color:var(--muted); margin:0; line-height:1.48;}}
    .detail-grid {{display:grid; grid-template-columns:repeat(3,1fr); gap:.65rem; margin:.8rem 0 1rem;}}
    .detail-card {{background:white; border:1px solid var(--line); border-radius:14px; padding:.85rem;}}
    .detail-card span {{display:block; color:var(--leaf); font-size:.61rem; font-weight:850; letter-spacing:.08em; text-transform:uppercase;}}
    .detail-card strong {{display:block; color:var(--ink); font-size:.82rem; margin:.28rem 0 .18rem;}}
    .detail-card small {{display:block; color:var(--muted); font-size:.66rem; line-height:1.4;}}
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
    .mission-statement {{max-width:720px; font-size:1.02rem; color:#d5e1dc;}}
    .mission-number {{display:block; color:#b9dd83; font-size:2rem; font-weight:870; line-height:1; margin-bottom:.35rem;}}
    .contributor-grid {{display:grid; grid-template-columns:repeat(3,1fr); gap:.75rem; margin:.9rem 0 1rem;}}
    .contributor-card {{background:white; border:1px solid var(--line); border-radius:17px; padding:1rem; text-align:center;}}
    .contributor-portrait {{width:96px; height:96px; margin:0 auto .75rem; border-radius:50%; overflow:hidden; background:#e7f1e8; border:4px solid #f1f6f1; box-shadow:0 5px 16px rgba(11,59,46,.1);}}
    .contributor-portrait img {{width:100%; height:100%; object-fit:cover;}}
    .contributor-placeholder {{width:100%; height:100%; display:grid; place-items:center; background:linear-gradient(145deg,var(--pine-800),var(--leaf)); color:white; font-size:1.35rem; font-weight:850;}}
    .contributor-card h3 {{font-size:.92rem; margin:.15rem 0 .2rem;}}
    .contributor-card p {{font-size:.69rem; color:var(--muted); margin:0; line-height:1.45;}}
    .source-strip {{margin-top:.8rem; padding:.8rem .9rem; border:1px solid var(--line); border-radius:13px; background:#fbfcfa; color:var(--muted); font-size:.68rem; line-height:1.5;}}
    .source-strip a {{color:var(--pine-800); font-weight:750;}}
    .site-footer {{display:flex; justify-content:space-between; gap:1rem; align-items:flex-end; border-top:1px solid var(--line); margin-top:2.5rem; padding:1.2rem 0 .4rem; color:var(--muted); font-size:.72rem;}}
    .site-footer strong {{color:var(--pine-900); font-size:.82rem;}} .footer-note-right {{text-align:right;}}

    @media (max-width:900px) and (min-width:701px) {{
      .block-container {{padding-left:1rem; padding-right:1rem;}}
      .hero-shell {{min-height:330px; background-position:58% center;}}
      .hero-copy {{width:60%; padding:2rem;}}
      .hero-copy h1 {{font-size:2.45rem;}}
      .species-row {{grid-template-columns:1.9rem 1fr auto;}}
      .species-order {{display:none;}}
    }}

    @media (max-width:700px) {{
      .block-container {{padding:0 .8rem 5.7rem;}}
      .site-header {{height:62px;}} .site-brand img {{width:36px;height:36px;}} .brand-sub,.header-badge {{display:none;}}
      .hero-shell {{min-height:310px; align-items:flex-end; border-radius:18px; background-position:61% center;
        background-image:linear-gradient(0deg,rgba(5,43,33,.98) 0%,rgba(5,43,33,.83) 45%,rgba(5,43,33,.06) 78%),url("data:image/webp;base64,{hero_data}");}}
      .hero-copy {{width:100%; padding:1.15rem;}} .hero-copy h1 {{font-size:2rem; max-width:330px;}} .hero-copy p {{font-size:.8rem; max-width:330px; line-height:1.45;}}
      .st-key-site_nav {{max-width:none; position:fixed; left:.7rem; right:.7rem; bottom:.65rem; z-index:9999; margin:0; padding:.3rem; background:rgba(255,255,255,.96); border:1px solid #cfdcd3; border-radius:17px; box-shadow:0 12px 34px rgba(7,44,34,.22); backdrop-filter:blur(14px);}}
      .st-key-site_nav [data-testid="stHorizontalBlock"] {{flex-direction:row !important; gap:.2rem !important;}}
      .st-key-site_nav [data-testid="column"] {{width:auto !important; flex:1 1 0 !important; min-width:0 !important;}}
      .st-key-site_nav .stButton > button {{min-height:3.2rem; padding:.35rem .25rem; font-size:.72rem;}}
      .st-key-site_nav .stButton > button svg {{display:block; width:1.05rem; height:1.05rem;}}
      .st-key-site_nav .stButton > button[kind="primary"] {{background:var(--pine-900); color:white; box-shadow:none;}}
      .section-head {{margin:1.75rem 0 .85rem;}} .section-head h2 {{font-size:1.85rem;}}
      .tip-grid,.eco-grid,.species-list,.prediction-grid,.detail-grid,.contributor-grid {{grid-template-columns:1fr;}}
      .prediction-image-wrap {{height:220px;}}
      [data-testid="stHorizontalBlock"] {{flex-direction:column; gap:.45rem;}}
      [data-testid="column"] {{width:100% !important; flex:1 1 100% !important;}}
      .result-card {{grid-template-columns:1fr;}} .score-block {{text-align:left; padding:.75rem 0 0; border-left:0; border-top:1px solid rgba(255,255,255,.15);}}
      .score-note {{grid-column:1;}} .species-order {{display:none;}} .footer-note-right {{display:none;}}
    }}
    @media (max-width:420px) {{
      .block-container {{padding-left:.65rem; padding-right:.65rem;}}
      .hero-shell {{min-height:290px; border-radius:16px;}}
      .hero-copy {{padding:1.05rem;}}
      .hero-copy h1 {{font-size:1.82rem;}}
      .hero-copy p {{font-size:.75rem; line-height:1.4;}}
      .st-key-site_nav {{left:.45rem; right:.45rem; bottom:.45rem;}}
      .st-key-site_nav .stButton > button {{font-size:.66rem; min-height:3rem;}}
      .upload-shell {{grid-template-columns:1fr; gap:.5rem;}}
      .step-chip {{justify-self:start;}}
      .site-footer {{align-items:flex-start;}}
    }}
    @media (max-height:560px) and (orientation:landscape) {{
      .hero-shell {{min-height:245px;}}
      .hero-copy h1 {{font-size:2.15rem;}}
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
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.container(key="site_nav"):
    nav_items = (
        ("Identify", ":material/photo_camera:"),
        ("Explore", ":material/menu_book:"),
        ("Mission", ":material/eco:"),
    )
    nav_columns = st.columns(3, gap="small")
    for column, (label, icon) in zip(nav_columns, nav_items):
        with column:
            st.button(
                label,
                icon=icon,
                key=f"nav_{label.lower()}",
                type="primary" if st.session_state.site_page == label else "tertiary",
                on_click=navigate,
                args=(label,),
                use_container_width=True,
            )

page = st.session_state.site_page

if page == "Explore":
    render_bird_guide()
    footer()
    st.stop()

if page == "Mission":
    st.markdown(
        f"""
        <div class="section-head compact-head">
          <div class="section-kicker">AI in service of ecology</div>
          <h2>Make every identification a reason to care</h2>
          <p>Nepal Bird ID connects computer vision, ecological learning and responsible observation in one public tool.</p>
        </div>
        <div class="purpose-panel">
          <div class="result-label">Why this contribution matters</div>
          <h2>Technology should return attention to nature</h2>
          <p class="mission-statement">Birds move through forests, farms, rivers, wetlands and cities. They disperse seeds, pollinate plants, regulate insects, recycle nutrients and reveal changes in living landscapes. Recognising a bird can be the first step toward noticing the ecosystem that supports it.</p>
          <h3>Identify carefully. Learn openly. Observe responsibly.</h3>
          <p>This project does not replace ornithologists or field evidence. It makes a research model understandable, shows uncertainty, and uses Grad-CAM to expose where the model concentrated its attention.</p>
        </div>
        <div class="eco-grid">
          <div class="eco-card"><span class="mission-number">85</span><h3>Fine-grained classes</h3><p>A focused model library turns a technical ecology study into an approachable public experience.</p></div>
          <div class="eco-card"><span class="mission-number">3</span><h3>Comparable suggestions</h3><p>Showing alternatives discourages blind trust in a single label and supports closer visual comparison.</p></div>
          <div class="eco-card"><span class="mission-number">1</span><h3>Shared responsibility</h3><p>AI can support awareness; protection still depends on people, evidence and sustained conservation work.</p></div>
        </div>

        <div class="section-head">
          <div class="section-kicker">People behind the work</div>
          <h2>Contributors</h2>
          <p>Research, product development and academic guidance brought this ecological learning prototype together.</p>
        </div>
        <div class="contributor-grid">
          {contributor_card('Prajwol Karki', 'MS Knowledge Engineering · IOE Pulchowk', 'PK', 'prajwol-karki')}
          {contributor_card('Utsav Phuyal', 'Master’s in Business and Economics · KUSOM', 'UP', 'utsav-phuyal')}
          {contributor_card('Bibha SSS', 'Thesis Supervisor · IOE Pulchowk', 'BS', 'bibha-sss')}
        </div>

        <div class="source-strip"><strong>Evidence and scope:</strong> Nepal-wide figures and threatened-status fields follow the supplied taxonomy report, which describes records through 2022. Ecological-service context is supported by <a href="https://www.birdlife.org/news/2019/01/04/why-we-need-birds-far-more-than-they-need-us/" target="_blank" rel="noopener">BirdLife International</a>. Predictions are educational suggestions, not conservation assessments.</div>
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
    <div class="upload-shell"><div><strong>Start with a photograph</strong><span>JPG, PNG, WebP, HEIC, TIFF or BMP · your image is not added to the training set</span></div><div class="step-chip">Step 1 of 2</div></div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a bird photograph",
    type=["jpg", "jpeg", "jfif", "png", "webp", "heic", "heif", "bmp", "tif", "tiff"],
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
    try:
        uploaded_image = open_uploaded_image(image_bytes)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        st.error(f"This image could not be opened safely. {error}")
        if uploaded_file.name.lower().endswith((".heic", ".heif")) and not HEIF_SUPPORT:
            st.info("HEIC support requires the pillow-heif package listed in requirements.txt.")
    else:
        focus_enabled = st.toggle(
            "Focus on a centred bird",
            value=False,
            help="Optionally crops the outer edges locally. Keep this off when the bird is not near the centre.",
        )
        crop_percent = 0
        if focus_enabled:
            crop_percent = st.slider(
                "Focus strength",
                min_value=5,
                max_value=30,
                value=12,
                step=1,
                help="Higher values remove more of the outer frame. This is not AI background removal.",
            )
            st.caption(
                "Focus mode keeps your image on this server and avoids a third-party removal API. "
                "It is optional because the model was trained on normal photographs."
            )

        inference_image = centre_focus_crop(uploaded_image, crop_percent)
        image_key = hashlib.sha256(
            image_bytes + f":centre-crop:{crop_percent}".encode("utf-8")
        ).hexdigest()
        if st.session_state.prediction_key != image_key:
            st.session_state.prediction_key = None
            st.session_state.prediction_results = None
            st.session_state.gradcam_key = None
            st.session_state.gradcam_images = None

        photo_col, action_col = st.columns([1.45, 1], gap="medium")
        with photo_col:
            caption = "Focused preview used for prediction" if focus_enabled else "Your observation"
            st.image(inference_image, caption=caption, use_container_width=True)
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
                            get_model(), inference_image, load_class_names(), k=3
                        )
                        st.session_state.prediction_key = image_key
                except Exception as error:
                    st.error("The model could not make a prediction.")
                    with st.expander("Technical details"):
                        st.exception(error)

        results = st.session_state.prediction_results if st.session_state.prediction_key == image_key else None
        if results:
            best = results[0]
            status, note = confidence_details(best["confidence"])

            st.markdown(
                '<div class="section-head"><div class="section-kicker">Your result</div><h2>Three closest visual matches</h2><p>Compare the bird’s shape, bill, plumage and habitat across all three suggestions.</p></div>',
                unsafe_allow_html=True,
            )
            prediction_cards = "".join(
                 prediction_photo_card(rank, result).strip()
                   for rank, result in enumerate(results, start=1)
                   )
            st.markdown(
                f'<div class="prediction-grid">{prediction_cards}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="notice"><strong>{status}.</strong> {html.escape(note)} Scores compare only the model’s 85 trained classes; they are not guaranteed real-world probabilities. The model will still return a result for an unsupported species or non-bird image.</div>',
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
                                get_model(), inference_image, class_index=best["index"]
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
