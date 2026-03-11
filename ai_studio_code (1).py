import streamlit as st
import requests
from PIL import Image
import io
import zipfile

# --- IMAGE PROCESSING ENGINE ---
def process_product_image(img_data, target_size=(1000, 563)):
    """Trims, scales, and centers an image on a 1000x563 white canvas."""
    try:
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")

        # 1. Trim existing whitespace or transparency to get the 'tight' product
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        # 2. Calculate scaling (1000x563 is wide, so we usually scale by height)
        # We leave a 60px padding so the product doesn't touch the edges
        max_w = target_size[0] - 120
        max_h = target_size[1] - 80
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

        # 3. Create the pure white background
        canvas = Image.new("RGB", target_size, (255, 255, 255))

        # 4. Calculate centering position
        offset_x = (target_size[0] - img.width) // 2
        offset_y = (target_size[1] - img.height) // 2
        
        # Paste using the image itself as a mask (handles transparency correctly)
        canvas.paste(img, (offset_x, offset_y), mask=img)
        
        return canvas
    except Exception as e:
        return None

# --- GOOGLE SEARCH ENGINE ---
def get_image_from_google(ean, api_key, cx):
    """Uses Google API to find the best professional product image."""
    search_url = "https://www.googleapis.com/customsearch/v1"
    
    # Improved query for high-quality retail images
    query = f"EAN {ean} professional product photography packshot"
    
    params = {
        "q": query,
        "cx": cx,
        "key": api_key,
        "searchType": "image",
        "imgSize": "xlarge", # We want high res only
        "num": 1
    }

    try:
        response = requests.get(search_url, params=params)
        data = response.json()
        if "items" in data:
            return data["items"][0]["link"]
    except:
        return None
    return None

# --- WEB INTERFACE (STREAMLIT) ---
st.set_page_config(page_title="EAN Image Pro", layout="centered")
st.title("📸 EAN Image Pro: 1000x563")
st.markdown("Finds products via Google and formats them for your catalog.")

# Sidebar for Setup
with st.sidebar:
    st.header("⚙️ API Configuration")
    api_key = st.text_input("Google API Key", type="password")
    cx_id = st.text_input("Search Engine ID (CX)")
    st.divider()
    st.write("Format: **1000x563 px**")
    st.write("Background: **White**")
    st.write("Centering: **Enabled**")

# Main Input
ean_input = st.text_area("Enter EANs (one per line):", height=200, placeholder="5060079654738\n5281128101793")

if st.button("Generate & Download ZIP"):
    if not api_key or not cx_id:
        st.error("Please enter your API Key and CX ID in the sidebar.")
    elif not ean_input.strip():
        st.warning("Please enter at least one EAN.")
    else:
        ean_list = [e.strip() for e in ean_input.split("\n") if e.strip()]
        zip_buffer = io.BytesIO()
        success_count = 0

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            progress_bar = st.progress(0)
            
            for idx, ean in enumerate(ean_list):
                # Update progress
                progress_bar.progress((idx + 1) / len(ean_list))
                
                with st.status(f"Processing {ean}...", expanded=False):
                    img_url = get_image_from_google(ean, api_key, cx_id)
                    
                    if img_url:
                        try:
                            headers = {'User-Agent': 'Mozilla/5.0'}
                            img_data = requests.get(img_url, headers=headers, timeout=10).content
                            final_img = process_product_image(img_data)
                            
                            if final_img:
                                # Save to Zip
                                img_io = io.BytesIO()
                                final_img.save(img_io, format='JPEG', quality=95)
                                zip_file.writestr(f"{ean}.jpg", img_io.getvalue())
                                
                                st.image(final_img, caption=f"Found: {ean}")
                                success_count += 1
                            else:
                                st.error(f"Failed to process image for {ean}")
                        except:
                            st.error(f"Failed to download image for {ean}")
                    else:
                        st.error(f"Google could not find an image for {ean}")

        if success_count > 0:
            st.success(f"Successfully created {success_count} images!")
            st.download_button(
                label="📁 Download Processed Images (.zip)",
                data=zip_buffer.getvalue(),
                file_name="ean_catalog_images.zip",
                mime="application/zip"
            )