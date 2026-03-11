import streamlit as st
from PIL import Image, ImageChops
import requests
import io
import zipfile

# --- SETTINGS ---
TARGET_SIZE = (1000, 563)
WHITE = (255, 255, 255)

# --- IMAGE PROCESSING ---
def process_to_spec(img_content):
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        # 1. Trim whitespace
        bg = Image.new(img.mode, img.size, (255, 255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if bbox: img = img.crop(bbox)
        # 2. Scale to fit
        img.thumbnail((TARGET_SIZE[0] - 100, TARGET_SIZE[1] - 60), Image.Resampling.LANCZOS)
        # 3. Canvas
        canvas = Image.new("RGB", TARGET_SIZE, WHITE)
        offset = ((TARGET_SIZE[0] - img.width) // 2, (TARGET_SIZE[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        return canvas
    except:
        return None

# --- INITIALIZE STATE ---
if 'ean_list' not in st.session_state: st.session_state.ean_list = []
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0
if 'processed' not in st.session_state: st.session_state.processed = {} # {ean: PIL_Image}

# --- SIDEBAR ---
with st.sidebar:
    st.title("📋 Queue")
    raw = st.text_area("Paste EANs:", height=150)
    if st.button("Start / Reset Queue"):
        st.session_state.ean_list = [e.strip() for e in raw.split("\n") if e.strip()]
        st.session_state.current_idx = 0
        st.session_state.processed = {}
        st.rerun()
    
    st.divider()
    st.write(f"**Progress:** {len(st.session_state.processed)} / {len(st.session_state.ean_list)}")
    
    if st.session_state.processed:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for ean, img in st.session_state.processed.items():
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=95)
                zf.writestr(f"{ean}.jpg", buf.getvalue())
        st.download_button("📥 Download ZIP Batch", zip_buf.getvalue(), "wolt_images.zip", use_container_width=True)

# --- MAIN WORKSTATION ---
st.title("🛍️ Wolt Image Station")

if not st.session_state.ean_list:
    st.info("Paste EANs in the sidebar and click 'Start'.")
else:
    ean = st.session_state.ean_list[st.session_state.current_idx]
    
    # 1. Search Action
    st.subheader(f"Current EAN: `{ean}`")
    google_url = f"https://www.google.com/search?tbm=isch&q={ean}"
    st.link_button(f"🔍 Search Google Images for {ean}", google_url)
    
    st.divider()

    # 2. Input and Preview Logic
    # We use a unique key for the text input so it resets properly
    url_key = f"url_input_{ean}"
    img_url = st.text_input("Paste 'Image Address' here:", key=url_key)

    if img_url:
        with st.status("Fetching Preview..."):
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                r = requests.get(img_url, headers=headers, timeout=10)
                preview = process_to_spec(r.content)
                if preview:
                    st.image(preview, caption="Live Preview: 1000x563, Centered, White BG")
                    
                    # 3. SAVE BUTTON (Outside of a form for 1-click response)
                    if st.button("✅ SAVE & NEXT", type="primary"):
                        st.session_state.processed[ean] = preview
                        if st.session_state.current_idx < len(st.session_state.ean_list) - 1:
                            st.session_state.current_idx += 1
                        else:
                            st.balloons()
                            st.success("All items complete!")
                        st.rerun()
                else:
                    st.error("Could not process this image type.")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Navigation
    st.divider()
    prev, empty, nxt = st.columns([1, 2, 1])
    if prev.button("⬅️ Previous"):
        if st.session_state.current_idx > 0:
            st.session_state.current_idx -= 1
            st.rerun()
    if nxt.button("Next ➡️"):
        if st.session_state.current_idx < len(st.session_state.ean_list) - 1:
            st.session_state.current_idx += 1
            st.rerun()