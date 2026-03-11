import streamlit as st
import requests
from PIL import Image
import io
import zipfile
import time
from duckduckgo_search import DDGS

# --- SETTINGS ---
TARGET_SIZE = (1000, 563)
WHITE = (255, 255, 255)

def process_image(img_content):
    """Formats image to 1000x563 centered on white."""
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        # 1. Trim whitespace
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        # 2. Scale to fit (leaving a margin)
        img.thumbnail((TARGET_SIZE[0] - 80, TARGET_SIZE[1] - 80), Image.Resampling.LANCZOS)
        # 3. Create canvas and center
        canvas = Image.new("RGB", TARGET_SIZE, WHITE)
        offset = ((TARGET_SIZE[0] - img.width) // 2, (TARGET_SIZE[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        return canvas
    except:
        return None

def find_image_url(ean):
    """Waterfall search for EAN images."""
    # Source A: Open Food Facts (Reliable/No Blocks)
    try:
        off_url = f"https://world.openfoodfacts.org/api/v0/product/{ean}.json"
        res = requests.get(off_url, timeout=5).json()
        if res.get("status") == 1:
            url = res["product"].get("image_url")
            if url: return url
    except:
        pass

    # Source B: DuckDuckGo Search (Bypasses most single-site blocks)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{ean} product white background", max_results=2))
            if results:
                return results[0]['image']
    except:
        pass
    
    return None

# --- UI ---
st.set_page_config(page_title="EAN Image Pro", layout="wide")
st.title("📸 EAN Image Factory (Robust Mode)")
st.write("Automatically finding and formatting images to **1000x563** centered on white.")

input_eans = st.text_area("Paste EANs (one per line):", height=150)

if st.button("🚀 Find and Process Images"):
    ean_list = [e.strip() for e in input_eans.split("\n") if e.strip()]
    
    if not ean_list:
        st.warning("Please enter EANs.")
    else:
        zip_buffer = io.BytesIO()
        success_count = 0
        cols = st.columns(3)
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for idx, ean in enumerate(ean_list):
                with st.spinner(f"Finding {ean}..."):
                    img_url = find_image_url(ean)
                    
                    if img_url:
                        try:
                            # Use browser headers to bypass blocks
                            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                            img_res = requests.get(img_url, headers=headers, timeout=10)
                            
                            processed = process_image(img_res.content)
                            if processed:
                                # Save to ZIP
                                buf = io.BytesIO()
                                processed.save(buf, format='JPEG', quality=95)
                                zip_file.writestr(f"{ean}.jpg", buf.getvalue())
                                
                                # Display
                                with cols[success_count % 3]:
                                    st.image(processed, caption=f"EAN: {ean}")
                                success_count += 1
                                continue
                        except:
                            pass
                    
                    st.error(f"❌ Failed to find/download: {ean}")
                # Small sleep to prevent bot detection
                time.sleep(0.5)

        if success_count > 0:
            st.success(f"Successfully processed {success_count} images!")
            st.download_button("📥 Download All (.zip)", zip_buffer.getvalue(), "ean_images.zip")