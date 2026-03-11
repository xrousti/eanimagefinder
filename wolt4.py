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
        
        # 1. Trim whitespace
        bg = Image.new(img.mode, img.size, (255, 255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        # 2. Scale to fit (90% for professional padding)
        img.thumbnail((int(target_size[0] * 0.90), int(target_size[1] * 0.90)), Image.Resampling.LANCZOS)
        
        # 3. Create white canvas
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        
        # 4. Center
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        
        return canvas
    except:
        return None

# --- CALLBACK FUNCTIONS (This fixes the double-click error) ---
def save_and_next(ean, img_url):
    if not img_url:
        st.error("Please paste a URL first!")
        return

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(img_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            final_img = process_to_wolt_spec(resp.content)
            if final_img:
                # Save to state
                st.session_state.processed_images[ean] = final_img
                # Increment index
                if st.session_state.current_index < len(st.session_state.ean_list) - 1:
                    st.session_state.current_index += 1
                else:
                    st.toast("✅ Last item processed!", icon="🎉")
            else:
                st.error("Processing failed for this image.")
        else:
            st.error(f"Download failed (Status {resp.status_code})")
    except Exception as e:
        st.error(f"Error: {e}")

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
    raw_input = st.text_area("Paste EAN list:", height=200, placeholder="5060079654738\n5060708600341")
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
            file_name="wolt_images.zip",
            mime="application/zip",
            use_container_width=True
        )

# --- MAIN WORKSTATION ---
st.title("🚀 EAN Image Processor")

if not st.session_state.ean_list:
    st.info("Paste EANs in the sidebar to begin.")
else:
    current_ean = st.session_state.ean_list[st.session_state.current_index]
    
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader(f"Current: `{current_ean}`")
        
        # 1. Search Link
        search_url = f"https://www.google.com/search?tbm=isch&q={current_ean}"
        st.link_button(f"🔍 Search Google Images for {current_ean}", search_url)
        
        # 2. Use a Form to group the URL and the Save button
        # This prevents the page from refreshing until you submit the form
        with st.form(key=f"form_{current_ean}", clear_on_submit=True):
            img_url = st.text_input("Paste 'Image Address' here:")
            submit_button = st.form_submit_button(label="✅ Save & Next")
            
            if submit_button:
                save_and_next(current_ean, img_url)
                st.rerun()

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
        # Show a preview of the PREVIOUSLY saved image for this EAN if it exists
        if current_ean in st.session_state.processed_images:
            st.write("✅ Currently saved image:")
            st.image(st.session_state.processed_images[current_ean])
        else:
            st.write("⏳ No image saved for this EAN yet.")