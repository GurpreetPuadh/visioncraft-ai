"""
VisionCraft AI Processing Engine
OpenCV + NumPy based image/video editing.
Fixed: background removal, background color change, object detection reliability.
"""

import cv2
import numpy as np
import time
import re
import os
from pathlib import Path


# ─── Named Colors ─────────────────────────────────────────────────────────────

NAMED_COLORS = {
    'red':         (0,   0,   255),
    'green':       (0,   200, 0),
    'blue':        (255, 0,   0),
    'white':       (255, 255, 255),
    'black':       (0,   0,   0),
    'yellow':      (0,   255, 255),
    'orange':      (0,   165, 255),
    'purple':      (128, 0,   128),
    'pink':        (203, 192, 255),
    'cyan':        (255, 255, 0),
    'gray':        (128, 128, 128),
    'grey':        (128, 128, 128),
    'brown':       (42,  42,  165),
    'teal':        (128, 128, 0),
    'navy':        (128, 0,   0),
    'lime':        (0,   255, 0),
    'magenta':     (255, 0,   255),
    'violet':      (238, 130, 238),
    'indigo':      (130, 0,   75),
    'maroon':      (0,   0,   128),
    'beige':       (220, 245, 245),
    'gold':        (0,   215, 255),
    'silver':      (192, 192, 192),
    'transparent': None,
    'blur':        None,
}


# ─── Prompt Parser ────────────────────────────────────────────────────────────

_color_list = '|'.join(NAMED_COLORS.keys())

PROMPT_RULES = [
    # BG color change — checked BEFORE remove_background
    (rf'\b(change|make|set|turn|color|fill|replace)\b.{{0,30}}\b(background|bg|back)\b.{{0,20}}\b({_color_list})\b',
     'change_bg_color'),
    (rf'\b(background|bg|back)\b.{{0,20}}\b(to|into|=|:)\b.{{0,20}}\b({_color_list})\b',
     'change_bg_color'),

    # BG removal
    (r'\b(remove|delete|strip|cut|erase|clear)\b.{0,20}\b(background|bg|back)\b',
     'remove_background'),
    (r'\b(transparent|no\s+background|cutout)\b',
     'remove_background'),

    # BG blur
    (r'\b(blur|soften|bokeh)\b.{0,20}\b(background|bg|back)\b',
     'blur_background'),
    (r'\b(background|bg|back)\b.{0,20}\b(blur|blurr?y|soft|out.of.focus)\b',
     'blur_background'),

    # Detection
    (r'\b(detect|find|identify|locate|show|mark|highlight|label|annotate)\b.{0,30}'
     r'\b(object|thing|item|face|person|people|car|edge|subject)\b',
     'detect_objects'),
    (r'\bdetect\b|\bobject detection\b|\bfind objects\b',
     'detect_objects'),

    # Standard operations
    (r'\b(gray|grey|grayscale|black.{0,5}white|monochrome|desaturate)\b', 'grayscale'),
    (r'\b(sharp|sharpen|crisp|clarity|unblur)\b',                         'sharpen'),
    (r'\b(enhance|improve|restore|fix|upscale|better|quality)\b',         'enhance'),
    (r'\b(denoise|noise|clean|smooth|grain)\b',                           'denoise'),
    (r'\b(bright|lighten|exposure|luminance)\b',                          'brightness'),
    (r'\b(contrast|vivid|pop|punch)\b',                                   'contrast'),
    (r'\b(edge|outline|sketch|drawing|wireframe)\b',                      'edge_detect'),
    (r'\b(cartoon|anime|illustrat|comic)\b',                              'cartoon'),
    (r'\b(emboss|3d.{0,5}effect|relief|raised)\b',                        'emboss'),
    (r'\b(sepia|vintage|old.{0,5}photo|warm.{0,5}tone|retro|aged)\b',     'sepia'),
]


def parse_prompt(prompt: str) -> tuple:
    text = prompt.lower().strip()
    for pattern, operation in PROMPT_RULES:
        if re.search(pattern, text):
            return operation, _extract_params(text, operation)
    return 'enhance', {}


def _extract_params(text: str, operation: str) -> dict:
    params = {}
    if operation == 'change_bg_color':
        for color_name, bgr in NAMED_COLORS.items():
            if re.search(r'\b' + re.escape(color_name) + r'\b', text):
                params['color_name'] = color_name
                params['color_bgr']  = list(bgr) if bgr is not None else None
                break
    if operation == 'brightness':
        params['factor'] = -50 if re.search(r'\b(dark|darker|dim|shadow)\b', text) else 50
    if operation == 'contrast':
        params['alpha'] = 1.6
    if operation == 'blur_background':
        params['blur_strength'] = 25 if re.search(r'\b(strong|heavy|lot|very|extreme)\b', text) else 21
    return params


# ─── Main Entry Points ────────────────────────────────────────────────────────

def process_image(input_path: str, output_path: str, operation: str, params: dict) -> dict:
    start = time.time()
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Cannot read image: {input_path}")

    result_img, meta = _apply_operation(img, operation, params)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, result_img)

    return {
        'processing_time': round(time.time() - start, 3),
        'operation': operation,
        'width': result_img.shape[1],
        'height': result_img.shape[0],
        **meta
    }


