import streamlit as st
from PIL import Image, ImageChops
import requests
import io
import zipfile

# --- PAGE CONFIG ---
st.set_page_config(page_title="Wolt Image Dashboard", layout="wide")

# --- IMAGE PROCESSING LOGIC ---
def process_to_wolt_spec(img_content, target_size=(1000, 563)):
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        
        # 1. Trim whitespace
        bg = Image.new(img.mode, img.size, (255, 255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        # 2. Scale to fit (85% of canvas size for professional padding)
        img.thumbnail((int(target_size[0] * 0.85), int(target_size[1] * 0.85)), Image.Resampling.LANCZOS)
        
        # 3. Create white canvas
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        
        # 4. Center the product
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        
        return canvas
    except Exception as e:
        st.error(f"Processing error: {e}")
        return None

# --- SESSION STATE INITIALIZATION ---
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = {} # Stores EAN: PIL Image
if 'ean_list' not in st.session_state:
    st.session_state.ean_list = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# --- SIDEBAR: INPUT & QUEUE ---
with st.sidebar:
    st.title("📦 Queue Management")
    raw_input = st.text_area("Paste EANs (one per line):", height=200)
    if st.button("Start New Session"):
        st.session_state.ean_list = [e.strip() for e in raw_input.split("\n") if e.strip()]
        st.session_state.current_index = 0
        st.session_state.processed_images = {}
        st.rerun()

    st.write("---")
    st.write(f"Done: {len(st.session_state.processed_images)} / {len(st.session_state.ean_list)}")
    
    if st.session_state.processed_images:
        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for ean, img in st.session_state.processed_images.items():
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                zip_file.writestr(f"{ean}.jpg", img_byte_arr.getvalue())
        
        st.download_button(
            label="📥 Download ZIP Batch",
            data=zip_buffer.getvalue(),
            file_name="wolt_images_batch.zip",
            mime="application/zip",
            use_container_width=True
        )

# --- MAIN INTERFACE ---
st.title("🛍️ Wolt Image Workstation")

if not st.session_state.ean_list:
    st.info("Paste EANs in the sidebar to start.")
else:
    current_ean = st.session_state.ean_list[st.session_state.current_index]
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(f"Current EAN: `{current_ean}`")
        st.write(f"Item {st.session_state.current_index + 1} of {len(st.session_state.ean_list)}")
        
        # Search Link
        search_url = f"https://www.google.com/search?q={current_ean}+product+packaging+white+background&tbm=isch"
        st.link_button(f"🔍 Search Google for {current_ean}", search_url)
        
        # URL Input
        img_url = st.text_input("Paste 'Image Address' here:", key=f"input_{current_ean}")
        
        if img_url:
            try:
                # Add headers to avoid some site blocks
                resp = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if resp.status_code == 200:
                    preview_img = process_to_wolt_spec(resp.content)
                    if preview_img:
                        st.session_state.temp_img = preview_img
                        st.image(preview_img, caption="Live Preview (1000x563 Centered)")
                        
                        if st.button("✅ Add to Batch & Next"):
                            st.session_state.processed_images[current_ean] = st.session_state.temp_img
                            if st.session_state.current_index < len(st.session_state.ean_list) - 1:
                                st.session_state.current_index += 1
                                st.rerun()
                            else:
                                st.success("All items in queue processed!")
                else:
                    st.error("Could not download image. Try a different image link.")
            except:
                st.error("Invalid URL. Please right-click an image and select 'Copy Image Address'.")

    with col2:
        st.subheader("Navigation")
        n_col1, n_col2 = st.columns(2)
        if n_col1.button("⬅️ Previous"):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
                st.rerun()
        if n_col2.button("Next ➡️"):
            if st.session_state.current_index < len(st.session_state.ean_list) - 1:
                st.session_state.current_index += 1
                st.rerun()
        
        st.write("---")
        st.write("### Instructions")
        st.markdown("""
        1. Click the **Search** button.
        2. Find a high-quality packaging image.
        3. **Right-click** it and select **'Copy Image Address'**.
        4. Paste it here. 
        5. Verify the preview (it will be auto-centered and resized).
        6. Click **Add to Batch**.
        """)