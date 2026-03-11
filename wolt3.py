import streamlit as st
from PIL import Image, ImageChops
import requests
import io
import zipfile

# --- PAGE CONFIG ---
st.set_page_config(page_title="EAN Image Factory", layout="wide")

# --- IMAGE PROCESSING LOGIC ---
def process_to_wolt_spec(img_content, target_size=(1000, 563)):
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        
        # 1. Trim whitespace (crops the image to the actual product edges)
        bg = Image.new(img.mode, img.size, (255, 255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        # 2. Scale to fit (Leaving 10% padding for a professional catalog look)
        img.thumbnail((int(target_size[0] * 0.90), int(target_size[1] * 0.90)), Image.Resampling.LANCZOS)
        
        # 3. Create white canvas
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        
        # 4. Center the product
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        
        return canvas
    except Exception as e:
        st.error(f"Processing error: {e}")
        return None

# --- SESSION STATE ---
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = {} 
if 'ean_list' not in st.session_state:
    st.session_state.ean_list = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# --- SIDEBAR: INPUT & DOWNLOAD ---
with st.sidebar:
    st.title("📋 EAN Queue")
    raw_input = st.text_area("Paste EAN list here:", height=200, placeholder="5060079654738\n5060708600341")
    if st.button("Initialize Queue"):
        st.session_state.ean_list = [e.strip() for e in raw_input.split("\n") if e.strip()]
        st.session_state.current_index = 0
        st.session_state.processed_images = {}
        st.rerun()

    st.write("---")
    st.write(f"**Progress:** {len(st.session_state.processed_images)} / {len(st.session_state.ean_list)}")
    
    if st.session_state.processed_images:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for ean, img in st.session_state.processed_images.items():
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=95)
                zip_file.writestr(f"{ean}.jpg", img_byte_arr.getvalue())
        
        st.download_button(
            label="📥 Download ZIP Batch",
            data=zip_buffer.getvalue(),
            file_name="processed_ean_images.zip",
            mime="application/zip",
            use_container_width=True
        )

# --- MAIN WORKSTATION ---
st.title("🚀 EAN Image Processor")

if not st.session_state.ean_list:
    st.info("Step 1: Paste your EANs into the sidebar and click 'Initialize Queue'.")
else:
    current_ean = st.session_state.ean_list[st.session_state.current_index]
    
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader(f"Current: `{current_ean}`")
        
        # --- SEARCH BUTTON (ONLY THE EAN) ---
        search_url = f"https://www.google.com/search?tbm=isch&q={current_ean}"
        st.link_button(f"🔍 Search Google Images for {current_ean}", search_url)
        
        # --- URL INPUT ---
        img_url = st.text_input("Paste 'Image Address' here:", key=f"url_{current_ean}")
        
        if img_url:
            try:
                # Bypass basic bot protection
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(img_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    preview_img = process_to_wolt_spec(resp.content)
                    if preview_img:
                        st.image(preview_img, caption=f"Result for {current_ean} (1000x563 White Background)")
                        
                        if st.button("✅ Save & Next"):
                            st.session_state.processed_images[current_ean] = preview_img
                            if st.session_state.current_index < len(st.session_state.ean_list) - 1:
                                st.session_state.current_index += 1
                                st.rerun()
                            else:
                                st.success("Queue complete! Download your ZIP from the sidebar.")
                else:
                    st.error("Could not download image. Try a different 'Image Address'.")
            except:
                st.error("Invalid URL. Right-click the image on Google and select 'Copy Image Address'.")

    with col2:
        st.subheader("Queue Navigation")
        n1, n2 = st.columns(2)
        if n1.button("⬅️ Previous"):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
                st.rerun()
        if n2.button("Next ➡️"):
            if st.session_state.current_index < len(st.session_state.ean_list) - 1:
                st.session_state.current_index += 1
                st.rerun()
        
        st.write("---")
        st.write("### Instructions")
        st.markdown(f"""
        1. Click the search button above (Opens Google Images for `{current_ean}`).
        2. Find the best product photo.
        3. **Right-click** the image and select **'Copy Image Address'**.
        4. Paste that link into the box on the left.
        5. The tool will automatically trim, center, and resize the image to **1000x563** on a **white background**.
        6. Click **Save & Next**.
        """)