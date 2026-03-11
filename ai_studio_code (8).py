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

def get_product_name(ean):
    """Gets the clean product name to improve search accuracy."""
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{ean}.json"
        res = requests.get(url, timeout=5).json()
        if res.get("status") == 1:
            return res["product"].get("product_name", "")
    except:
        return ""
    return ""

def process_image(img_content):
    """Formats image to 1000x563 centered on white with padding."""
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        # 1. Trim whitespace
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        # 2. Scale to fit (leaving a professional margin)
        img.thumbnail((TARGET_SIZE[0] - 120, TARGET_SIZE[1] - 80), Image.Resampling.LANCZOS)
        # 3. Create canvas and center
        canvas = Image.new("RGB", TARGET_SIZE, WHITE)
        offset = ((TARGET_SIZE[0] - img.width) // 2, (TARGET_SIZE[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        return canvas
    except:
        return None

def find_pro_image_url(ean):
    """Search for professional studio packshots only."""
    product_name = get_product_name(ean)
    
    # We build a very specific 'Professional' query
    query = f"{product_name} {ean} professional white background packshot studio"
    
    try:
        with DDGS() as ddgs:
            # We look for large, professional images
            results = list(ddgs.images(
                query, 
                max_results=5, 
                region="wt-wt", 
                size="Large", 
                type_image="photo"
            ))
            
            if results:
                # Prioritize 'clean' URLs from retail giants or barcode databases
                pro_domains = ['amazon', 'walmart', 'tesco', 'upcitemdb', 'barcodelookup', 'bigw', 'ocado']
                for r in results:
                    if any(domain in r['image'].lower() for domain in pro_domains):
                        return r['image']
                
                # Fallback to the first result if no pro domain found
                return results[0]['image']
    except:
        pass
    return None

# --- UI ---
st.set_page_config(page_title="Wolt Image Factory", layout="wide")
st.title("🛍️ Wolt-Ready Image Factory")
st.write("Generating professional **1000x563** studio packshots for your store.")

input_eans = st.text_area("Paste EANs (one per line):", height=150)

if st.button("🚀 Generate Studio Images"):
    ean_list = [e.strip() for e in input_eans.split("\n") if e.strip()]
    
    if not ean_list:
        st.warning("Please enter EANs.")
    else:
        zip_buffer = io.BytesIO()
        success_count = 0
        cols = st.columns(3)
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for idx, ean in enumerate(ean_list):
                with st.spinner(f"Finding studio shot for {ean}..."):
                    img_url = find_pro_image_url(ean)
                    
                    if img_url:
                        try:
                            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                            img_res = requests.get(img_url, headers=headers, timeout=10)
                            
                            processed = process_image(img_res.content)
                            if processed:
                                buf = io.BytesIO()
                                processed.save(buf, format='JPEG', quality=95)
                                zip_file.writestr(f"{ean}.jpg", buf.getvalue())
                                
                                with cols[success_count % 3]:
                                    st.image(processed, caption=f"EAN: {ean}")
                                success_count += 1
                                continue
                        except:
                            pass
                    
                    st.error(f"❌ Could not find a professional shot for: {ean}")
                time.sleep(1) # Human-like delay

        if success_count > 0:
            st.success(f"Successfully processed {success_count} images!")
            st.download_button("📥 Download ZIP for Wolt", zip_buffer.getvalue(), "wolt_images.zip")