import streamlit as st
import requests
from PIL import Image
import io
import zipfile
from duckduckgo_search import DDGS
import time

# --- IMAGE PROCESSING ---
def process_product_image(img_data, target_size=(1000, 563)):
    try:
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        
        # 1. Trim whitespace
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        
        # 2. Scale to fit (1000x563)
        # Leave a safety margin of 60px
        max_w, max_h = target_size[0] - 120, target_size[1] - 80
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        
        # 3. Create white background
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        
        # 4. Center the product
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img)
        
        return canvas
    except:
        return None

# --- PRODUCT IDENTIFIER ---
def get_product_name_from_ean(ean):
    """Gets the actual product name so we don't search with just numbers."""
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{ean}.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 1:
                return data["product"].get("product_name", "")
    except:
        pass
    return ""

# --- SMART SEARCH ENGINE ---
def search_for_high_quality_image(ean):
    # Try to get the name first
    product_name = get_product_name_from_ean(ean)
    
    # If we found a name, search for the name. If not, fallback to EAN.
    if product_name:
        query = f"{product_name} packshot white background"
        st.write(f"🔍 Searching for: **{product_name}**")
    else:
        query = f"EAN {ean} product marketing image"
        st.write(f"🔍 Searching by EAN only: **{ean}**")

    try:
        with DDGS() as ddgs:
            # We look for 'Large' images specifically
            results = ddgs.images(
                query,
                region="wt-wt",
                safesearch="off",
                size="Large", 
                max_results=5
            )
            return [r['image'] for r in results] if results else []
    except:
        return []

# --- UI ---
st.set_page_config(page_title="Smart EAN Pro", layout="wide")
st.title("📦 Smart EAN Product Finder")
st.write("Converts EANs to Product Names, then finds professional high-res packshots.")

ean_input = st.text_area("Enter EANs (one per line):", height=150)

if st.button("Generate Images"):
    if not ean_input.strip():
        st.warning("Please enter EANs.")
    else:
        ean_list = [e.strip() for e in ean_input.split("\n") if e.strip()]
        zip_buffer = io.BytesIO()
        success_count = 0

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            cols = st.columns(3)
            
            for idx, ean in enumerate(ean_list):
                with st.spinner(f"Processing {ean}..."):
                    image_urls = search_for_high_quality_image(ean)
                    
                    found = False
                    for url in image_urls:
                        try:
                            headers = {"User-Agent": "Mozilla/5.0"}
                            r = requests.get(url, headers=headers, timeout=10)
                            
                            # Basic check: is the file large enough to be a real image?
                            if len(r.content) < 10000: continue 

                            processed = process_product_image(r.content)
                            if processed:
                                img_io = io.BytesIO()
                                processed.save(img_io, format='JPEG', quality=95)
                                zip_file.writestr(f"{ean}.jpg", img_io.getvalue())
                                
                                with cols[success_count % 3]:
                                    st.image(processed, caption=f"✅ {ean}")
                                
                                success_count += 1
                                found = True
                                break 
                        except:
                            continue
                    
                    if not found:
                        st.error(f"❌ {ean}: No suitable image found.")
                
                # Small delay to prevent search engine blocks
                time.sleep(1)

        if success_count > 0:
            st.success(f"Successfully processed {success_count} images!")
            st.download_button("📥 Download All (.zip)", zip_buffer.getvalue(), "catalog_images.zip")