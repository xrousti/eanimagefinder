import os
import io
import webbrowser
import requests
from PIL import Image, ImageChops

# --- SETTINGS ---
TARGET_SIZE = (1000, 563) # Wolt Requirement
WHITE_BG = (255, 255, 255)

def trim_whitespace(img):
    """Crops the image to the actual product edges."""
    bg = Image.new(img.mode, img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    return img.crop(bbox) if bbox else img

def process_and_save(ean, img_content):
    """Formats image to 1000x563 centered on white."""
    try:
        img = Image.open(io.BytesIO(img_content)).convert("RGBA")
        
        # 1. Trim existing borders
        img = trim_whitespace(img)
        
        # 2. Scale to fit within the box (leaving 10% safety padding)
        max_w = int(TARGET_SIZE[0] * 0.9)
        max_h = int(TARGET_SIZE[1] * 0.9)
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        
        # 3. Create white canvas and center product
        canvas = Image.new("RGB", TARGET_SIZE, WHITE_BG)
        offset = ((TARGET_SIZE[0] - img.width) // 2, (TARGET_SIZE[1] - img.height) // 2)
        
        # Paste using transparency mask if it exists
        canvas.paste(img, offset, mask=img if img.mode == 'RGBA' else None)
        
        # 4. Save
        if not os.path.exists("finished_images"):
            os.makedirs("finished_images")
            
        output_path = f"finished_images/{ean}.jpg"
        canvas.save(output_path, "JPEG", quality=95)
        print(f"✅ Saved: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        return False

def run_assistant():
    print("--- Wolt Image Assistant ---")
    input_data = input("Paste your EANs here (separated by spaces or new lines): ")
    eans = input_data.replace(',', ' ').split()
    
    for ean in eans:
        print(f"\n🚀 Processing EAN: {ean}")
        
        # Open Google Images search
        search_url = f"https://www.google.com/search?q={ean}&tbm=isch"
        webbrowser.open(search_url)
        
        # Wait for user to provide the link
        while True:
            img_url = input(f"Find the image, 'Copy Image Address', and PASTE it here (or type 'skip'): ").strip()
            
            if img_url.lower() == 'skip':
                break
            
            try:
                # Bypass bot protection on most sites
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(img_url, headers=headers, timeout=10)
                
                if resp.status_code == 200:
                    if process_and_save(ean, resp.content):
                        break # Move to next EAN
                else:
                    print(f"⚠️ Could not download that link (Status {resp.status_code}). Try another link.")
            except:
                print("❌ Invalid link or error. Make sure you chose 'Copy Image Address'.")

    print("\n🏁 All EANs processed! Check the 'finished_images' folder.")

if __name__ == "__main__":
    run_assistant()