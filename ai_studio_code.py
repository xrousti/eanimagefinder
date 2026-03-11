import streamlit as st
import requests
from PIL import Image
import io
import zipfile
import time

# --- CONFIGURATION & API HELPERS ---
def get_google_image(ean, api_key, cx):
    """Searches Google Images for the EAN and returns the first result URL."""
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": f"product image EAN {ean}",
        "cx": cx,
        "key": api_key,
        "searchType": "image",
        "num": 1,
        "safe": "active"
    }
    try:
        response = requests.get(search_url, params=params)
        results = response.json()
        if "items" in results:
            return results["items"][0]["link"]
    except Exception as e:
        st.error(f"Google Search Error: {e}")
    return None

def get_off_image(ean):
    """Searches Open Food Facts for the EAN."""
    url = f"https://world.openfoodfacts.org/api/v0/product/{ean}.json"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("status") == 1:
            return data["product"].get("image_url")
    except:
        return None
    return None

def process_image(img_url, target_size=(1000, 563)):
    """Downloads, trims, centers, and pads image to 1000x563 white background."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(img_url, headers=headers, timeout=10)
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")

        # 1. Trim whitespace/alpha
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        # 2. Resize to fit (with 40px padding)
        img.thumbnail((target_size[0] - 80, target_size[1] - 80), Image.Resampling.LANCZOS)

        # 3. Create white canvas
        canvas = Image.new("RGB", target_size, (255, 255, 255))

        # 4. Center
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        
        return canvas
    except Exception as e:
        return None

# --- STREAMLIT UI ---
st.set_page_config(page_title="EAN Image Factory", layout="wide")
st.title("🖼️ EAN Image Factory (Google + OFF)")

with st.sidebar:
    st.header("Settings")
    google_api_key = st.text_input("Google API Key", type="password")
    google_cx = st.text_input("Search Engine ID (CX)")
    st.info("The tool will try Open Food Facts first. If it fails, it uses Google Search.")

input_eans = st.text_area("Enter EANs (one per line):", height=200)
process_btn = st.button("Generate & Process Images")

if process_btn:
    if not input_eans.strip():
        st.warning("Please enter at least one EAN.")
    else:
        ean_list = [e.strip() for e in input_eans.split("\n") if e.strip()]
        zip_buffer = io.BytesIO()
        processed_count = 0
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            cols = st.columns(3)
            
            for i, ean in enumerate(ean_list):
                with st.spinner(f"Finding image for {ean}..."):
                    # Step 1: Try Open Food Facts
                    img_url = get_off_image(ean)
                    source = "Open Food Facts"
                    
                    # Step 2: Try Google if OFF fails
                    if not img_url and google_api_key and google_cx:
                        img_url = get_google_image(ean, google_api_key, google_cx)
                        source = "Google Images"
                    
                    if img_url:
                        final_img = process_image(img_url)
                        if final_img:
                            # Save to ZIP
                            img_byte_arr = io.BytesIO()
                            final_img.save(img_byte_arr, format='JPEG', quality=90)
                            zip_file.writestr(f"{ean}.jpg", img_byte_arr.getvalue())
                            
                            # Display
                            with cols[i % 3]:
                                st.image(final_img, caption=f"EAN: {ean} (via {source})")
                            processed_count += 1
                        else:
                            st.error(f"Failed to process image for {ean}")
                    else:
                        st.error(f"Could not find image for {ean} (Check API settings)")

        if processed_count > 0:
            st.success(f"Successfully processed {processed_count} images!")
            st.download_button(
                label="Download Zip File",
                data=zip_buffer.getvalue(),
                file_name="product_images_1000x563.zip",
                mime="application/zip"
            )