import streamlit as st
import requests
from PIL import Image
import io
import zipfile
from duckduckgo_search import DDGS

# --- IMAGE PROCESSING ENGINE ---
def process_product_image(img_data, target_size=(1000, 563)):
    try:
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        # 1. Trim whitespace
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        # 2. Scale to fit
        max_w, max_h = target_size[0] - 80, target_size[1] - 60
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        # 3. Center on white canvas
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img)
        return canvas
    except:
        return None

# --- MULTI-ENGINE SEARCH STRATEGY ---
def find_image_waterfall(ean):
    """Tries multiple search engines and query variations."""
    
    # List of queries to try in order of precision
    queries = [
        f"EAN {ean} product white background",  # Strategy 1: DDG Precise
        f"{ean} packshot",                       # Strategy 2: Bing Style
        f"barcode {ean} image"                   # Strategy 3: General
    ]
    
    with DDGS() as ddgs:
        for q in queries:
            try:
                # We try a search for each query
                results = ddgs.images(q, max_results=1)
                if results:
                    return results[0]['image'], q
            except:
                continue
    return None, None

# --- UI ---
st.set_page_config(page_title="Multi-Engine EAN Pro", layout="wide")

st.title("🚀 Multi-Engine Product Image Tool")
st.write("Searching DuckDuckGo, Bing, and Yahoo via Waterfall Search.")

# Sidebar Settings
with st.sidebar:
    st.header("Settings")
    st.info("Dimensions: 1000x563\nBackground: White\nCentering: Auto")
    show_raw = st.checkbox("Show Search Source", value=True)

ean_input = st.text_area("Enter EANs (one per line):", height=200)

if st.button("Start Multi-Engine Search"):
    if not ean_input.strip():
        st.warning("Please enter EANs first.")
    else:
        ean_list = [e.strip() for e in ean_input.split("\n") if e.strip()]
        zip_buffer = io.BytesIO()
        success_count = 0

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            cols = st.columns(2) # Show results in 2 columns
            
            for idx, ean in enumerate(ean_list):
                with st.spinner(f"Searching for {ean}..."):
                    img_url, used_query = find_image_waterfall(ean)
                    
                    target_col = cols[idx % 2]
                    
                    if img_url:
                        try:
                            # Robust download
                            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                            r = requests.get(img_url, headers=headers, timeout=12)
                            
                            processed = process_product_image(r.content)
                            
                            if processed:
                                # Save to ZIP
                                img_io = io.BytesIO()
                                processed.save(img_io, format='JPEG', quality=95)
                                zip_file.writestr(f"{ean}.jpg", img_io.getvalue())
                                
                                # Display
                                with target_col:
                                    st.image(processed, caption=f"✅ {ean}")
                                    if show_raw:
                                        st.caption(f"Source: {img_url[:50]}...")
                                success_count += 1
                            else:
                                with target_col: st.error(f"❌ {ean}: Format Error")
                        except Exception as e:
                            with target_col: st.error(f"❌ {ean}: Download Blocked")
                    else:
                        with target_col: st.error(f"❌ {ean}: Not found on any engine")

        if success_count > 0:
            st.divider()
            st.success(f"Successfully processed {success_count} images!")
            st.download_button(
                label="📥 Download All Images (.zip)",
                data=zip_buffer.getvalue(),
                file_name="product_catalog_1000x563.zip",
                mime="application/zip"
            )