import os
import json
import glob
import numpy as np
import openslide
from shapely.geometry import Polygon, box
from shapely.affinity import translate, scale
import cv2
from pathlib import Path
from tqdm import tqdm

# --- CONFIGURATION (Adjust these as needed) ---
PATCH_SIZE = 1024  # Size of the patches (pixels)
OVERLAP = 100        # Overlap between patches (pixels)
TARGET_SIZE = 640  # Resize patch to this size for training (optional, can be same as PATCH_SIZE)
WSI_EXT = ".tif"   # Extension of WSI files
ANNOTATION_EXT = ".geojson"

# Paths
BASE_DIR = "../../" # Relative to scripts/preprocessing
RAW_DATA_DIR = os.path.join(BASE_DIR, "data/raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data/processed")

# Class mapping (Name in QuPath -> Class ID in YOLO)
# Update this dictionary based on your specific classes
CLASS_MAP = {
    "Decidua": 0,
    "Stroma": 1,
    "Necrosis": 2
    # Add more as needed
}

def create_dirs(split="train"):
    img_dir = os.path.join(PROCESSED_DIR, split, "images")
    lbl_dir = os.path.join(PROCESSED_DIR, split, "labels")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(lbl_dir, exist_ok=True)
    return img_dir, lbl_dir

def load_annotations(geojson_path):
    """Loads annotations from a QuPath GeoJSON file."""
    if not os.path.exists(geojson_path):
        print(f"Warning: Annotation file not found: {geojson_path}")
        return []
    
    with open(geojson_path, 'r') as f:
        data = json.load(f)
        
    polygons = []
    # GeoJSON from QuPath usually wraps features in a FeatureCollection
    if data.get('type') == 'FeatureCollection':
        features = data['features']
    else:
        features = [data]
        
    for feature in features:
        # Check classification
        classification = feature.get('properties', {}).get('classification', {})
        class_name = classification.get('name') if classification else None
        
        if class_name in CLASS_MAP:
            class_id = CLASS_MAP[class_name]
            geom_type = feature['geometry']['type']
            coords = feature['geometry']['coordinates']
            
            # GeoJSON polygons: list of lists of points (first list is exterior ring)
            if geom_type == 'Polygon':
                # Handle exterior ring only for simplicity, or manage holes if needed
                poly = Polygon(coords[0])
                if not poly.is_valid:
                    poly = poly.buffer(0)
                polygons.append({'poly': poly, 'class_id': class_id})
            elif geom_type == 'MultiPolygon':
                for poly_coords in coords:
                    poly = Polygon(poly_coords[0])
                    if not poly.is_valid:
                        poly = poly.buffer(0)
                    polygons.append({'poly': poly, 'class_id': class_id})
                    
    return polygons

def save_yolo_label(file_path, polygons, img_width, img_height):
    """Saves polygons to YOLO segmentation format."""
    lines = []
    for item in polygons:
        poly = item['poly']
        class_id = item['class_id']
        
        # Normalize coordinates
        normalized_coords = []
        if poly.is_empty: continue
        
        # Get exterior coordinates
        x, y = poly.exterior.coords.xy
        for i in range(len(x)):
            norm_x = min(max(x[i] / img_width, 0.0), 1.0)
            norm_y = min(max(y[i] / img_height, 0.0), 1.0)
            normalized_coords.extend([norm_x, norm_y])
            
        # Format: <class-index> <x1> <y1> <x2> <y2> ... <xn> <yn>
        line = f"{class_id} " + " ".join(map(str, map(lambda x: round(x, 6), normalized_coords)))
        lines.append(line)
        
    if lines:
        with open(file_path, 'w') as f:
            f.write("\n".join(lines))
    return len(lines) > 0

