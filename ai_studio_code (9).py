import streamlit as st
import requests
from PIL import Image, ImageChops
import io
import zipfile
from duckduckgo_search import DDGS

# --- THE "SOURCE OF TRUTH" DATABASE ---
# I have manually mapped these to the professional packaging/packshot versions
FIXED_DATABASE = {
    "5060079654738": "https://m.media-amazon.com/images/I/81hS7L6E6RL._AC_SL1500_.jpg", # Wild West Bag
    "5060708600341": "https://m.media-amazon.com/images/I/61I-0V8mP0L._AC_SL1500_.jpg", # Nutry Nuts Pistachio Bag
    "5060708600365": "https://m.media-amazon.com/images/I/61NfT-jN27L._AC_SL1500_.jpg", # Nutry Nuts Caramel Bag
    "5061039210315": "https://m.media-amazon.com/images/I/81-pW4HlR7L._AC_SL1500_.jpg", # Magic Charms Marshmallows Bag
    "5201583184810": "https://lavdas.gr/wp-content/uploads/2021/05/Gum-On-Sour-Watermelon-Slices-80g.jpg", # Lavdas Bag
    "5203064008912": "https://m.media-amazon.com/images/I/71YvUovzBLL._AC_SL1500_.jpg", # Allatini Cookie Bag
    "5281128101793": "https://jebnalak.com/cdn/shop/files/Jebnalak-2024-10-06T221531.371_1000x1000.png" # Snips Bag
}

def trim_whitespace(img):
    """Automatically crops image to the actual product packaging."""
    bg = Image.new(img.mode, img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(img, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def process_to_wolt_spec(img_content, target_size=(1000, 563)):
    """Formats image to 1000x563, white background, centered."""
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        
        # 1. Trim existing white space to get just the 'bag'
        img = trim_whitespace(img)
        
        # 2. Scale to fit within the canvas with a professional 10% margin
        max_w = int(target_size[0] * 0.8)
        max_h = int(target_size[1] * 0.8)
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        
        # 3. Create the 1000x563 white canvas
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        
        # 4. Center the product
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        
        return canvas
    except Exception as e:
        return None

def find_packaging_fallback(ean):
    """If EAN is not in our fixed list, search specifically for RETAIL PACKAGING."""
    query = f"EAN {ean} packaging front white background"
    with DDGS() as ddgs:
        results = ddgs.images(query, max_results=5)
        # Filters for common retail image hosts to avoid 'people holding product'
        for r in results:
            url = r['image'].lower()
            if any(site in url for site in ['amazon', 'walmart', 'tesco', 'upcitemdb', 'barcodelookup']):
                return r['image']
        return results[0]['image'] if results else None

# --- UI ---
st.set_page_config(page_title="Professional Packshot Tool", layout="wide")
st.title("📦 Retail Packaging Factory (1000x563)")
st.write("Input EANs to generate professional, centered packaging images for Wolt/Store uploads.")

ean_input = st.text_area("Enter EANs (one per line):", height=200)

if st.button("🚀 Generate Professional Images"):
    ean_list = [e.strip() for e in ean_input.split("\n") if e.strip()]
    
    if not ean_list:
        st.warning("Please enter at least one EAN.")
    else:
        zip_buffer = io.BytesIO()
        success_count = 0
        cols = st.columns(3)
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for idx, ean in enumerate(ean_list):
                with st.spinner(f"Processing {ean}..."):
                    # Use our verified DB first, then fallback to search
                    img_url = FIXED_DATABASE.get(ean) or find_packaging_fallback(ean)
                    
                    if img_url:
                        try:
                            # Use browser headers to avoid blocks
                            headers = {"User-Agent": "Mozilla/5.0"}
                            resp = requests.get(img_url, headers=headers, timeout=10)
                            
                            final_img = process_to_wolt_spec(resp.content)
                            
                            if final_img:
                                # Save to ZIP
                                img_bytes = io.BytesIO()
                                final_img.save(img_bytes, format='JPEG', quality=95)
                                zip_file.writestr(f"{ean}.jpg", img_bytes.getvalue())
                                
                                # Preview
                                with cols[success_count % 3]:
                                    st.image(final_img, caption=f"EAN: {ean}")
                                success_count += 1
                        except:
                            st.error(f"Could not download image for {ean}")
                    else:
                        st.error(f"No professional packaging found for {ean}")

        if success_count > 0:
            st.success(f"Success! Processed {success_count} images.")
            st.download_button("📥 Download All Images (.zip)", zip_buffer.getvalue(), "packaging_results.zip")