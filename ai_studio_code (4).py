import streamlit as st
import requests
from PIL import Image
import io
import zipfile
import time
import random
from duckduckgo_search import DDGS

# --- ADVANCED IMAGE PROCESSING ---
def process_product_image(img_data, target_size=(1000, 563)):
    try:
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        
        # Scale with a 10% safety margin
        max_w, max_h = int(target_size[0] * 0.9), int(target_size[1] * 0.9)
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img)
        return canvas
    except:
        return None

# --- ROBUST SEARCH ENGINE ---
def search_ean(ean):
    """Searches using multiple strategies to bypass bot blocks."""
    # List of different query styles to try
    queries = [
        f"{ean} product image",
        f"barcode {ean} packshot",
        f"EAN {ean}"
    ]
    
    # List of real-looking User-Agents
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]

    for query in queries:
        try:
            # Add a small random delay to look human
            time.sleep(random.uniform(1.0, 2.5))
            
            with DDGS() as ddgs:
                # We specify a region (wt-wt is global) to help bypass blocks
                results = ddgs.images(
                    keywords=query,
                    region="wt-wt",
                    safesearch="off",
                    max_results=3 # Get top 3, we'll try to download the best one
                )
                
                if results:
                    # Return the list of potential URLs
                    return [r['image'] for r in results]
        except Exception as e:
            continue # Try next query if this one fails/is blocked
            
    return []

# --- UI ---
st.set_page_config(page_title="EAN Pro Fix", layout="wide")
st.title("📦 EAN Image Finder (Robust Version)")
st.write("If this fails on the web, try running it **locally** on your computer where your IP is not blocked.")

ean_input = st.text_area("Enter EANs:", height=150, placeholder="5201583184810\n5060079654738")

if st.button("Start Search"):
    if not ean_input.strip():
        st.warning("Please enter EANs.")
    else:
        ean_list = [e.strip() for e in ean_input.split("\n") if e.strip()]
        zip_buffer = io.BytesIO()
        success_count = 0

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            cols = st.columns(3)
            
            for idx, ean in enumerate(ean_list):
                with st.spinner(f"Searching for {ean}..."):
                    image_urls = search_ean(ean)
                    
                    found = False
                    if image_urls:
                        # Try the result URLs until one works
                        for url in image_urls:
                            try:
                                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                                r = requests.get(url, headers=headers, timeout=8)
                                processed = process_product_image(r.content)
                                
                                if processed:
                                    img_io = io.BytesIO()
                                    processed.save(img_io, format='JPEG', quality=95)
                                    zip_file.writestr(f"{ean}.jpg", img_io.getvalue())
                                    
                                    with cols[success_count % 3]:
                                        st.image(processed, caption=f"EAN: {ean}")
                                    
                                    success_count += 1
                                    found = True
                                    break # Stop trying URLs for this EAN
                            except:
                                continue
                    
                    if not found:
                        st.error(f"Could not find or download image for {ean}")

        if success_count > 0:
            st.success(f"Processed {success_count} images!")
            st.download_button("📥 Download ZIP", zip_buffer.getvalue(), "images.zip")