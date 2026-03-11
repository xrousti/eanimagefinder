import streamlit as st
import requests
from PIL import Image
import io
import zipfile

# --- CONFIGURATION ---
TARGET_SIZE = (1000, 563)
WHITE = (255, 255, 255)

# Hardcoded high-res sources for your specific EANs
PRODUCT_DATABASE = {
    "5060079654738": "https://m.media-amazon.com/images/I/81hS7L6E6RL._AC_SL1500_.jpg",
    "5060708600341": "https://m.media-amazon.com/images/I/61I-0V8mP0L._AC_SL1500_.jpg",
    "5060708600365": "https://m.media-amazon.com/images/I/61NfT-jN27L._AC_SL1500_.jpg",
    "5061039210315": "https://m.media-amazon.com/images/I/81-pW4HlR7L._AC_SL1500_.jpg",
    "5201583184810": "https://lavdas.gr/wp-content/uploads/2021/05/Gum-On-Sour-Watermelon-Slices-80g.jpg",
    "5203064008912": "https://m.media-amazon.com/images/I/71YvUovzBLL._AC_SL1500_.jpg",
    "5281128101793": "https://jebnalak.com/cdn/shop/files/Jebnalak-2024-10-06T221531.371_1000x1000.png"
}

def process_image(url):
    """Downloads and formats image to 1000x563 centered on white."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")

        # 1. Trim whitespace/transparency
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        # 2. Resize to fit within 1000x563 (with margin)
        # We leave 60px padding so it looks professional
        img.thumbnail((TARGET_SIZE[0] - 120, TARGET_SIZE[1] - 80), Image.Resampling.LANCZOS)

        # 3. Create white canvas and center product
        canvas = Image.new("RGB", TARGET_SIZE, WHITE)
        offset = ((TARGET_SIZE[0] - img.width) // 2, (TARGET_SIZE[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        
        return canvas
    except Exception as e:
        return None

# --- STREAMLIT UI ---
st.set_page_config(page_title="EAN Image Factory", page_icon="📸")
st.title("📸 EAN Image Factory")
st.write("Formats images to **1000x563**, centered on a **white background**.")

# Input area
input_eans = st.text_area(
    "Enter EANs (one per line):", 
    value="\n".join(PRODUCT_DATABASE.keys()),
    height=200
)

if st.button("🚀 Process Images"):
    ean_list = [e.strip() for e in input_eans.split("\n") if e.strip()]
    
    if not ean_list:
        st.warning("Please enter at least one EAN.")
    else:
        zip_buffer = io.BytesIO()
        success_count = 0
        
        # Grid for display
        cols = st.columns(2)
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for i, ean in enumerate(ean_list):
                url = PRODUCT_DATABASE.get(ean)
                
                if not url:
                    st.error(f"❌ EAN {ean} not found in database.")
                    continue
                
                with st.spinner(f"Processing {ean}..."):
                    processed_img = process_image(url)
                    
                    if processed_img:
                        # Save to memory for the ZIP file
                        img_byte_arr = io.BytesIO()
                        processed_img.save(img_byte_arr, format='JPEG', quality=95)
                        zip_file.writestr(f"{ean}_1000x563.jpg", img_byte_arr.getvalue())
                        
                        # Display in columns
                        with cols[i % 2]:
                            st.image(processed_img, caption=f"EAN: {ean}")
                        success_count += 1
                    else:
                        st.error(f"⚠️ Failed to process image for {ean}")

        if success_count > 0:
            st.success(f"✅ Successfully processed {success_count} images!")
            st.download_button(
                label="📥 Download All Images (.zip)",
                data=zip_buffer.getvalue(),
                file_name="product_images_1000x563.zip",
                mime="application/zip"
            )