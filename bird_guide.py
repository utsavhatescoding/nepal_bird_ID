import html
import re

import requests
import streamlit as st

from bird_catalog import ORDER_STORIES, STATUS_NAMES, build_catalog
from model_utils import load_class_names


COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def _plain_text(value):
    value = html.unescape(value or "")
    return re.sub(r"<[^>]+>", "", value).strip()


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_commons_photo(scientific_name, common_name):
    """Find one attributed Wikimedia Commons photo, with a safe fallback."""
    headers = {"User-Agent": "NepalBirdID/1.0 (educational biodiversity prototype)"}
    blocked_words = ("map", "range", "distribution", "egg", "skull", "stamp", "museum", "specimen", "skin")

    for query in (scientific_name, common_name):
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f'"{query}" filetype:bitmap',
            "gsrnamespace": 6,
            "gsrlimit": 8,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": 1000,
            "format": "json",
            "formatversion": 2,
            "origin": "*",
        }
        try:
            response = requests.get(COMMONS_API, params=params, headers=headers, timeout=8)
            response.raise_for_status()
            pages = response.json().get("query", {}).get("pages", [])
        except (requests.RequestException, ValueError):
            continue

        for page in pages:
            title = page.get("title", "").lower()
            info = (page.get("imageinfo") or [{}])[0]
            if any(word in title for word in blocked_words):
                continue
            if info.get("mime") not in {"image/jpeg", "image/png", "image/webp"}:
                continue
            metadata = info.get("extmetadata", {})
            artist = _plain_text(metadata.get("Artist", {}).get("value")) or "Wikimedia contributor"
            licence = _plain_text(metadata.get("LicenseShortName", {}).get("value")) or "See source licence"
            licence_url = metadata.get("LicenseUrl", {}).get("value", "")
            page_url = info.get("descriptionurl", "")
            return {
                "url": info.get("thumburl") or info.get("url"),
                "artist": artist[:120],
                "licence": licence[:80],
                "licence_url": licence_url,
                "source_url": page_url,
            }
    return None


def _status_pill(code, label):
    css_class = f"status-{code.lower()}" if code != "-" else "status-none"
    visible = code if code != "-" else "—"
    return f'<span class="status-pill {css_class}" title="{html.escape(STATUS_NAMES[code])}">{label} {visible}</span>'


def render_bird_guide():
    catalog = build_catalog(load_class_names())
    orders = sorted({bird["order"] for bird in catalog})
    threatened_nepal = sum(bird["nepal_status"] != "-" for bird in catalog)

    st.markdown(
        """
        <div class="section-head compact-head">
          <div class="section-kicker">Learn · Notice · Care</div>
          <h2>Meet the 85 birds</h2>
          <p>Explore the exact species known by this model, then follow the taxonomy to understand how they relate.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3)
    a.metric("Species in model", len(catalog))
    b.metric("Taxonomic orders", len(orders))
    c.metric("Nepal-listed in report", threatened_nepal, help="VU, EN or CR in the report's national status field")

    st.markdown("### Open a bird profile")
    search = st.text_input("Search birds", placeholder="Try monal, vulture, owl…", label_visibility="collapsed")
    selected_order = st.selectbox("Filter by order", ["All orders", *orders])

    filtered = catalog
    if search.strip():
        needle = search.casefold().strip()
        filtered = [
            bird for bird in filtered
            if needle in bird["common_name"].casefold() or needle in bird["scientific_name"].casefold()
        ]
    if selected_order != "All orders":
        filtered = [bird for bird in filtered if bird["order"] == selected_order]

    if not filtered:
        st.info("No bird matches that search and order. Clear one of the filters and try again.")
        return

    selected_name = st.selectbox(
        "Choose a species",
        [bird["common_name"] for bird in filtered],
        index=0,
    )
    bird = next(item for item in filtered if item["common_name"] == selected_name)
    photo = fetch_commons_photo(bird["scientific_name"], bird["common_name"])

    image_col, detail_col = st.columns([1.25, 1], gap="large")
    with image_col:
        if photo and photo.get("url"):
            st.image(photo["url"], use_container_width=True)
            credit = html.escape(photo["artist"])
            source = photo.get("source_url") or photo.get("licence_url")
            if source:
                st.caption(f"Photo: {credit} · {photo['licence']} · [View source]({source})")
            else:
                st.caption(f"Photo: {credit} · {photo['licence']}")
        else:
            st.info("A freely licensed profile photograph was not available right now.")

    with detail_col:
        st.markdown(
            f"""
            <article class="profile-card">
              <div class="result-label">Species {bird['number']:02d}</div>
              <h2>{html.escape(bird['common_name'])}</h2>
              <div class="result-latin">{html.escape(bird['scientific_name'])}</div>
              <div class="taxonomy"><span>Order</span><strong>{bird['order']}</strong></div>
              <div class="taxonomy"><span>Family</span><strong>{bird['family']}</strong></div>
              <div class="status-row">
                {_status_pill(bird['global_status'], 'Global')}
                {_status_pill(bird['nepal_status'], 'Nepal')}
              </div>
            </article>
            """,
            unsafe_allow_html=True,
        )
        story = ORDER_STORIES.get(
            bird["order"],
            ("A distinct bird lineage", "Taxonomic orders group bird families that share evolutionary history and structural traits."),
        )
        st.markdown(f"**{story[0]}**")
        st.write(story[1])

    st.markdown(
        '<div class="notice"><strong>Status note:</strong> Global and Nepal fields reproduce the project report’s table based on its cited 2022 checklist. “—” only means the species was not marked VU, EN or CR in that table. Always verify a current authoritative list before conservation use.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Browse the complete model library")
    st.caption(f"Showing {len(filtered)} of {len(catalog)} species")
    cards = []
    for item in filtered:
        threat = item["nepal_status"] if item["nepal_status"] != "-" else item["global_status"]
        threat_label = f'<span class="mini-threat">{threat}</span>' if threat != "-" else ""
        cards.append(
            f'<div class="species-row"><span class="species-number">{item["number"]:02d}</span>'
            f'<span><strong>{html.escape(item["common_name"])}</strong><small>{html.escape(item["scientific_name"])}</small></span>'
            f'<span class="species-order">{item["order"]}</span>{threat_label}</div>'
        )
    st.markdown('<div class="species-list">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    st.markdown("### Read the landscape through birds")
    st.markdown(
        """
        <div class="eco-grid">
          <div class="eco-card"><div class="eco-icon">🌳</div><h3>Habitat signals</h3><p>Changes in bird communities can prompt closer attention to forests, farms, rivers and wetlands.</p></div>
          <div class="eco-card"><div class="eco-icon">🧬</div><h3>Fine-grained diversity</h3><p>Closely related birds may differ through small field marks, calls, behaviour and range.</p></div>
          <div class="eco-card"><div class="eco-icon">📝</div><h3>Observe responsibly</h3><p>Record place, date and behaviour; keep distance and avoid disturbing nests or feeding birds.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
