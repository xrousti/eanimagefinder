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
        # 2. Scale to fit within 1000x563 with 10% padding
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
if 'processed' not in st.session_state: st.session_state.processed = {} 

# --- SIDEBAR ---
with st.sidebar:
    st.title("📋 Queue")
    raw = st.text_area("Paste EANs (one per line):", height=150)
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
    
    # 1. Header & Search
    st.write(f"### Item {st.session_state.current_idx + 1} of {len(st.session_state.ean_list)}")
    st.header(f"Target EAN: `{ean}`")
    
    google_url = f"https://www.google.com/search?tbm=isch&q={ean}"
    st.link_button(f"🔍 Search Google Images for {ean}", google_url)
    
    # 2. Input (No form, direct response)
    img_url = st.text_input("Paste 'Image Address' here:", key=f"url_{ean}")

    if img_url:
        # Automatic processing as soon as URL is pasted
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(img_url, headers=headers, timeout=10)
            preview = process_to_spec(r.content)
            
            if preview:
                # Big clear preview
                st.image(preview, caption="Final Output Preview (1000x563 Centered)")
                
                # Big prominent button
                if st.button("✅ SAVE & GO TO NEXT", type="primary", use_container_width=True):
                    st.session_state.processed[ean] = preview
                    if st.session_state.current_idx < len(st.session_state.ean_list) - 1:
                        st.session_state.current_idx += 1
                    else:
                        st.balloons()
                        st.success("All items complete! Click 'Download ZIP' in the sidebar.")
                    st.rerun()
            else:
                st.error("Invalid image link. Please try another one.")
        except Exception as e:
            st.error("Could not load image. Make sure you copied the 'Image Address'.")
    
    # 3. Simple Nav
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back"):
        if st.session_state.current_idx > 0:
            st.session_state.current_idx -= 1
            st.rerun()
    if col2.button("Skip Item ➡️"):
        if st.session_state.current_idx < len(st.session_state.ean_list) - 1:
            st.session_state.current_idx += 1
            st.rerun()