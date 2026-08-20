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

st.logo(str(LOGO_PATH), icon_image=str(LOGO_PATH), size="large")


@st.cache_resource(show_spinner="Waking up the bird model…")
def get_model():
    return build_and_load_model()


def confidence_details(confidence):
    if confidence >= 0.75:
        return "Strong match", "The model sees a clear resemblance within its 85 species."
    if confidence >= 0.50:
        return "Possible match", "Compare the alternatives and visible field marks."
    return "Uncertain suggestion", "Try a closer, sharper photo before relying on this result."


def clear_identification():
    st.session_state.upload_version += 1
    st.session_state.prediction_key = None
    st.session_state.prediction_results = None
    st.session_state.gradcam_key = None
    st.session_state.gradcam_images = None


for key, default in {
    "upload_version": 0,
    "prediction_key": None,
    "prediction_results": None,
    "gradcam_key": None,
    "gradcam_images": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


hero_data = ""
if HERO_PATH.exists():
    hero_data = base64.b64encode(HERO_PATH.read_bytes()).decode("ascii")

st.markdown(
    f"""
    <style>
    :root {{
      --forest: #12382b; --moss: #789867; --cream: #f6f4ed;
      --paper: #fffdf8; --gold: #d89b32; --ink: #17382c;
      --muted: #65756e; --line: #dce4da;
    }}
    .stApp {{background: var(--cream);}}
    .block-container {{max-width: 900px; padding: 1.1rem 1.15rem 3rem;}}
    header[data-testid="stHeader"] {{background: transparent;}}
    #MainMenu, footer {{visibility: hidden;}}
    h1, h2, h3 {{letter-spacing: -0.03em; color: var(--ink);}}
    p {{line-height: 1.62;}}
    .hero-shell {{
      min-height: 430px; border-radius: 28px; padding: 2.6rem;
      display: flex; align-items: flex-end; overflow: hidden;
      background-image: linear-gradient(90deg, rgba(7,35,26,.94) 0%, rgba(7,35,26,.72) 42%, rgba(7,35,26,.10) 74%),
        url("data:image/webp;base64,{hero_data}");
      background-size: cover; background-position: center;
      box-shadow: 0 18px 52px rgba(18,56,43,.16);
    }}
    .hero-copy {{max-width: 480px; color: #fff;}}
    .brand-pill {{display: inline-flex; gap: .45rem; align-items: center; padding: .42rem .75rem;
      border: 1px solid rgba(255,255,255,.3); border-radius: 999px; background: rgba(8,35,27,.38);
      color: #f7dfad; font-size: .78rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;}}
    .hero-copy h1 {{font-size: clamp(2.6rem, 7vw, 4.8rem); line-height: .92; margin: 1rem 0 .85rem; color: white;}}
    .hero-copy p {{font-size: 1.05rem; max-width: 430px; margin: 0; color: rgba(255,255,255,.9);}}
    .mini-trust {{display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; margin-top: 1.25rem; color: rgba(255,255,255,.78); font-size: .82rem;}}
    .section-kicker {{color: #7b5a1e; font-size: .74rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .3rem;}}
    .section-head {{margin: 2.6rem 0 1.1rem;}}
    .section-head h2 {{font-size: clamp(1.75rem, 4vw, 2.4rem); margin: 0 0 .35rem;}}
    .section-head p {{color: var(--muted); margin: 0;}}
    [data-testid="stFileUploader"] {{background: var(--paper); border: 1px solid var(--line); border-radius: 20px; padding: .45rem .85rem .2rem; box-shadow: 0 8px 30px rgba(18,56,43,.06);}}
    [data-testid="stFileUploaderDropzone"] {{border: 1.5px dashed #9caf9e; border-radius: 15px; background: #f4f8f1;}}
    .stButton > button {{border-radius: 999px; min-height: 3rem; font-weight: 750; border-width: 1px;}}
    .stButton > button[kind="primary"] {{background: var(--gold); border-color: var(--gold); color: #1f2d25;}}
    .stButton > button[kind="primary"]:hover {{background: #e3aa44; border-color: #e3aa44; color: #14231b;}}
    [data-testid="stImage"] img {{border-radius: 18px;}}
    .result-card {{background: var(--forest); color: white; padding: 1.5rem; border-radius: 22px; margin: .3rem 0 1.1rem; box-shadow: 0 14px 35px rgba(18,56,43,.14);}}
    .result-label {{font-size: .72rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: #c6d9bf;}}
    .result-card h2 {{font-size: clamp(2rem, 5vw, 3rem); line-height: 1; margin: .5rem 0 .35rem; color: white;}}
    .result-latin {{font-style: italic; color: #cbd9d3; margin-bottom: 1.2rem;}}
    .result-score {{display: flex; align-items: baseline; gap: .7rem; flex-wrap: wrap;}}
    .score-number {{font-size: 2rem; font-weight: 800; color: #f4c76e;}}
    .score-status {{font-size: .9rem; font-weight: 700;}}
    .score-note {{font-size: .84rem; color: #cbd9d3; margin-top: .25rem;}}
    .alt-card {{background: var(--paper); border: 1px solid var(--line); border-radius: 16px; padding: .9rem 1rem .45rem; margin-bottom: .65rem;}}
    .alt-name {{font-weight: 780; color: var(--ink);}}
    .alt-latin {{font-style: italic; color: var(--muted); font-size: .88rem;}}
    [data-testid="stProgress"] > div > div > div > div {{background-color: var(--gold);}}
    .notice {{background: #eef3ea; border-left: 4px solid var(--moss); border-radius: 4px 14px 14px 4px; padding: .9rem 1rem; color: #3c554a; font-size: .88rem;}}
    .eco-grid {{display: grid; grid-template-columns: repeat(3, 1fr); gap: .8rem; margin-top: 1rem;}}
    .eco-card {{background: var(--paper); border: 1px solid var(--line); border-radius: 18px; padding: 1.15rem;}}
    .eco-icon {{font-size: 1.4rem;}}
    .eco-card h3 {{font-size: 1rem; margin: .55rem 0 .25rem;}}
    .eco-card p {{font-size: .82rem; color: var(--muted); margin: 0; line-height: 1.48;}}
    .footer-note {{border-top: 1px solid var(--line); margin-top: 2.7rem; padding-top: 1.25rem; color: var(--muted); font-size: .8rem;}}
    [data-testid="stSegmentedControl"] {{margin: 1rem auto 0;}}
    [data-testid="stSegmentedControl"] > div {{background: #e6ece3; padding: .28rem; border-radius: 999px; gap: .2rem;}}
    [data-testid="stSegmentedControl"] button {{border-radius: 999px; min-height: 2.65rem; font-weight: 750;}}
    .compact-head {{margin-top: 2rem;}}
    [data-testid="stMetric"] {{background: var(--paper); border: 1px solid var(--line); border-radius: 16px; padding: .8rem 1rem;}}
    .profile-card {{background: var(--forest); color: white; padding: 1.35rem; border-radius: 20px;}}
    .profile-card h2 {{color: white; line-height: 1; font-size: 2rem; margin: .55rem 0 .25rem;}}
    .taxonomy {{display: flex; justify-content: space-between; gap: 1rem; border-top: 1px solid rgba(255,255,255,.14); padding: .65rem 0; font-size: .86rem;}}
    .taxonomy span {{color: #b9cbc4;}}
    .status-row {{display: flex; flex-wrap: wrap; gap: .45rem; margin-top: .7rem;}}
    .status-pill {{border-radius: 999px; padding: .35rem .6rem; font-size: .72rem; font-weight: 800;}}
    .status-cr {{background: #ffd7d2; color: #8c2016;}} .status-en {{background: #ffe6b6; color: #714600;}}
    .status-vu {{background: #fff3ba; color: #665100;}} .status-none {{background: #dce8df; color: #345246;}}
    .species-list {{display: grid; grid-template-columns: 1fr 1fr; gap: .55rem; margin: .8rem 0 2rem;}}
    .species-row {{display: grid; grid-template-columns: 2.1rem 1fr auto auto; align-items: center; gap: .7rem;
      padding: .8rem; background: var(--paper); border: 1px solid var(--line); border-radius: 14px;}}
    .species-number {{display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: 50%; background: #e6eee2; color: var(--forest); font-size: .72rem; font-weight: 800;}}
    .species-row strong {{display: block; color: var(--ink); font-size: .88rem; line-height: 1.2;}}
    .species-row small {{display: block; color: var(--muted); font-size: .72rem; font-style: italic; margin-top: .14rem;}}
    .species-order {{color: #728279; font-size: .66rem;}} .mini-threat {{background: #ffe1ba; color: #704713; border-radius: 999px; padding: .2rem .4rem; font-size: .65rem; font-weight: 800;}}
    .purpose-panel {{background: var(--forest); color: white; border-radius: 24px; padding: 1.7rem; margin-top: 1rem;}}
    .purpose-panel h2, .purpose-panel h3 {{color: white;}} .purpose-panel p {{color: #d5e1dc;}}
    @media (max-width: 650px) {{
      .block-container {{padding: .65rem .8rem 2rem;}}
      .hero-shell {{min-height: 520px; padding: 1.35rem; border-radius: 22px; background-position: 62% center;
        background-image: linear-gradient(0deg, rgba(7,35,26,.98) 0%, rgba(7,35,26,.78) 42%, rgba(7,35,26,.06) 72%), url("data:image/webp;base64,{hero_data}");}}
      .hero-copy h1 {{font-size: 3.25rem;}}
      .hero-copy p {{font-size: .96rem;}}
      .eco-grid {{grid-template-columns: 1fr;}}
      .species-list {{grid-template-columns: 1fr;}}
      .species-order {{display: none;}}
      [data-testid="stHorizontalBlock"] {{flex-direction: column;}}
      [data-testid="column"] {{width: 100% !important; flex: 1 1 100% !important;}}
    }}
    </style>
    <section class="hero-shell">
      <div class="hero-copy">
        <div class="brand-pill">✦ Biodiversity for everyone</div>
        <h1>Nepal<br>Bird ID</h1>
        <p>Turn a bird photograph into a thoughtful first clue—built around Nepal's extraordinary birdlife.</p>
        <div class="mini-trust"><span>◎ 85 trained species</span><span>⌁ Runs from one photo</span><span>♧ Explainable result</span></div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

page = st.segmented_control(
    "Site section",
    ["Identify", "Bird guide", "Our purpose"],
    default="Identify",
    label_visibility="collapsed",
)

if page == "Bird guide":
    render_bird_guide()
    st.markdown(
        '<div class="footer-note">Nepal Bird ID · Species metadata follows the project report; photographs are retrieved from Wikimedia Commons with source attribution.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

if page == "Our purpose":
    st.markdown(
        """
        <div class="section-head compact-head">
          <div class="section-kicker">Technology with a reason</div>
          <h2>A small tool for a bigger relationship</h2>
          <p>Nepal Bird ID is designed to make bird curiosity easier to begin—not to replace field experts, conservation organisations or careful ecological research.</p>
        </div>
        <div class="purpose-panel">
          <h2>From recognition to participation</h2>
          <p>The research behind this prototype studied fine-grained classification across 85 bird species and used explainable AI to make model attention more visible. This website translates that technical work into a welcoming public experience.</p>
          <h3>What contribution can look like</h3>
          <p>Learn a name. Notice a habitat. Record an observation. Ask a better question. Share respect for the living systems around us.</p>
        </div>
        <div class="eco-grid">
          <div class="eco-card"><div class="eco-icon">🔎</div><h3>Transparent by design</h3><p>Top alternatives, limitations and optional Grad-CAM keep uncertainty visible.</p></div>
          <div class="eco-card"><div class="eco-icon">📱</div><h3>Publicly accessible</h3><p>A mobile-first website lowers the barrier to trying ecological AI.</p></div>
          <div class="eco-card"><div class="eco-icon">🇳🇵</div><h3>Rooted in Nepal</h3><p>The model library and learning experience centre Nepal’s remarkable bird diversity.</p></div>
        </div>
        <div class="notice" style="margin-top:1rem"><strong>Responsible scope:</strong> This prototype is a learning and first-clue tool. Conservation decisions require current authoritative data and expert verification.</div>
        <div class="footer-note">Nepal Bird ID · An independent social-innovation prototype for biodiversity learning. Not affiliated with Merlin Bird ID or the Cornell Lab of Ornithology.</div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

st.markdown(
    """
    <div class="section-head">
      <div class="section-kicker">01 · Identify</div>
      <h2>Which bird did you see?</h2>
      <p>Use one clear photograph with the bird filling a good part of the frame.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a bird photograph",
    type=["jpg", "jpeg", "png", "webp"],
    help="JPG, PNG or WebP. Clear side views usually work best.",
    key=f"bird_upload_{st.session_state.upload_version}",
)

if uploaded_file is None:
    st.markdown(
        '<div class="notice">📷 No photograph is stored. Choose an image above whenever you are ready.</div>',
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
        left, right = st.columns([1.35, 1], gap="medium")
        with left:
            st.image(uploaded_image, caption="Your observation", use_container_width=True)
        with right:
            st.markdown("#### Ready to explore?")
            st.caption("The analysis runs the already-trained model. It does not retrain or add your photo to a training set.")
            identify = st.button(
                "Identify this bird",
                type="primary",
                icon=":material/photo_camera:",
                use_container_width=True,
            )

        if identify:
            if not Path(MODEL_PATH).exists():
                st.error("The model weights file is missing from the app folder.")
            else:
                try:
                    with st.spinner("Looking closely at shape, colour and texture…"):
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

            st.markdown('<div class="section-head"><div class="section-kicker">02 · Result</div><h2>Your closest match</h2></div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <article class="result-card">
                  <div class="result-label">Best model match</div>
                  <h2>{html.escape(common_name)}</h2>
                  <div class="result-latin">{html.escape(scientific_name)}</div>
                  <div class="result-score"><span class="score-number">{confidence_percent:.1f}%</span><span class="score-status">{status}</span></div>
                  <div class="score-note">{note}</div>
                </article>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("#### Other possible matches")
            for result in results[1:]:
                _, other_common, other_scientific = split_class_name(result["raw_name"])
                st.markdown(
                    f'<div class="alt-card"><span class="alt-name">{html.escape(other_common)}</span><br><span class="alt-latin">{html.escape(other_scientific)}</span></div>',
                    unsafe_allow_html=True,
                )
                st.progress(result["confidence"], text=f"{result['confidence'] * 100:.1f}% match score")

            st.markdown(
                '<div class="notice"><strong>Keep field judgment in the loop.</strong> The score is the model’s relative preference among 85 known classes—not a guarantee, and not a test for every bird found in Nepal.</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="section-head"><div class="section-kicker">03 · Explain</div><h2>See what the model noticed</h2><p>Grad-CAM highlights image regions that most influenced the top match.</p></div>',
                unsafe_allow_html=True,
            )
            explain = st.toggle(
                "Show the model attention map",
                value=False,
                help="This is an interpretation aid, not proof of correct identification.",
            )
            if explain:
                if st.session_state.gradcam_key != image_key:
                    try:
                        with st.spinner("Tracing the model’s visual attention…"):
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
                        st.image(heatmap, caption="Activation heatmap", use_container_width=True)
                    with overlay_col:
                        st.image(overlay, caption="Attention over your photo", use_container_width=True)
                    st.caption("Warmer colours indicate stronger influence on this prediction. Attention does not confirm that the model used biologically meaningful field marks.")

            st.write("")
            st.button(
                "Try another photograph",
                icon=":material/refresh:",
                on_click=clear_identification,
                use_container_width=True,
            )

st.markdown(
    """
    <div class="section-head">
      <div class="section-kicker">Why it matters</div>
      <h2>Birds make landscapes legible</h2>
      <p>Recognising the birds around us can turn everyday observations into curiosity, care and better conversations about habitat.</p>
    </div>
    <div class="eco-grid">
      <div class="eco-card"><div class="eco-icon">🌱</div><h3>Living ecosystems</h3><p>Bird communities can reflect changes across forests, farms and wetlands.</p></div>
      <div class="eco-card"><div class="eco-icon">🔭</div><h3>Closer observation</h3><p>A name is a starting point for noticing behaviour, habitat and season.</p></div>
      <div class="eco-card"><div class="eco-icon">🤝</div><h3>Shared stewardship</h3><p>Accessible tools can invite more people into Nepal’s conservation story.</p></div>
    </div>
    <div class="footer-note">Nepal Bird ID · An independent social-innovation prototype for biodiversity learning. Not affiliated with Merlin Bird ID or the Cornell Lab of Ornithology.</div>
    """,
    unsafe_allow_html=True,
)
