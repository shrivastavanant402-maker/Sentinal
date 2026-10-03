import math
from PIL import Image, ImageDraw, ImageFilter

def create_aegismesh_icon(output_path: str, size: int = 512):
    # Supersampling factor for extreme anti-aliased sharpness
    scale = 4
    dim = size * scale
    center = dim / 2
    
    # Create RGBA canvas with transparency
    img = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Color palette
    c_shield_bg = (13, 17, 30, 245)      # Deep cyber slate
    c_border_outer = (99, 102, 241, 255) # Electric Indigo (#6366f1)
    c_cyan_glow = (6, 182, 212, 255)     # Cyber Cyan (#06b6d4)
    c_node_core = (255, 255, 255, 255)   # White hot center
    c_mesh_line = (56, 189, 248, 140)    # Soft cyan mesh line
    c_accent_purple = (168, 85, 247, 230)# Vivid Purple
    
    # Outer Shield boundary coordinates
    # Shield shape: top-flat with central peak, angular shoulders, tapering down to a sharp base
    # Margin ~ 10%
    pad_top = dim * 0.10
    pad_bottom = dim * 0.90
    pad_left = dim * 0.14
    pad_right = dim * 0.86
    shoulder_y = dim * 0.44
    
    shield_pts = [
        (center, pad_top),               # Top peak
        (pad_right, dim * 0.22),         # Top right shoulder
        (pad_right - dim * 0.04, shoulder_y), # Mid right
        (center, pad_bottom),            # Bottom point
        (pad_left + dim * 0.04, shoulder_y),  # Mid left
        (pad_left, dim * 0.22),          # Top left shoulder
    ]
    
    # 1. Soft subtle outer glow behind the shield
    glow_img = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    glow_draw.polygon(shield_pts, fill=(99, 102, 241, 70))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=18 * scale))
    img.paste(glow_img, (0, 0), glow_img)
    
    # 2. Draw solid shield background with subtle radial gradient
    draw.polygon(shield_pts, fill=c_shield_bg)
    
    # 3. Inner faceted geometry / mesh segments
    # Define mesh nodes inside the shield:
    n_top = (center, dim * 0.22)
    n_bottom = (center, dim * 0.76)
    n_left = (center - dim * 0.24, dim * 0.44)
    n_right = (center + dim * 0.24, dim * 0.44)
    n_center = (center, dim * 0.44)
    
    # Secondary facet nodes
    n_upper_left = (center - dim * 0.15, dim * 0.31)
    n_upper_right = (center + dim * 0.15, dim * 0.31)
    n_lower_left = (center - dim * 0.14, dim * 0.60)
    n_lower_right = (center + dim * 0.14, dim * 0.60)
    
    # Draw internal facet shading for 3D crystalline depth
    # Left hemisphere facets (slightly darker for contrast)
    draw.polygon([n_top, n_center, n_left], fill=(20, 28, 52, 220))
    draw.polygon([n_left, n_center, n_bottom], fill=(16, 23, 44, 220))
    # Right hemisphere facets (brighter indigo tint)
    draw.polygon([n_top, n_center, n_right], fill=(30, 41, 75, 220))
    draw.polygon([n_right, n_center, n_bottom], fill=(24, 34, 62, 220))
    
    # 4. Outer shield borders (multi-layer for precision bevel look)
    line_w_outer = int(14 * scale)
    line_w_inner = int(6 * scale)
    draw.polygon(shield_pts, outline=c_border_outer, width=line_w_outer)
    
    # Inset border
    inset_pts = [
        (center, pad_top + dim * 0.05),
        (pad_right - dim * 0.04, dim * 0.24),
        (pad_right - dim * 0.07, shoulder_y),
        (center, pad_bottom - dim * 0.06),
        (pad_left + dim * 0.07, shoulder_y),
        (pad_left + dim * 0.04, dim * 0.24),
    ]
    draw.polygon(inset_pts, outline=(99, 102, 241, 100), width=int(3 * scale))
    
    # 5. Interconnecting Zero-Trust Mesh Lines (Edges)
    edges = [
        (n_top, n_upper_left), (n_top, n_upper_right), (n_top, n_center),
        (n_upper_left, n_left), (n_upper_right, n_right),
        (n_upper_left, n_center), (n_upper_right, n_center),
        (n_left, n_center), (n_right, n_center),
        (n_left, n_lower_left), (n_right, n_lower_right),
        (n_lower_left, n_center), (n_lower_right, n_center),
        (n_lower_left, n_bottom), (n_lower_right, n_bottom),
        (n_center, n_bottom),
        # Cross diagonals for high-tech lattice feel
        (n_upper_left, n_lower_left), (n_upper_right, n_lower_right)
    ]
    
    for p1, p2 in edges:
        draw.line([p1, p2], fill=c_mesh_line, width=int(3.5 * scale))
    
    # 6. Mesh Vertices (Nodes)
    def draw_node(pt, radius_outer, radius_inner, glow_color, core_color):
        r_out = radius_outer * scale
        r_in = radius_inner * scale
        draw.ellipse([pt[0] - r_out, pt[1] - r_out, pt[0] + r_out, pt[1] + r_out], fill=glow_color)
        draw.ellipse([pt[0] - r_in, pt[1] - r_in, pt[0] + r_in, pt[1] + r_in], fill=core_color)
    
    # Outer constellation nodes
    nodes = [n_top, n_left, n_right, n_bottom, n_upper_left, n_upper_right, n_lower_left, n_lower_right]
    for pt in nodes:
        draw_node(pt, 9, 4, c_cyan_glow, c_node_core)
        
    # Central Integrity Core Node (Prominent, Glowing, represents AegisMesh PDP)
    # Layered core halo
    halo_img = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo_img)
    halo_draw.ellipse([n_center[0] - 40 * scale, n_center[1] - 40 * scale, 
                       n_center[0] + 40 * scale, n_center[1] + 40 * scale], fill=(6, 182, 212, 130))
    halo_img = halo_img.filter(ImageFilter.GaussianBlur(radius=10 * scale))
    img.paste(halo_img, (0, 0), halo_img)
    
    draw_node(n_center, 18, 9, c_cyan_glow, c_node_core)
    
    # Small lock/check accent at the very top notch
    draw.line([(center, pad_top), (center, dim * 0.17)], fill=(255, 255, 255, 220), width=int(4 * scale))
    
    # Downsample using high-quality Lanczos filter
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    final_img.save(output_path, "PNG")
    print(f"Generated {output_path} ({size}x{size}) successfully.")

if __name__ == "__main__":
    import os
    os.makedirs("vscode-extension/media", exist_ok=True)
    create_aegismesh_icon("vscode-extension/media/icon.png", 512)
