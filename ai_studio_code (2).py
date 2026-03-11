import streamlit as st
import requests
from PIL import Image
import io
import zipfile

def process_product_image(img_data, target_size=(1000, 563)):
    try:
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        max_w, max_h = target_size[0] - 100, target_size[1] - 60
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
        canvas.paste(img, offset, mask=img)
        return canvas
    except: return None

def get_image_from_google(ean, api_key, cx):
    search_url = "https://www.googleapis.com/customsearch/v1"
    # We simplified the query to the bare minimum
    params = {
        "q": ean, 
        "cx": cx,
        "key": api_key,
        "searchType": "image",
        "num": 1
    }

    try:
        response = requests.get(search_url, params=params)
        data = response.json()
        
        # DIAGNOSTIC LOGGING
        if "error" in data:
            return None, f"Google API Error: {data['error']['message']}"
        
        if "items" in data:
            return data["items"][0]["link"], None
        
        return None, "Google found 0 results for this EAN on your 50 sites."
    except Exception as e:
        return None, f"Connection Error: {str(e)}"

# --- UI ---
st.set_page_config(page_title="EAN Debugger", layout="centered")
st.title("🔍 EAN Image Search (Diagnostic Mode)")

with st.sidebar:
    st.header("Step 1: Setup")
    api_key = st.text_input("Google API Key", type="password")
    cx_id = st.text_input("Search Engine ID (CX)")
    st.warning("Ensure 'Image Search' is ON in your Google Dashboard.")

ean_input = st.text_area("Step 2: Enter EANs", height=150)

if st.button("Step 3: Search & Process"):
    if not api_key or not cx_id:
        st.error("Missing API Key or CX ID")
    else:
        ean_list = [e.strip() for e in ean_input.split("\n") if e.strip()]
        zip_buffer = io.BytesIO()
        success_count = 0

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for ean in ean_list:
                with st.spinner(f"Searching {ean}..."):
                    url, error_msg = get_image_from_google(ean, api_key, cx_id)
                    
                    if url:
                        try:
                            headers = {"User-Agent": "Mozilla/5.0"}
                            r = requests.get(url, headers=headers, timeout=10)
                            final_img = process_product_image(r.content)
                            if final_img:
                                buf = io.BytesIO()
                                final_img.save(buf, format='JPEG', quality=95)
                                zip_file.writestr(f"{ean}.jpg", buf.getvalue())
                                st.image(final_img, caption=f"Success: {ean}")
                                success_count += 1
                            else:
                                st.error(f"Image format error for {ean}")
                        except:
                            st.error(f"Website blocked the download for {ean}")
                    else:
                        st.error(f"{ean}: {error_msg}")

        if success_count > 0:
            st.success(f"Processed {success_count} images.")
            st.download_button("📥 Download ZIP", zip_buffer.getvalue(), "images.zip")