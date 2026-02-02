import os
import shutil
import re
from pathlib import Path
from collections import defaultdict

# Configuration
# Resolve BASE_DIR relative to the script location, not the CWD
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
SOURCE_DIR = os.path.join(BASE_DIR, "data/raw/images_yusmaris")
DEST_IMG_DIR = os.path.join(BASE_DIR, "data/raw/wsi_images")
DEST_ANN_DIR = os.path.join(BASE_DIR, "data/raw/annotations")
DEST_META_DIR = os.path.join(BASE_DIR, "data/raw/metadata") # Optional

# Regex to identify the base name (everything before the file extension/suffix)
# Example: "2023_03_16__11_24__17639.czi - Scene #01_noOverlay_flat_cal.tif" -> Group: "2023_03_16__11_24__17639.czi - Scene #01"
# We look for the common part shared by .geojson, .meta.json, and .tif
PATTERN = re.compile(r"(.+?)(_noOverlay_flat_cal|_withOverlay_flat_cal)?(\.tif|\.geojson|\.meta\.json)$")

def organize_files():
    # create dirs if not exist
    for d in [DEST_IMG_DIR, DEST_ANN_DIR, DEST_META_DIR]:
        os.makedirs(d, exist_ok=True)

    files = os.listdir(SOURCE_DIR)
    groups = defaultdict(dict)

    # 1. Group files
    for f in files:
        match = PATTERN.match(f)
        if match:
            base_name = match.group(1)
            # Normalize base name (sometimes there might be slight diffs, but usually this regex works)
            # If base name ends with " ", strip it
            base_name = base_name.strip()
            
            if f.endswith(".geojson"):
                groups[base_name]["geojson"] = f
            elif f.endswith(".meta.json"):
                groups[base_name]["meta"] = f
            elif "noOverlay" in f and f.endswith(".tif"):
                groups[base_name]["tif"] = f
            # We ignore "withOverlay" files for now

    # 2. Rename and Move
    sorted_bases = sorted(groups.keys())
    
    print(f"Found {len(sorted_bases)} unique scenes/regions.")
    
    for idx, base in enumerate(sorted_bases):
        new_name = f"slide_{idx+1:03d}"
        group = groups[base]
        
        # Check completeness
        if "geojson" not in group or "tif" not in group:
            print(f"Skipping incomple group: {base} (Has: {list(group.keys())})")
            continue
            
        # Move TIF
        src_tif = os.path.join(SOURCE_DIR, group["tif"])
        dst_tif = os.path.join(DEST_IMG_DIR, f"{new_name}.tif")
        shutil.move(src_tif, dst_tif)
        
        # Move GeoJSON
        src_geo = os.path.join(SOURCE_DIR, group["geojson"])
        dst_geo = os.path.join(DEST_ANN_DIR, f"{new_name}.geojson")
        shutil.move(src_geo, dst_geo)
        
        # Move Meta (if exists)
        if "meta" in group:
            src_meta = os.path.join(SOURCE_DIR, group["meta"])
            dst_meta = os.path.join(DEST_META_DIR, f"{new_name}.meta.json")
            shutil.move(src_meta, dst_meta)
            
        print(f"Moved {base} -> {new_name}")

if __name__ == "__main__":
    organize_files()