def process_wsi(wsi_path, annotation_path, output_img_dir, output_lbl_dir):
    slide_name = Path(wsi_path).stem
    print(f"Processing: {slide_name}")
    
    try:
        slide = openslide.OpenSlide(wsi_path)
    except Exception as e:
        print(f"Error opening slide {wsi_path}: {e}")
        return

    w_wsi, h_wsi = slide.dimensions
    
    # Load all annotations for this slide
    all_polys = load_annotations(annotation_path)
    if not all_polys:
        print(f"No valid annotations found for {slide_name}")
        # Proceeding anyway might be useful for background patches, but skipping for now
        # return 

    # Grid tiling
    step = PATCH_SIZE - OVERLAP
    
    for y in tqdm(range(0, h_wsi, step), desc="Rows"):
        for x in range(0, w_wsi, step):
            # Check if patch is within bounds (or handle edge cases)
            w_patch = min(PATCH_SIZE, w_wsi - x)
            h_patch = min(PATCH_SIZE, h_wsi - y)
            
            # Define patch geometry in WSI coordinates
            patch_poly = box(x, y, x + w_patch, y + h_patch)
            
            # Find intersecting annotations
            patch_annotations = []
            has_obj = False
            
            for item in all_polys:
                poly = item['poly']
                if patch_poly.intersects(poly):
                    # Clip geometry to patch
                    intersection = patch_poly.intersection(poly)
                    
                    if not intersection.is_empty:
                        # Translate to patch local coordinates
                        # (x_wsi, y_wsi) -> (x_patch, y_patch)
                        # We subtract x AND y from the coordinates
                        local_poly = translate(intersection, xoff=-x, yoff=-y)
                        
                        # Handle MultiPolygons that might result from clipping
                        if local_poly.geom_type == 'Polygon':
                            patch_annotations.append({'poly': local_poly, 'class_id': item['class_id']})
                        elif local_poly.geom_type == 'MultiPolygon':
                            for p in local_poly.geoms:
                                patch_annotations.append({'poly': p, 'class_id': item['class_id']})
                        
                        has_obj = True

            # Logic to save patch:
            # 1. Save if it has annotations
            # 2. Optionally save empty background patches (with a probability)
            # For this example, we save if it has annotations OR randomly 5% of backgrounds
            if has_obj or np.random.rand() < 0.05:
                # Read image region
                region = slide.read_region((x, y), 0, (w_patch, h_patch)).convert("RGB")
                region_np = np.array(region)

                # Resize if needed
                if TARGET_SIZE != PATCH_SIZE:
                    region_np = cv2.resize(region_np, (TARGET_SIZE, TARGET_SIZE))
                    # Scale polygon coordinates accordingly
                    scale_factor = TARGET_SIZE / PATCH_SIZE
                    for item in patch_annotations:
                         # Scale relative to (0,0) of the patch
                        item['poly'] = scale(item['poly'], xfact=scale_factor, yfact=scale_factor, origin=(0,0))
                    
                    # Update dimensions for normalization
                    save_w, save_h = TARGET_SIZE, TARGET_SIZE
                else:
                    save_w, save_h = w_patch, h_patch

                # Save Image
                fname = f"{slide_name}_x{x}_y{y}"
                cv2.imwrite(os.path.join(output_img_dir, f"{fname}.jpg"), cv2.cvtColor(region_np, cv2.COLOR_RGB2BGR))
                
                # Save Label
                if has_obj:
                    save_yolo_label(os.path.join(output_lbl_dir, f"{fname}.txt"), patch_annotations, save_w, save_h)

def main():
    # Setup directories
    train_img_dir, train_lbl_dir = create_dirs("train")
    
    # Get list of WSIs
    wsi_files = glob.glob(os.path.join(RAW_DATA_DIR, "wsi_images", f"*{WSI_EXT}"))
    
    if not wsi_files:
        print(f"No {WSI_EXT} files found in {os.path.join(RAW_DATA_DIR, 'wsi_images')}")
        return

    print(f"Found {len(wsi_files)} WSI files.")

    for wsi_file in wsi_files:
        basename = Path(wsi_file).stem
        # Assuming annotation file has same basename + .geojson
        # Adjust pattern if your files are named differently (e.g. .tif.geojson)
        geojson_pattern = os.path.join(RAW_DATA_DIR, "annotations", f"{basename}*{ANNOTATION_EXT}")
        found_geojsons = glob.glob(geojson_pattern)
        
        if not found_geojsons:
            print(f"No annotation found for {basename}, skipping...")
            continue
            
        # Take the first match
        geojson_file = found_geojsons[0]
        
        # Future improvement: Implement train/val split logic here
        # For now, put everything in train, user might want to split manually or via script
        process_wsi(wsi_file, geojson_file, train_img_dir, train_lbl_dir)

if __name__ == "__main__":
    main()
