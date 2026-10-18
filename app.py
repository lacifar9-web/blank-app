import streamlit as st
from PIL import Image, ImageOps, ImageFilter
import io
import zipfile
import os
from rembg import remove
import numpy as np

# Page config
st.set_page_config(
    page_title="Meesho Low-Shipping Image Generator",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .stButton > button { width: 100%; background: #FF6B35; color: white; border: none; font-weight: 600; }
    .stButton > button:hover { background: #E85D2D; }
    .variant-card { border: 2px solid #eee; border-radius: 12px; padding: 1rem; text-align: center; }
    .variant-card.selected { border-color: #FF6B35; background: #FFF4F0; }
    .metric-badge { background: #FF6B35; color: white; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
    .footer { text-align: center; color: #888; font-size: 0.85rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# Constants
MEESHO_WIDTH = 1080
MEESHO_HEIGHT = 1440
MEESHO_RATIO = MEESHO_WIDTH / MEESHO_HEIGHT  # 0.75 (3:4)
FILL_RATIOS = [0.76, 0.78, 0.80, 0.82, 0.84]  # Product fills this % of frame
MAX_FILE_SIZE_KB = 500

def remove_background(image: Image.Image) -> Image.Image:
    """Remove background using rembg (local AI model)."""
    # Convert to bytes
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    input_bytes = buf.getvalue()
    
    # Remove background
    output_bytes = remove(input_bytes)
    
    # Load result
    result = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
    return result

def add_white_background(image: Image.Image) -> Image.Image:
    """Add white background to transparent image."""
    white_bg = Image.new("RGB", image.size, (255, 255, 255))
    white_bg.paste(image, mask=image.split()[3] if image.mode == "RGBA" else None)
    return white_bg

def smart_crop_and_resize(
    image: Image.Image, 
    fill_ratio: float,
    target_size: tuple = (MEESHO_WIDTH, MEESHO_HEIGHT)
) -> Image.Image:
    """
    Crop tightly around non-white content, then resize to Meesho 3:4 with specified fill ratio.
    """
    # Convert to numpy for analysis
    arr = np.array(image.convert("RGBA"))
    
    # Find non-white/non-transparent pixels (product bounds)
    if image.mode == "RGBA":
        alpha = arr[:, :, 3]
        non_empty = alpha > 10
    else:
        # For RGB, find non-white pixels
        non_white = np.any(arr[:, :, :3] < 250, axis=2)
        non_empty = non_white
    
    rows = np.any(non_empty, axis=1)
    cols = np.any(non_empty, axis=1)
    
    if not np.any(rows) or not np.any(cols):
        # Fallback: center crop
        return ImageOps.fit(image, target_size, method=Image.LANCZOS, centering=(0.5, 0.5))
    
    y_min, y_max = np.where(rows)[0][[0, -1]]
    x_min, x_max = np.where(cols)[0][[0, -1]]
    
    # Add small padding around detected product (2%)
    h, w = arr.shape[:2]
    pad_y = int(h * 0.02)
    pad_x = int(w * 0.02)
    y_min = max(0, y_min - pad_y)
    y_max = min(h, y_max + pad_y)
    x_min = max(0, x_min - pad_x)
    x_max = min(w, x_max + pad_x)
    
    # Crop to product bounds
    cropped = image.crop((x_min, y_min, x_max, y_max))
    
    # Now resize to fit target with fill_ratio
    crop_w, crop_h = cropped.size
    target_w, target_h = target_size
    
    # Calculate scale so product fills fill_ratio of target
    scale_w = (target_w * fill_ratio) / crop_w
    scale_h = (target_h * fill_ratio) / crop_h
    scale = min(scale_w, scale_h)
    
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    
    # Resize product
    resized_product = cropped.resize((new_w, new_h), Image.LANCZOS)
    
    # Create white canvas
    canvas = Image.new("RGB", target_size, (255, 255, 255))
    
    # Center paste
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    
    if resized_product.mode == "RGBA":
        canvas.paste(resized_product, (paste_x, paste_y), resized_product)
    else:
        canvas.paste(resized_product, (paste_x, paste_y))
    
    return canvas

def compress_to_target(image: Image.Image, target_kb: int = MAX_FILE_SIZE_KB, quality: int = 85) -> tuple[Image.Image, int]:
    """Compress JPEG to under target KB."""
    # Try qualities from 85 down to 30
    for q in range(quality, 20, -5):
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=q, optimize=True)
        size_kb = len(buf.getvalue()) / 1024
        if size_kb <= target_kb:
            buf.seek(0)
            return Image.open(buf), int(size_kb)
    
    # If still too large, downscale slightly
    img = image.copy()
    for scale in [0.95, 0.9, 0.85, 0.8]:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70, optimize=True)
        size_kb = len(buf.getvalue()) / 1024
        if size_kb <= target_kb:
            buf.seek(0)
            return Image.open(buf), int(size_kb)
    
    # Last resort
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=50, optimize=True)
    buf.seek(0)
    return Image.open(buf), int(len(buf.getvalue()) / 1024)

def create_variants(original: Image.Image) -> list[dict]:
    """Generate all variant images."""
    # Step 1: Remove background
    with st.spinner("🔄 Removing background..."):
        no_bg = remove_background(original)
    
    # Step 2: Add white background
    white_bg_img = add_white_background(no_bg)
    
    variants = []
    progress = st.progress(0)
    status = st.empty()
    
    for i, fill_ratio in enumerate(FILL_RATIOS):
        status.text(f"Generating variant {i+1}/{len(FILL_RATIOS)} (fill: {int(fill_ratio*100)}%)...")
        
        # Crop and resize
        variant = smart_crop_and_resize(white_bg_img, fill_ratio)
        
        # Compress
        compressed, size_kb = compress_to_target(variant)
        
        # Save to bytes
        buf = io.BytesIO()
        compressed.save(buf, format="JPEG", quality=85, optimize=True)
        buf.seek(0)
        
        variants.append({
            "fill_ratio": fill_ratio,
            "label": f"{int(fill_ratio*100)}% Fill",
            "image": compressed,
            "bytes": buf.getvalue(),
            "size_kb": size_kb,
            "dimensions": f"{compressed.width}×{compressed.height}"
        })
        progress.progress((i + 1) / len(FILL_RATIOS))
    
    status.empty()
    progress.empty()
    return variants

def create_zip(variants: list[dict]) -> bytes:
    """Create ZIP file with all variants."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for v in variants:
            filename = f"meesho_{v['label'].replace('%', 'pct').replace(' ', '_')}.jpg"
            zf.writestr(filename, v["bytes"])
    zip_buf.seek(0)
    return zip_buf.getvalue()

# ===== UI =====
st.title("📦 Meesho Low-Shipping Image Generator")
st.caption("Generate tight-crop, white-background images optimized for Meesho's volumetric weight calculation — **100% free, runs locally**")

# File uploader
uploaded = st.file_uploader(
    "Upload your product photo",
    type=["jpg", "jpeg", "png", "webp"],
    help="Best results: clear product shot, any background. Max 10MB."
)

if uploaded:
    original = Image.open(uploaded).convert("RGBA")
    
    # Show original
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Original")
        st.image(original, use_container_width=True)
        st.caption(f"{original.width}×{original.height} • {uploaded.size/1024:.0f} KB")
    
    with col2:
        if st.button("🚀 Generate 5 Optimized Variants", type="primary", use_container_width=True):
            variants = create_variants(original)
            st.session_state.variants = variants
            st.session_state.original_name = uploaded.name.rsplit('.', 1)[0]
            st.rerun()

# Show variants if generated
if "variants" in st.session_state:
    variants = st.session_state.variants
    
    st.markdown("---")
    st.subheader("✅ Generated Variants — Pick the best one")
    st.caption("Each variant uses a different crop tightness. Test each on Meesho draft to find lowest shipping.")
    
    # Variant grid
    cols = st.columns(len(variants))
    selected_idx = st.session_state.get("selected_idx", 0)
    
    for i, (col, v) in enumerate(zip(cols, variants)):
        with col:
            is_selected = (i == selected_idx)
            card_class = "variant-card selected" if is_selected else "variant-card"
            
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            st.image(v["image"], use_container_width=True)
            
            # Metrics
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<span class="metric-badge">{v["size_kb"]} KB</span>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<span class="metric-badge">{v["dimensions"]}</span>', unsafe_allow_html=True)
            
            st.caption(v["label"])
            
            if st.button("Select", key=f"select_{i}", use_container_width=True):
                st.session_state.selected_idx = i
                st.rerun()
            
            # Individual download
            st.download_button(
                "⬇️ Download",
                data=v["bytes"],
                file_name=f"meesho_{v['label'].replace('%', 'pct').replace(' ', '_')}.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Bulk download
    st.markdown("---")
    zip_bytes = create_zip(variants)
    st.download_button(
        "📦 Download ALL as ZIP",
        data=zip_bytes,
        file_name=f"{st.session_state.original_name}_meesho_variants.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True
    )
    
    # Instructions
    with st.expander("📋 How to test on Meesho"):
        st.markdown("""
        1. Go to **Meesho Supplier Panel** → Add Product
        2. Upload **one variant at a time** as the **first/main image**
        3. Fill basic details (category, price, weight)
        4. **Save as Draft** — check the **shipping charge** shown
        5. Repeat for each variant → **pick the one with lowest shipping**
        6. Use that variant as your primary image for the live listing
        
        **Why this works:** Meesho's AI estimates volumetric weight from your primary image. 
        Tighter crops (76-84% fill) with clean white backgrounds = smaller estimated dimensions = lower shipping.
        """)

# Footer
st.markdown("""
<div class="footer">
    Built with ❤️ for Indian sellers • Powered by <a href="https://github.com/danielgatis/rembg" target="_blank">rembg</a> (local AI) • 
    Deploy free on <a href="https://huggingface.co/spaces" target="_blank">Hugging Face Spaces</a>
</div>
""", unsafe_allow_html=True)