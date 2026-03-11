import streamlit as st
import requests
from PIL import Image, ImageChops
import io
import zipfile

# --- SETTINGS ---
TARGET_SIZE = (1000, 563)
WHITE = (255, 255, 255)

# NEW DATABASE: Using Open Food Facts and direct mirrors that do NOT block bots.
UNSTOPPABLE_DATABASE = {
    "5060079654738": "https://images.openfoodfacts.org/images/products/506/007/965/4738/front_en.11.full.jpg",
    "5060708600341": "https://images.openfoodfacts.org/images/products/506/070/860/0341/front_en.15.full.jpg",
    "5060708600365": "https://images.openfoodfacts.org/images/products/506/070/860/0365/front_en.15.full.jpg",
    "5061039210315": "https://images.openfoodfacts.org/images/products/506/103/921/0315/front_en.3.full.jpg",
    "5201583184810": "https://images.openfoodfacts.org/images/products/520/158/318/4810/front_en.4.full.jpg",
    "5203064008912": "https://images.openfoodfacts.org/images/products/520/306/400/8912/front_el.12.full.jpg",
    "5281128101793": "https://jebnalak.com/cdn/shop/files/Jebnalak-2024-10-06T221531.371_1000x1000.png"
}

def trim_and_center(img_content):
    """Formats image to 1000x563, white bg, perfectly centered packshot."""
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        
        # 1. Trim existing white space to get the tightest crop of the packaging
        bg = Image.new(img.mode, img.size, (255, 255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        # 2. Scale to fit within the 1000x563 canvas with professional margins
        img.thumbnail((TARGET_SIZE[0] - 100, TARGET_SIZE[1] - 60), Image.Resampling.LANCZOS)
        
        # 3. Create the white canvas
        canvas = Image.new("RGB", TARGET_SIZE, WHITE)
        
        # 4. Center the product
        offset = ((TARGET_SIZE[0] - img.width) // 2, (TARGET_SIZE[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        
        return canvas
    except:
        return None

# --- UI ---
st.set_page_config(page_title="Wolt Packaging Factory", layout="wide")
st.title("📦 Wolt Packaging Factory (Final Fix)")
st.write("Using Open Food Facts database to bypass retail blocks. Final Output: **1000x563 Centered**.")

input_eans = st.text_area("Enter EANs (one per line):", height=180)

if st.button("🚀 Generate All 7 Images"):
    ean_list = [e.strip() for e in input_eans.split("\n") if e.strip()]
    
    if not ean_list:
        st.warning("Please paste your EANs.")
    else:
        zip_buffer = io.BytesIO()
        success_count = 0
        cols = st.columns(3)
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for idx, ean in enumerate(ean_list):
                with st.spinner(f"Fetching Packaging for {ean}..."):
                    url = UNSTOPPABLE_DATABASE.get(ean)
                    
                    if url:
                        try:
                            # Open Food Facts is bot-friendly, simple requests work perfectly
                            resp = requests.get(url, timeout=10)
                            if resp.status_code == 200:
                                processed = trim_and_center(resp.content)
                                if processed:
                                    img_io = io.BytesIO()
                                    processed.save(img_io, format='JPEG', quality=95)
                                    zip_file.writestr(f"{ean}.jpg", img_io.getvalue())
                                    
                                    with cols[success_count % 3]:
                                        st.image(processed, caption=f"SUCCESS: {ean}")
                                    success_count += 1
                                    continue
                        except:
                            pass
                    
                    st.error(f"❌ Could not retrieve: {ean}")

        if success_count > 0:
            st.success(f"Successfully processed {success_count} of {len(ean_list)} images!")
            st.download_button("📥 Download ZIP for Wolt", zip_buffer.getvalue(), "wolt_ready_packaging.zip")