def process_video(input_path: str, output_path: str, operation: str, params: dict,
                  max_frames: int = 300) -> dict:
    start = time.time()
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {input_path}")

    fps    = cap.get(cv2.CAP_PROP_FPS) or 25
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    processed = 0
    while processed < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        pframe, _ = _apply_operation(frame, operation, params)
        if pframe.shape[:2] != (height, width):
            pframe = cv2.resize(pframe, (width, height))
        out.write(pframe)
        processed += 1

    cap.release()
    out.release()
    return {'processing_time': round(time.time() - start, 3), 'operation': operation,
            'frames_processed': processed, 'total_frames': total, 'fps': fps,
            'width': width, 'height': height}


# ─── Operation Dispatcher ─────────────────────────────────────────────────────

def _apply_operation(img: np.ndarray, operation: str, params: dict):
    meta = {}

    if operation == 'grayscale':
        result = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)

    elif operation == 'sharpen':
        k = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
        result = cv2.filter2D(img, -1, k)

    elif operation == 'enhance':
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8)).apply(l)
        result = cv2.cvtColor(cv2.merge([l,a,b]), cv2.COLOR_LAB2BGR)
        result = cv2.filter2D(result, -1, np.array([[0,-1,0],[-1,5,-1],[0,-1,0]]))

    elif operation == 'denoise':
        result = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    elif operation == 'brightness':
        f = params.get('factor', 50)
        result = np.clip(img.astype(np.int16) + f, 0, 255).astype(np.uint8)

    elif operation == 'contrast':
        a = params.get('alpha', 1.6)
        result = np.clip(img.astype(np.float32) * a, 0, 255).astype(np.uint8)

    elif operation == 'edge_detect':
        gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 180)
        result = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    elif operation == 'cartoon':
        gray  = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 5)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                      cv2.THRESH_BINARY, 9, 9)
        color  = cv2.bilateralFilter(img, 9, 300, 300)
        result = cv2.bitwise_and(color, color, mask=edges)

    elif operation == 'emboss':
        k = np.array([[-2,-1,0],[-1,1,1],[0,1,2]])
        result = np.clip(cv2.filter2D(img,-1,k).astype(np.int16)+128, 0,255).astype(np.uint8)

    elif operation == 'sepia':
        k = np.array([[0.272,0.534,0.131],[0.349,0.686,0.168],[0.393,0.769,0.189]])
        result = np.clip(img.astype(np.float32) @ k.T, 0, 255).astype(np.uint8)

    elif operation == 'blur_background':
        result, meta = _blur_background(img, params)

    elif operation == 'remove_background':
        result, meta = _remove_background(img)

    elif operation == 'change_bg_color':
        result, meta = _change_background_color(img, params)

    elif operation == 'detect_objects':
        result, meta = _detect_objects(img)

    else:
        result = img

    return result, meta


# ─── Background Segmentation Core ────────────────────────────────────────────

def _get_foreground_mask(img: np.ndarray) -> np.ndarray:
    """
    Robust GrabCut-based foreground mask with morphological cleanup.
    Returns uint8 mask: 255 = foreground, 0 = background.
    """
    h, w = img.shape[:2]
    mask  = np.zeros((h, w), np.uint8)
    bgd   = np.zeros((1, 65), np.float64)
    fgd   = np.zeros((1, 65), np.float64)

    # Rect: 12% inset from edges — keeps subject centred
    mx = max(1, int(w * 0.12))
    my = max(1, int(h * 0.12))
    rect = (mx, my, w - 2*mx, h - 2*my)

    try:
        cv2.grabCut(img, mask, rect, bgd, fgd, 10, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        # Fallback: oval in centre
        fb = np.zeros((h, w), np.uint8)
        cv2.ellipse(fb, (w//2, h//2), (int(w*0.38), int(h*0.38)), 0, 0, 360, 255, -1)
        return fb

    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # Morphology: close holes, remove noise
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19)))
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

    # Keep only largest blob
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if n > 1:
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        fg = np.where(labels == biggest, 255, 0).astype(np.uint8)

    # Soft feather for natural edges
    fg = cv2.GaussianBlur(fg, (7, 7), 0)
    _, fg = cv2.threshold(fg, 127, 255, cv2.THRESH_BINARY)
    return fg


def _remove_background(img: np.ndarray):
    fg = _get_foreground_mask(img)
    result = img.copy()
    result[fg == 0] = [255, 255, 255]
    pct = round(np.sum(fg == 255) / fg.size * 100, 1)
    return result, {'method': 'GrabCut+white_bg', 'fg_coverage': f'{pct}%'}


def _change_background_color(img: np.ndarray, params: dict):
    """Replace background with any named color, or blur it."""
    color_name = params.get('color_name', 'white')
    color_bgr  = params.get('color_bgr')          # None means use blur

    fg = _get_foreground_mask(img)
    result = img.copy()

    if color_bgr is None:
        # Special case: blur or transparent → use heavy blur as BG
        blurred = cv2.GaussianBlur(img, (51, 51), 0)
        result[fg == 0] = blurred[fg == 0]
        method = 'blurred background'
    else:
        bg = tuple(int(c) for c in color_bgr)
        result[fg == 0] = bg
        method = f'solid #{color_name}'

    pct = round(np.sum(fg == 255) / fg.size * 100, 1)
    return result, {'method': method, 'color': color_name, 'fg_coverage': f'{pct}%'}


