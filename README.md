# Meesho Low-Shipping Image Generator

**Free, automated tool to generate Meesho-optimized product images that minimize delivery charges.**

## How It Works

Meesho calculates shipping based on **volumetric weight** estimated from your **primary listing image** using AI. This tool:

1. **Removes background** (local AI, no API keys)
2. **Auto-crops tightly** around your product
3. **Generates 5 variants** with different fill ratios (76%-84%)
4. **Compresses to <500KB** (Meesho requirement)
5. **Outputs 1080×1440 (3:4)** — Meesho's preferred format

Test each variant on Meesho draft → pick the one with lowest shipping charge.

---

## Deploy Free on Hugging Face Spaces (3 Minutes)

### 1. Create Hugging Face Account
- Go to [huggingface.co](https://huggingface.co) → Sign up (free)

### 2. Create New Space
- Click **+ New Space** (top right)
- **Owner**: your username
- **Space name**: `meesho-image-optimizer` (or whatever you like)
- **License**: MIT
- **Space SDK**: **Streamlit** ⚠️ **Important: Select Streamlit, not Docker**
- **Hardware**: CPU basic (free)
- **Visibility**: Public (or Private if you prefer)
- Click **Create Space**

### 3. Upload Files
In your new Space, click **Files → Add file → Upload files**

Upload these 3 files from this folder:
- `app.py`
- `requirements.txt`
- `README.md` (this file)

### 4. Wait for Build
- HF Spaces will auto-install dependencies and launch
- First build takes ~3-5 minutes (downloads AI model ~180MB)
- Subsequent restarts are faster

### 5. Use It!
- Your Space URL: `https://huggingface.co/spaces/YOUR_USERNAME/meesho-image-optimizer`
- Bookmark it, share with team, use forever free

---

## Local Run (Optional)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Run
streamlit run app.py
```

---

## Why This Reduces Shipping

| Factor | Standard Image | Optimized Image |
|--------|----------------|-----------------|
| Background | Cluttered/colored | Pure white |
| Product fill | 40-60% | **76-84%** (tight crop) |
| Aspect ratio | Random | **1080×1440 (3:4)** |
| File size | Often >500KB | **<500KB** |
| Estimated volume | High | **Minimal** |

**Typical savings: ₹15-40 per order** on shipping charges.

---

## Tips for Best Results

1. **Shoot straight-on** (not angled) — AI detects bounds better
2. **Good lighting** — avoids shadows being counted as product
3. **Test all 5 variants** — sometimes 78% beats 80% depending on product shape
4. **Use the winning variant** as **Image #1** (primary) on Meesho
5. **Keep other images normal** — only primary image affects shipping calculation

---

## Tech Stack

- **Streamlit** — Web UI
- **rembg (u2net)** — Local background removal (runs in container, no API)
- **Pillow + NumPy** — Image processing
- **Hugging Face Spaces** — Free hosting (CPU, 16GB RAM, persistent storage)

---

## Cost

**₹0 forever** — Runs on HF Spaces free tier. No API keys, no credits, no limits.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Space sleeping" | Free spaces sleep after inactivity. First load takes ~30s to wake up. |
| Build fails | Check **Logs** tab. Usually fixed by restarting (Settings → Restart Space). |
| Out of memory | Use smaller input images (<5MB). Or upgrade to paid HF GPU (not needed usually). |
| Background not removed well | Try photo with clearer subject/background contrast. |

---

## License

MIT — Free to use, modify, distribute.

---

**Made for Indian e-commerce sellers 🇮🇳**  
*Stop overpaying on shipping due to bad product photos.*