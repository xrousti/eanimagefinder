import streamlit as st
import requests
from PIL import Image, ImageChops
import io
import zipfile
import time
import random
from duckduckgo_search import DDGS

# --- SETTINGS ---
TARGET_SIZE = (1000, 563)
WHITE = (255, 255, 255)

# 1. THE "BROWSER MIMIC" HEADERS
# This header package makes requests look like they're from a real desktop browser
SUPER_HUMAN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.google.com/', # Pretend we came from Google
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site'
}

# 2. THE HIGH-QUALITY SOURCE DATABASE
# We will always try these Amazon links first.
FIXED_DATABASE = {
    "5060079654738": "https://m.media-amazon.com/images/I/81hS7L6E6RL._AC_SL1500_.jpg",
    "5060708600341": "https://m.media-amazon.com/images/I/61I-0V8mP0L._AC_SL1500_.jpg",
    "5060708600365": "https://m.media-amazon.com/images/I/61NfT-jN27L._AC_SL1500_.jpg",
    "5061039210315": "https://m.media-amazon.com/images/I/81-pW4HlR7L._AC_SL1500_.jpg",
    "5201583184810": "https://lavdas.gr/wp-content/uploads/2021/05/Gum-On-Sour-Watermelon-Slices-80g.jpg",
    "5203064008912": "https://m.media-amazon.com/images/I/71YvUovzBLL._AC_SL1500_.jpg",
    "5281128101793": "https://jebnalak.com/cdn/shop/files/Jebnalak-2024-10-06T221531.371_1000x1000.png"
}

def trim(im):
    """Crops the image to the product bounds."""
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    return im.crop(bbox) if bbox else im

def process_image(img_content):
    """Formats image to 1000x563, white bg, centered."""
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        img = trim(img)
        img.thumbnail((TARGET_SIZE[0] - 120, TARGET_SIZE[1] - 80), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", TARGET_SIZE, WHITE)
        offset = ((TARGET_SIZE[0] - img.width) // 2, (TARGET_SIZE[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img)
        return canvas
    except:
        return None

# --- UI ---
st.set_page_config(page_title="Professional Packshot Factory", layout="wide")
st.title("📦 Retail Packaging Factory (Anti-Block Mode)")
st.write("Using browser mimicry to download high-quality packshots and format to **1000x563**.")

# Take EANs from text box
eans_to_process = st.text_area("Enter EANs (one per line):", height=200)

if st.button("🚀 Generate Professional Images"):
    ean_list = [ean.strip() for ean in eans_to_process.split('\n') if ean.strip()]
    if not ean_list:
        st.warning("Please provide at least one EAN.")
    else:
        zip_buffer = io.BytesIO()
        success_count = 0
        cols = st.columns(3)
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for idx, ean in enumerate(ean_list):
                with st.spinner(f"({idx+1}/{len(ean_list)}) Processing {ean}..."):
                    img_url = FIXED_DATABASE.get(ean)
                    if not img_url:
                        st.error(f"EAN {ean} not in database.")
                        continue

                    # 3. THE "HUMAN" DELAY
                    time.sleep(random.uniform(1.0, 2.5))
                    
                    try:
                        resp = requests.get(img_url, headers=SUPER_HUMAN_HEADERS, timeout=15)
                        if resp.status_code != 200:
                            raise ConnectionError(f"Blocked with status {resp.status_code}")

                        final_img = process_image(resp.content)
                        if final_img:
                            img_bytes = io.BytesIO()
                            final_img.save(img_bytes, format='JPEG', quality=95)
                            zip_file.writestr(f"{ean}.jpg", img_bytes.getvalue())
                            
                            with cols[success_count % 3]:
                                st.image(final_img, caption=f"Success: {ean}")
                            success_count += 1
                        else:
                            st.error(f"Failed to process image format for {ean}")
                    except Exception as e:
                        st.error(f"Download failed for {ean}: {e}")

        if success_count > 0:
            st.success(f"Successfully processed {success_count} of {len(ean_list)} images!")
            st.download_button("📥 Download All (.zip)", zip_buffer.getvalue(), "professional_packshots.zip")