def _blur_background(img: np.ndarray, params: dict):
    """Blur background, keep foreground sharp with soft edge blending."""
    strength = params.get('blur_strength', 21)
    if strength % 2 == 0:
        strength += 1

    fg = _get_foreground_mask(img)

    # Smooth alpha for natural blend
    alpha = cv2.GaussianBlur(fg.astype(np.float32), (21, 21), 0) / 255.0
    alpha = np.stack([alpha]*3, axis=-1)

    blurred = cv2.GaussianBlur(img, (strength, strength), 0)
    result = (img.astype(np.float32) * alpha +
              blurred.astype(np.float32) * (1 - alpha))
    return result.astype(np.uint8), {'blur_strength': strength}


# ─── Object Detection ─────────────────────────────────────────────────────────

BOX_COLORS = [
    (0,220,255), (0,255,128), (255,80,80),  (255,180,0),
    (180,0,255), (0,200,200), (255,100,200),(100,255,50),
]


def _guess_label(x, y, bw, bh, iw, ih, img):
    """Heuristic label based on position, shape & dominant color."""
    aspect  = bw / max(bh, 1)
    area_pct = (bw * bh) / (iw * ih)
    cx = (x + bw/2) / iw
    cy = (y + bh/2) / ih

    roi = img[y:y+bh, x:x+bw]
    if roi.size > 0:
        b, g, r = roi.mean(axis=(0,1))
        skin  = r > 150 and g > 100 and b > 70 and r > g > b
        sky   = b > 130 and b > r and b > g and cy < 0.4
        green = g > r and g > b and g > 80
    else:
        skin = sky = green = False

    if area_pct > 0.12 and 0.15 < cx < 0.85 and skin:  return 'person'
    if area_pct > 0.18 and 0.15 < cx < 0.85:            return 'person'
    if aspect > 1.6 and cy > 0.5 and area_pct > 0.04:   return 'car'
    if sky and cy < 0.35:                                return 'sky'
    if green and cy > 0.45:                              return 'plant'
    if area_pct < 0.06 and cy < 0.4 and 0.75<aspect<1.3: return 'face'
    if aspect < 0.55 and area_pct > 0.03:               return 'person'
    if aspect > 2.2 and cy > 0.6:                       return 'table'
    if area_pct < 0.025:                                 return 'object'
    return 'region'


def _detect_objects(img: np.ndarray):
    h, w = img.shape[:2]
    result = img.copy()
    detected = []

    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur    = cv2.GaussianBlur(gray, (5,5), 0)
    edges   = cv2.bitwise_or(cv2.Canny(blur, 30,100), cv2.Canny(blur, 80,200))
    dilated = cv2.dilate(edges, np.ones((7,7), np.uint8), iterations=3)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = (h * w) * 0.008
    significant = sorted([c for c in contours if cv2.contourArea(c) > min_area],
                         key=cv2.contourArea, reverse=True)

    boxes = _nms_boxes([cv2.boundingRect(c) for c in significant])[:8]

    for i, (x, y, bw, bh) in enumerate(boxes):
        x, y = max(0,x), max(0,y)
        bw, bh = min(bw, w-x), min(bh, h-y)
        if bw < 10 or bh < 10:
            continue

        color = BOX_COLORS[i % len(BOX_COLORS)]
        label = _guess_label(x, y, bw, bh, w, h, img)
        conf  = min(0.97, round(0.60 + (bw*bh)/(h*w) * 1.5, 2))

        cv2.rectangle(result, (x,y), (x+bw, y+bh), color, 2)

        txt = f"{label}  {conf:.0%}"
        fs  = max(0.4, min(0.65, w/1000))
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
        cv2.rectangle(result, (x, max(0, y-th-8)), (x+tw+8, y), color, -1)
        cv2.putText(result, txt, (x+4, max(th, y-4)),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, (0,0,0), 1, cv2.LINE_AA)

        detected.append({'label': label, 'confidence': conf,
                         'x': x, 'y': y, 'width': bw, 'height': bh})

    return result, {'detections': detected, 'count': len(detected)}


def _nms_boxes(boxes, overlap_thresh=0.35):
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: b[2]*b[3], reverse=True)
    kept  = []
    for box in boxes:
        x1,y1,bw,bh = box
        x2,y2 = x1+bw, y1+bh
        skip = False
        for kx1,ky1,kw,kh in kept:
            kx2,ky2 = kx1+kw, ky1+kh
            ix = max(0, min(x2,kx2) - max(x1,kx1))
            iy = max(0, min(y2,ky2) - max(y1,ky1))
            inter = ix*iy
            union = bw*bh + kw*kh - inter
            if union > 0 and inter/union > overlap_thresh:
                skip = True; break
        if not skip:
            kept.append(box)
    return kept
