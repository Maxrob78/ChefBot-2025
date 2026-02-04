import pygame
import sys
import unicodedata
import json
import os
import random
import shutil
import re
import math
import tkinter as tk
from tkinter import filedialog, messagebox

# --- 1. CONFIGURATION ---
pygame.init()

# Réglage clavier : délai 400ms, répétition toutes les 40ms
pygame.key.set_repeat(400, 40)

# --- FONCTION SPECIALE POUR L'EXE (Gestion des chemins) ---
def resource_path(relative_path):
    """ Obtenir le chemin absolu vers la ressource, fonctionne pour dev et pour PyInstaller """
    try:
        # PyInstaller crée un dossier temporaire et stocke le chemin dans _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

C = {
    "bg": (26, 26, 46), "card": (22, 33, 62), "card_hover": (30, 45, 80),
    "accent": (233, 69, 96), "accent_hover": (255, 100, 120),
    "text": (240, 240, 240), "dim": (160, 160, 180),
    "green": (50, 200, 120), "blue": (60, 120, 240), "orange": (255, 140, 50),
    "red": (220, 60, 60),
    "ice": (80, 220, 250),
    "ice_dark": (20, 60, 80),
    "text2": (0, 0, 0)
}
TK_C = {"bg": "#1A1A2E", "card": "#16213E", "text": "#EAEAEA", "accent": "#E94560", "input_bg": "#233252", "input_fg": "#FFFFFF"}

W, H = 1280, 720
screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
pygame.display.set_caption("ChefBot Ultimate - Portion Calculator")

def get_font(name, size, bold=False):
    try: return pygame.font.SysFont(name, size, bold)
    except: return pygame.font.SysFont("Arial", size, bold)

font_L = get_font("Segoe UI", 36, True)
font_M = get_font("Segoe UI", 24, True)
font_S = get_font("Segoe UI", 18)
font_bold = get_font("Segoe UI", 18, True)

clock = pygame.time.Clock()

# --- 2. FONCTIONS UTILITAIRES ---

def normalize(text):
    text = text.lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def flatten_ingredients(ings):
    r = []
    for i in ings:
        if isinstance(i, str): r.append(normalize(i))
        elif isinstance(i, dict):
            for o in i.get("ou", []):
                if isinstance(o, list): r.extend([normalize(x) for x in o])
                else: r.append(normalize(o))
    return r

def get_text_index(text, font, x_offset):
    """ Trouve l'index de la lettre la plus proche de la position x_offset (pixels) """
    if not text: return 0
    best_i = 0
    min_dist = float('inf')
    # On teste toutes les positions possibles du curseur (de 0 à len)
    for i in range(len(text) + 1):
        w = font.size(text[:i])[0] # Taille du texte jusqu'à i
        dist = abs(w - x_offset)   # Distance avec la souris
        if dist < min_dist:
            min_dist = dist
            best_i = i
        else:
            # Si la distance commence à augmenter, on a dépassé le point idéal
            break 
    return best_i


# --- MOTEUR DE CALCUL DE PORTIONS ---
def scale_text(text, factor):
    if factor == 1.0: return text
    def replacer(match):
        try:
            val = float(match.group(1).replace(',', '.'))
            new_val = val * factor
            res = f"{new_val:.2f}".rstrip('0').rstrip('.')
            return res.replace('.', ',')
        except: return match.group(1)
    return re.sub(r'(\d+(?:[.,]\d+)?)', replacer, text)

def format_display_ing(ing, factor=1.0):
    if isinstance(ing, str): 
        return f"• {scale_text(ing, factor)}"
    if isinstance(ing, dict):
        opts = []
        for o in ing.get("ou", []):
            if isinstance(o, list): opts.append(" + ".join([scale_text(x, factor) for x in o]))
            else: opts.append(scale_text(str(o), factor))
        return f"• Choix : {' OU '.join(opts)}"
    return str(ing)

def wrap(text, font, w):
    lines = []
    for p in text.replace('\\n', '\n').split('\n'):
        words = p.split(' ')
        curr = []
        for wd in words:
            if font.size(' '.join(curr + [wd]))[0] < w: curr.append(wd)
            else: lines.append(' '.join(curr)); curr = [wd]
        lines.append(' '.join(curr))
    return lines

# --- 3. DONNÉES ---
DATABASE = {"plats": {}, "sauces": {}}
FAVORITES = []
IMG_CACHE = {}
ALL_INGREDIENTS_WORDS = set()
PARTICLES = []
TIMER_DATA = {"active": False, "end_time": 0, "total": 0}

# Variables globales
CACHE_SURFACE = None
CACHE_HEIGHT = 0
PORTION_FACTOR = 1.0
LAST_SEL = None
SORT_MODE = "nom"
SORT_ASCENDING = True
cursor_pos = 0

def get_all_recipes():
    d = {}
    d.update(DATABASE.get("plats", {}))
    d.update(DATABASE.get("sauces", {}))
    return d

def load_data():
    global DATABASE, FAVORITES, ALL_INGREDIENTS_WORDS
    # Note: On utilise os.path.exists direct ici pour que le fichier soit editable a cote de l'exe
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r', encoding='utf-8') as f: DATABASE = json.load(f)
        except Exception as e: print(f"Erreur JSON: {e}")
    
    if os.path.exists('favorites.json'):
        try:
            with open('favorites.json', 'r', encoding='utf-8') as f: FAVORITES = json.load(f)
        except: FAVORITES = []
    
    ALL_INGREDIENTS_WORDS.clear()
    for cat in DATABASE.values():
        for rec in cat.values():
            raw = flatten_ingredients(rec.get("ingredients", []))
            for i in raw:
                for word in i.split():
                    if len(word) > 2: ALL_INGREDIENTS_WORDS.add(word)

def save_data():
    try:
        with open('data.json', 'w', encoding='utf-8') as f: json.dump(DATABASE, f, indent=4, ensure_ascii=False)
    except: pass

def save_favorites():
    try:
        with open('favorites.json', 'w', encoding='utf-8') as f: json.dump(FAVORITES, f)
    except: pass

def add_particles(x, y, color):
    for _ in range(15):
        PARTICLES.append({
            "x": x, "y": y, "vx": random.uniform(-3, 3), "vy": random.uniform(-3, 3),
            "life": 255, "color": color, "size": random.randint(3, 6)
        })

def update_draw_particles():
    for p in PARTICLES[:]:
        p["x"] += p["vx"]; p["y"] += p["vy"]; p["life"] -= 5; p["size"] -= 0.05
        if p["life"] <= 0 or p["size"] <= 0: PARTICLES.remove(p); continue
        s = pygame.Surface((int(p["size"])*2, int(p["size"])*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*p["color"], p["life"]), (int(p["size"]), int(p["size"])), int(p["size"]))
        screen.blit(s, (p["x"], p["y"]))

def start_timer(minutes):
    TIMER_DATA["active"] = True
    TIMER_DATA["total"] = minutes * 60 * 1000
    TIMER_DATA["end_time"] = pygame.time.get_ticks() + TIMER_DATA["total"]

def export_shopping_list():
    if not FAVORITES: return
    text = "LISTE COURSES\n=============\n\n"
    all_recs = get_all_recipes()
    for nom in FAVORITES:
        if nom in all_recs:
            text += f"[ ] {nom}\n"
            for ing in flatten_ingredients(all_recs[nom].get("ingredients", [])):
                text += f" - {ing}\n"
            text += "\n"
    try:
        with open("liste_courses.txt", "w", encoding="utf-8") as f: f.write(text)
        os.startfile("liste_courses.txt") if sys.platform == "win32" else None
    except: pass

def toggle_fav(nom, x, y):
    if nom in FAVORITES: FAVORITES.remove(nom)
    else: FAVORITES.append(nom); add_particles(x, y, C["accent"])
    save_favorites()

# --- 4. RECHERCHE & TRI ---

def recherche(cat, s, strict_mode=False):
    # 1. Sélection de la source
    src = {}
    if cat == "favoris": src = {k:v for k,v in get_all_recipes().items() if k in FAVORITES}
    elif cat == "tout": src = get_all_recipes()
    else: src = DATABASE.get(cat, {})
    
    # Si barre vide, on renvoie tout
    if not s.strip(): return list(src.keys())

    # 2. Préparation des mots-clés
    stop_words = {"de", "du", "la", "le", "les", "et", "au", "aux", "un", "une", "des", "pour", "avec"}
    raw_req = re.split(r'[,\s]+', s)
    req = [normalize(x) for x in raw_req if x.strip() and normalize(x) not in stop_words]
    
    if not req: return list(src.keys())

    scored_results = [] # Liste de tuples (score, nom_recette)
    basics = ["sel", "poivre", "eau", "huile", "beurre", "sucre", "farine", "vinaigre", "levure"]

    for name, data in src.items():
        recipe_ing_flat = flatten_ingredients(data.get("ingredients", []))
        norm_name = normalize(name)
        
        # --- MODE FRIGO (STRICT) ---
        # "Est-ce que je peux cuisiner ça avec ce que j'ai ?"
        if strict_mode:
            possible = True
            # On vérifie chaque ingrédient de la RECETTE
            for r_ing in recipe_ing_flat:
                is_basic = any(b in r_ing for b in basics)
                if is_basic: continue # On a toujours du sel/eau

                # Est-ce que cet ingrédient est dans ma recherche (mon frigo) ?
                found_in_fridge = False
                for my_item in req:
                    # On utilise la regex permissive sur le pluriel pour matcher
                    # ex: my_item="oeuf" matchera r_ing="oeufs"
                    if re.search(rf"\b{re.escape(my_item)}s?\b", r_ing):
                        found_in_fridge = True
                        break
                
                if not found_in_fridge:
                    possible = False
                    break # Il manque un ingrédient, recette impossible
            
            if possible:
                scored_results.append((100, name)) # Score max pour recette faisable

        # --- MODE RECHERCHE CLASSIQUE ---
        # "Trouve-moi des recettes qui parlent de ça"
        else:
            score = 0
            match_all_terms = True

            for word in req:
                term_found = False
                # Regex : \b = mot entier, s? = pluriel optionnel
                # Ex: "pomme" trouvera "pomme", "pommes", mais pas "pommeau"
                pattern = re.compile(rf"\b{re.escape(word)}s?\b", re.IGNORECASE)

                # 1. Bonus TITRE (Gros poids)
                if pattern.search(norm_name):
                    score += 10
                    term_found = True
                
                # 2. Bonus INGRÉDIENTS (Petit poids)
                for ing in recipe_ing_flat:
                    if pattern.search(ing):
                        score += 5
                        term_found = True
                        # Pas de break ici, si le mot apparait plusieurs fois, c'est bien aussi
                
                if not term_found:
                    match_all_terms = False
                    break # Un mot demandé n'est pas trouvé
            
            if match_all_terms:
                scored_results.append((score, name))

    # Tri par score décroissant (les plus pertinents en haut)
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    # On ne retourne que les noms
    return [x[1] for x in scored_results]

def extract_time_val(time_str):
    if not time_str: return 9999
    time_str = normalize(time_str)
    minutes = 0
    m_j = re.search(r'(\d+)\s*j', time_str)
    if m_j: minutes += int(m_j.group(1)) * 1440
    m_h = re.search(r'(\d+)\s*h', time_str)
    if m_h: minutes += int(m_h.group(1)) * 60
    m_min = re.search(r'(\d+)\s*min', time_str)
    if m_min: minutes += int(m_min.group(1))
    if not m_j and not m_h and not m_min:
        try: 
            val = int(re.sub(r'\D', '', time_str))
            if val > 0: minutes = val
        except: minutes = 9999
    return minutes

def difficulty_val(diff_str):
    d = normalize(diff_str)
    mapping = {"tres facile": 1, "facile": 2, "moyen": 3, "difficile": 4, "expert": 5}
    return mapping.get(d, 10)

def reorder_results(current_results):
    all_d = get_all_recipes()
    if SORT_MODE == "nom": key_func = lambda n: n.lower()
    elif SORT_MODE == "temps": key_func = lambda n: extract_time_val(all_d.get(n, {}).get("temps", ""))
    elif SORT_MODE == "difficulte": key_func = lambda n: difficulty_val(all_d.get(n, {}).get("difficulte", ""))
    else: return current_results
    current_results.sort(key=key_func, reverse=not SORT_ASCENDING)
    return current_results
 
def get_img(name, w, h):
    key = (name, w, h)
    if key in IMG_CACHE: return IMG_CACHE[key]
    
    # 1. Normalisation du nom (comme pour la sauvegarde)
    clean_name = normalize(name).replace(' ', '_')

    # Liste des variantes de noms possibles
    potential_names = [
        f"images/{name}.jpg", 
        f"images/{name}.png", 
        f"images/{clean_name}.jpg",
        f"images/{clean_name}.png"
    ]
    
    found = None
    
    for rel_path in potential_names:
        # A. D'abord, on cherche à l'EXTÉRIEUR (Dossier local "images/" à côté de l'exe)
        # C'est ici que sont vos nouvelles photos (Wrap, Chili, etc.)
        local_path = os.path.abspath(rel_path)
        
        if os.path.exists(local_path):
            try: 
                found = pygame.transform.smoothscale(pygame.image.load(local_path).convert(), (w,h))
                break # Trouvé dehors ! On arrête de chercher.
            except: pass
        
        # B. Si pas trouvé, on cherche à l'INTÉRIEUR (Dans le .exe / _MEIPASS)
        # C'est ici que sont les images d'origine
        internal_path = resource_path(rel_path)
        if os.path.exists(internal_path):
            try: 
                found = pygame.transform.smoothscale(pygame.image.load(internal_path).convert(), (w,h))
                break # Trouvé dedans !
            except: pass

    # Si vraiment aucune image n'est trouvée (ni dehors, ni dedans) -> Carré de couleur
    if not found:
        found = pygame.Surface((w,h))
        col = ((hash(name)&0xFF)%100+50, (hash(name)>>8&0xFF)%100+50, (hash(name)>>16&0xFF)%100+50)
        found.fill(col)
        txt = pygame.font.SysFont("Arial", int(h/1.8), True).render(name[0].upper(), True, (255,255,255))
        found.blit(txt, txt.get_rect(center=(w//2, h//2)))
        
    IMG_CACHE[key] = found
    return found

# --- 5. ÉDITEUR TKINTER ---
def ingredients_to_text(ing_list):
    text_lines = []
    for ing in ing_list:
        if isinstance(ing, str): text_lines.append(ing)
        elif isinstance(ing, dict) and "ou" in ing:
            options = []
            for opt in ing["ou"]:
                if isinstance(opt, list): options.append(" + ".join(opt))
                else: options.append(str(opt))
            text_lines.append(" OU ".join(options))
    return "\n".join(text_lines)

def text_to_ingredients(text_block):
    lines = text_block.strip().split('\n')
    final_list = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if " OU " in line.upper() or " ou " in line:
            raw_options = line.replace(" ou ", " OU ").split(" OU ")
            processed_options = []
            for opt in raw_options:
                opt = opt.strip()
                if "+" in opt: processed_options.append([x.strip() for x in opt.split('+')])
                else: processed_options.append(opt)
            final_list.append({"ou": processed_options})
        else: final_list.append(line)
    return final_list

def open_recipe_editor(category, old_name=None):
    default = {"temps": "", "difficulte": "Moyen", "tags": [], "ingredients": [], "instructions": ""}
    if old_name: default = DATABASE[category].get(old_name, default)

    root = tk.Tk()
    root.title("Éditeur")
    root.configure(bg=TK_C["bg"])
    rw, rh = 550, 750
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{rw}x{rh}+{(sw-rw)//2}+{(sh-rh)//2}")

    v_name = tk.StringVar(value=old_name if old_name else "")
    v_time = tk.StringVar(value=default.get("temps", ""))
    v_diff = tk.StringVar(value=default.get("difficulte", "Moyen"))
    v_tags = tk.StringVar(value=", ".join(default.get("tags", [])))
    v_img = tk.StringVar(value="")

    def lbl(t): tk.Label(root, text=t, bg=TK_C["bg"], fg=TK_C["text"], font=("Segoe UI", 10, "bold")).pack(pady=(10,2), anchor="w", padx=25)
    tk.Label(root, text="ÉDITION", bg=TK_C["card"], fg=TK_C["accent"], font=("Segoe UI", 14, "bold"), pady=10).pack(fill="x")

    lbl("Nom"); tk.Entry(root, textvariable=v_name, bg=TK_C["input_bg"], fg="white", relief="flat").pack(fill="x", padx=25, ipady=4)
    
    fr = tk.Frame(root, bg=TK_C["bg"]); fr.pack(fill="x", padx=25, pady=5)
    tk.Label(fr, text="Temps:", bg=TK_C["bg"], fg="white").pack(side="left")
    tk.Entry(fr, textvariable=v_time, width=10, bg=TK_C["input_bg"], fg="white", relief="flat").pack(side="left", padx=5)
    tk.Label(fr, text="Diff:", bg=TK_C["bg"], fg="white").pack(side="left", padx=5)
    tk.OptionMenu(fr, v_diff, "Très Facile", "Facile", "Moyen", "Difficile", "Expert").pack(side="left")

    lbl("Tags"); tk.Entry(root, textvariable=v_tags, bg=TK_C["input_bg"], fg="white", relief="flat").pack(fill="x", padx=25, ipady=4)
    lbl("Ingrédients"); ti = tk.Text(root, height=6, bg=TK_C["input_bg"], fg="white", relief="flat"); ti.pack(fill="x", padx=25)
    ti.insert("1.0", ingredients_to_text(default.get("ingredients", [])))
    lbl("Instructions"); tinst = tk.Text(root, height=6, bg=TK_C["input_bg"], fg="white", relief="flat"); tinst.pack(fill="x", padx=25)
    tinst.insert("1.0", default.get("instructions", ""))

    def pick():
        p = filedialog.askopenfilename(filetypes=[("Img", "*.jpg *.png")])
        if p: v_img.set(p)
    tk.Button(root, text="Choisir Image...", command=pick, bg=TK_C["card"], fg="white", relief="flat").pack(pady=10)

    def save():
        nm = v_name.get().strip()
        if not nm: return
        
        # --- LOGIQUE DE COPIE D'IMAGE MODIFIÉE POUR L'EXE ---
        if v_img.get():
            if not os.path.exists("images"): os.makedirs("images")
            
            # 1. Normaliser le nom de fichier (sans accents, minuscules, espaces -> tiret bas)
            clean_name = normalize(nm).replace(' ', '_')
            
            try: 
                ext = os.path.splitext(v_img.get())[1]
                # Sauvegarde au format normalisé, ce qui est l'une des pistes de recherche de get_img
                target_path = f"images/{clean_name}{ext}" 
                shutil.copy(v_img.get(), target_path)
            except Exception as e: 
                 print(f"Erreur copie image: {e}")
                 pass
        # --- FIN LOGIQUE ---
        
        nd = {
            "temps": v_time.get(), "difficulte": v_diff.get(),
            "tags": [x.strip() for x in v_tags.get().split(',') if x.strip()],
            "ingredients": text_to_ingredients(ti.get("1.0", tk.END)),
            "instructions": tinst.get("1.0", tk.END).strip()
        }
        if old_name and old_name != nm: del DATABASE[category][old_name]
        DATABASE[category][nm] = nd
        save_data()
        
        global IMG_CACHE
        IMG_CACHE = {} 
        
        root.destroy()

    tk.Button(root, text="ENREGISTRER", command=save, bg=TK_C["accent"], fg="white", font=("Segoe UI", 11, "bold"), relief="flat").pack(pady=10, ipadx=20)
    root.mainloop()
    return True

# --- 6. UI HELPERS ---
def draw_card_bg(rect, color, radius=12):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (0,0,0,60), s.get_rect(), border_radius=radius)
    screen.blit(s, (rect.x+3, rect.y+3))
    pygame.draw.rect(screen, color, rect, border_radius=radius)

def draw_btn(r, txt, hov, act=False):
    c = C["green"] if act else (C["accent_hover"] if hov else C["accent"])
    draw_card_bg(r, c, 8)
    t = font_bold.render(txt, True, C["text"])
    screen.blit(t, t.get_rect(center=r.center))

def draw_tag(x, y, txt, col, clickable=False):
    t = font_S.render(txt, True, C["text"])
    r = pygame.Rect(x, y, t.get_width()+16, 26)
    c = C["orange"] if clickable and r.collidepoint(pygame.mouse.get_pos()) else col
    draw_card_bg(r, c, 13)
    screen.blit(t, (x+8, y+2))
    return r.w + 6, r

def draw_rect(r, c, rad=10):
    pygame.draw.rect(screen, c, r, border_radius=rad)

def draw_loupe(rect):
    c = C["dim"]
    cx, cy = rect.x + 20, rect.centery
    pygame.draw.circle(screen, c, (cx, cy-2), 6, 2)
    pygame.draw.line(screen, c, (cx+4, cy+2), (cx+9, cy+7), 2)

# Ajoute ça dans la section 6. UI HELPERS

def draw_heart(surface, x, y, size, color, filled=True):
    """ Dessine un cœur vectoriel """
    w, h = size, size
    # Le cœur est composé de deux cercles et un triangle (polygone)
    width = int(w / 2) # Rayon des cercles
    if filled:
        pygame.draw.circle(surface, color, (x + width // 2, y + h // 3), width // 2) # Cercle gauche
        pygame.draw.circle(surface, color, (x + w - width // 2, y + h // 3), width // 2) # Cercle droit
        # Triangle bas
        points = [
            (x, y + h // 3),
            (x + w, y + h // 3),
            (x + w // 2, y + h)
        ]
        pygame.draw.polygon(surface, color, points)
    else:
        # Version contour (un peu plus complexe en pygame pur, on simplifie par un petit coeur vide)
        # Pour faire simple en contour, on dessine un plein plus petit au centre d'un grand
        draw_heart(surface, x, y, size, color, True)
        draw_heart(surface, x+2, y+2, size-4, C["card"], True) # On "efface" l'intérieur

# --- DANS LA BOUCLE PRINCIPALE (Partie Details) ---
# Remplace le bloc qui dessine le bouton Fav par ceci :

def draw_snowflake(surface, x, y, size, color):
    """ Dessine un flocon de neige minimaliste """
    # 3 lignes qui se croisent
    length = size // 2
    for angle in range(0, 180, 60):
        rad = math.radians(angle)
        # Calcul des extrémités
        x1 = x + math.cos(rad) * length
        y1 = y + math.sin(rad) * length
        x2 = x - math.cos(rad) * length
        y2 = y - math.sin(rad) * length
        pygame.draw.line(surface, color, (x1, y1), (x2, y2), 2)
        
        # Petits bouts aux extrémités (optionnel, pour faire plus "flocon")
        tip_len = length // 3
        for tip_angle in [-45, 45]:
            rad_tip = math.radians(angle + tip_angle)
            pygame.draw.line(surface, color, (x1, y1), (x1 - math.cos(rad_tip)*tip_len, y1 - math.sin(rad_tip)*tip_len), 1)
            pygame.draw.line(surface, color, (x2, y2), (x2 + math.cos(rad_tip)*tip_len, y2 + math.sin(rad_tip)*tip_len), 1)

# --- 7. CACHE & RENDU OPTIMISÉ ---
def prepare_details_surface(d, width):
    h_est = 1000 + len(d.get("ingredients", []))*40 + len(d.get("instructions", ""))*5
    s = pygame.Surface((width, h_est), pygame.SRCALPHA)
    
    iy = 0
    title_ing = font_M.render("Ingrédients", True, C["green"])
    s.blit(title_ing, (20, iy)); iy += 40
    
    for ing in d.get("ingredients", []):
        ls = wrap(format_display_ing(ing, PORTION_FACTOR), font_S, width/2 - 60)
        for l in ls:
            s.blit(font_S.render(l, True, C["dim"]), (20, iy))
            iy += 25
        iy += 5
    ing_height = iy
    
    py = 0
    title_prep = font_M.render("Préparation", True, C["accent"])
    s.blit(title_prep, (width/2 + 20, py)); py += 40
    
    lines = wrap(d.get("instructions", ""), font_S, width/2 - 60)
    for l in lines:
        col = C["text"] if (len(l)>0 and l[0].isdigit()) else C["dim"]
        s.blit(font_S.render(l, True, col), (width/2 + 20, py))
        py += 30
        
    final_h = max(ing_height, py) + 50
    return s.subsurface((0, 0, width, final_h)), final_h

# --- 8. MAIN LOOP ---
load_data()
etat, mode, sel = "menu", "tout", None
inp_txt, act_inp = "", False
strict_mode = False 
scroll_l, scroll_d = 0, 0
res = recherche(mode, inp_txt, strict_mode)
res = reorder_results(res)
anim_frigo_val = 0.0
# --- MODIFICATION ICI ---
scroll_l, scroll_d = 0, 0
target_scroll_l, target_scroll_d = 0, 0 # On ajoute les "Cibles"

# --- 8. MAIN LOOP ---
load_data()
etat, mode, sel = "menu", "tout", None
inp_txt, act_inp = "", False
strict_mode = False 
scroll_l, scroll_d = 0, 0
target_scroll_l, target_scroll_d = 0, 0
res = recherche(mode, inp_txt, strict_mode)
res = reorder_results(res)
anim_frigo_val = 0.0

while True:
    mx, my = pygame.mouse.get_pos()
    evs = pygame.event.get()
    screen.fill(C["bg"])
    cursor_hover = False 
    
    # Header global
    pygame.draw.rect(screen, (20,20,30), (0,0,W,80))
    pygame.draw.line(screen, C["card"], (0,80), (W,80), 2)
    screen.blit(font_L.render("ChefBot", True, C["accent"]), (30, 15))
    
    if TIMER_DATA["active"]:
        rem = max(0, TIMER_DATA["end_time"] - pygame.time.get_ticks())
        col_t = C["green"] if rem > 0 else C["red"]
        tr = pygame.Rect(W-150, 20, 120, 40)
        draw_rect(tr, (0,0,0), 8)
        ts = font_M.render(f"{int(rem//60000):02}:{int((rem%60000)/1000):02}", True, col_t)
        screen.blit(ts, ts.get_rect(center=tr.center))
        if rem == 0 and (pygame.time.get_ticks()//200)%2: pygame.draw.rect(screen, C["red"], tr, 2, border_radius=8)

    # --- PHYSIQUE DU SCROLL (Placée ici pour qu'elle s'exécute TOUJOURS) ---
    if etat == "menu":
        scroll_l += (target_scroll_l - scroll_l) * 0.15
        if abs(target_scroll_l - scroll_l) < 1: scroll_l = target_scroll_l
    elif etat == "details":
        scroll_d += (target_scroll_d - scroll_d) * 0.15
        if abs(target_scroll_d - scroll_d) < 1: scroll_d = target_scroll_d
    # -----------------------------------------------------------------------

    # Gestion Quitter et Resize (Global)
    for e in evs:
        if e.type == pygame.QUIT: sys.exit()
        if e.type == pygame.VIDEORESIZE:
            W, H = e.w, e.h
            screen = pygame.display.set_mode((W,H), pygame.RESIZABLE)
            if etat == "details": CACHE_SURFACE = None

    # ==========================================
    #                ETAT : MENU
    # ==========================================
    if etat == "menu":
        input_w = min(400, W-400)
        input_rect = pygame.Rect((W-input_w)//2, 20, input_w, 40)
        btn_strict = pygame.Rect(input_rect.right + 15, 20, 90, 40)
        btn_add = pygame.Rect(W-100, 20, 80, 40)
        
        btns = [("Tout","tout"), ("Plats","plats"), ("Sauces","sauces"), ("Favoris","favoris"), ("Hasard","rand")]
        bx = (W - (120*5+40))//2
        btn_sort = pygame.Rect(bx + 130 * 5, 100, 160, 40)

        sugg = []
        if act_inp and len(inp_txt) > 1:
            lw = inp_txt.split(',')[-1].strip().lower()
            if lw: sugg = [w for w in ALL_INGREDIENTS_WORDS if w.startswith(lw)][:3]

        for e in evs:
            # 1. Clics Souris
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1: 
                    act_inp = input_rect.collidepoint(e.pos)
                    if act_inp: cursor_pos = len(inp_txt)
                    # Dans if etat == "menu": -> for e in evs: -> if MOUSEBUTTONDOWN: -> if button == 1:
                    act_inp = input_rect.collidepoint(e.pos)
                    if act_inp:
                        # --- NOUVEAU : PLACEMENT DU CURSEUR AU CLIC ---
                        # On calcule la position relative de la souris dans le champ texte
                        # +40 c'est la marge gauche qu'on a mise pour la loupe
                        relative_x = e.pos[0] - (input_rect.x + 40)
                        # On utilise la fonction utilitaire (section 2) pour trouver l'index
                        cursor_pos = get_text_index(inp_txt, font_S, relative_x)
                        # ---------------------------------------------
                    else:
                        # Si on clique ailleurs, on garde la longueur max (optionnel)
                        pass

                    if sugg:
                        for i, s in enumerate(sugg):
                            if pygame.Rect(input_rect.x, input_rect.bottom + i*30, input_rect.w, 30).collidepoint(e.pos):
                                p = inp_txt.split(','); p[-1] = s; inp_txt = ",".join(p) + ", "
                                cursor_pos = len(inp_txt)
                                res = recherche(mode, inp_txt, strict_mode)
                                res = reorder_results(res)

                    if btn_strict.collidepoint(e.pos):
                        strict_mode = not strict_mode
                        res = recherche(mode, inp_txt, strict_mode)
                        res = reorder_results(res)

                    if btn_add.collidepoint(e.pos):
                        if open_recipe_editor("plats"): 
                            res = recherche(mode, inp_txt, strict_mode)
                            res = reorder_results(res)
                    
                    if btn_sort.collidepoint(e.pos):
                        current_state = (SORT_MODE, SORT_ASCENDING)
                        if current_state == ("nom", True): SORT_MODE, SORT_ASCENDING = "nom", False
                        elif current_state == ("nom", False): SORT_MODE, SORT_ASCENDING = "temps", True
                        elif current_state == ("temps", True): SORT_MODE, SORT_ASCENDING = "temps", False
                        elif current_state == ("temps", False): SORT_MODE, SORT_ASCENDING = "difficulte", True
                        elif current_state == ("difficulte", True): SORT_MODE, SORT_ASCENDING = "difficulte", False
                        else: SORT_MODE, SORT_ASCENDING = "nom", True
                        res = reorder_results(res)

                    cx = bx
                    for l, c in btns:
                        if pygame.Rect(cx, 100, 120, 40).collidepoint(e.pos):
                            if c == "rand":
                                f = recherche(mode, inp_txt, strict_mode)
                                if f: sel = random.choice(f); etat = "details"; scroll_d = 0; target_scroll_d = 0; CACHE_SURFACE = None
                            else: 
                                mode = c
                                res = recherche(mode, inp_txt, strict_mode)
                                res = reorder_results(res)
                                scroll_l = 0
                                target_scroll_l = 0
                        cx += 130
                    
                    sb_rect = pygame.Rect(bx - 170, 100, 160, 40)
                    if mode == "favoris" and sb_rect.collidepoint(e.pos): export_shopping_list()

                    sy = 170
                    for i, n in enumerate(res):
                        if pygame.Rect(50, sy+i*90-scroll_l, W-100, 80).collidepoint(e.pos) and (sy+i*90-scroll_l) > 150:
                            sel = n; etat = "details"; scroll_d = 0; target_scroll_d = 0; CACHE_SURFACE = None; PORTION_FACTOR = 1.0

            # 2. Clavier
            if e.type == pygame.KEYDOWN and act_inp:
                if e.key == pygame.K_v and (e.mod & pygame.KMOD_CTRL):
                    try:
                        temp_root = tk.Tk(); temp_root.withdraw()
                        clip = temp_root.clipboard_get(); temp_root.destroy()
                        if clip:
                            inp_txt = inp_txt[:cursor_pos] + clip + inp_txt[cursor_pos:]
                            cursor_pos += len(clip)
                            res = recherche(mode, inp_txt, strict_mode)
                            res = reorder_results(res)
                    except: pass
                elif e.key == pygame.K_BACKSPACE:
                    if cursor_pos > 0:
                        inp_txt = inp_txt[:cursor_pos-1] + inp_txt[cursor_pos:]
                        cursor_pos -= 1
                elif e.key == pygame.K_DELETE:
                    if cursor_pos < len(inp_txt):
                        inp_txt = inp_txt[:cursor_pos] + inp_txt[cursor_pos+1:]
                elif e.key == pygame.K_LEFT:
                    if cursor_pos > 0: cursor_pos -= 1
                elif e.key == pygame.K_RIGHT:
                    if cursor_pos < len(inp_txt): cursor_pos += 1
                elif e.unicode.isprintable():
                    inp_txt = inp_txt[:cursor_pos] + e.unicode + inp_txt[cursor_pos:]
                    cursor_pos += 1
                res = recherche(mode, inp_txt, strict_mode)
                res = reorder_results(res)

            # 3. Molette (CORRECTEMENT ALIGNÉE ICI)
            if e.type == pygame.MOUSEWHEEL: 
                total_content_height = 170 + len(res) * 90 + 20 
                max_scroll_l = max(0, total_content_height - H)
                target_scroll_l = max(0, min(target_scroll_l - e.y * 80, max_scroll_l))

        # --- DESSIN MENU ---
        draw_card_bg(input_rect, C["card_hover"] if act_inp else C["card"], 20)
        draw_loupe(input_rect)
        if input_rect.collidepoint(mx, my): cursor_hover = True
        
        t = font_S.render(inp_txt if inp_txt else "Ingrédients...", True, C["text"] if inp_txt else C["dim"])
        screen.set_clip(input_rect.inflate(-20,-10)); screen.blit(t, (input_rect.x+40, input_rect.y+8))
        if act_inp and (pygame.time.get_ticks()//500)%2:
            cursor_x_offset = font_S.size(inp_txt[:cursor_pos])[0]
            ix = input_rect.x + 40 + cursor_x_offset
            pygame.draw.line(screen, C["accent"], (ix, input_rect.y+8), (ix, input_rect.y+32), 2)
        screen.set_clip(None)
        
        if sugg:
            y_s = input_rect.bottom
            for s in sugg:
                r = pygame.Rect(input_rect.x, y_s, input_rect.w, 30)
                if r.collidepoint(mx, my): cursor_hover = True
                pygame.draw.rect(screen, C["card_hover"], r)
                screen.blit(font_S.render(s, True, C["dim"]), (r.x+10, r.y+2))
                y_s += 30

        draw_btn(btn_add, "+", btn_add.collidepoint(mx,my))
        if btn_add.collidepoint(mx, my): cursor_hover = True
        
        # Bouton Frigo Animé
        target_val = 1.0 if strict_mode else 0.0
        anim_frigo_val += (target_val - anim_frigo_val) * 0.2
        r_col = int(C["card"][0] + (C["ice"][0] - C["card"][0]) * anim_frigo_val)
        g_col = int(C["card"][1] + (C["ice"][1] - C["card"][1]) * anim_frigo_val)
        b_col = int(C["card"][2] + (C["ice"][2] - C["card"][2]) * anim_frigo_val)
        pygame.draw.rect(screen, (r_col, g_col, b_col), btn_strict, border_radius=20)
        
        start_x, end_x = btn_strict.x + 20, btn_strict.right - 20
        current_knob_x = start_x + (end_x - start_x) * anim_frigo_val
        
        if anim_frigo_val > 0.1:
            s_glow = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(s_glow, (255, 255, 255, int(100 * anim_frigo_val)), (20, 20), 19)
            screen.blit(s_glow, (current_knob_x - 20, btn_strict.centery - 20))
        pygame.draw.circle(screen, (255,255,255), (current_knob_x, btn_strict.centery), 16)
        
        snowflake_col = C["ice"] if anim_frigo_val > 0.5 else C["bg"]
        draw_snowflake(screen, current_knob_x, btn_strict.centery, 18, snowflake_col)

        if anim_frigo_val > 0.5:
            tsurf = font_bold.render("ON", True, C["ice_dark"])
            screen.blit(tsurf, (btn_strict.x + 10, btn_strict.centery - tsurf.get_height()//2))
        else:
            tsurf = font_bold.render("OFF", True, C["dim"])
            screen.blit(tsurf, (btn_strict.right - 35, btn_strict.centery - tsurf.get_height()//2))

        lbl_col = C["ice"] if strict_mode else C["dim"]
        lbl = font_bold.render("Mode Frigo", True, lbl_col)
        screen.blit(lbl, (btn_strict.right + 12, btn_strict.centery - lbl.get_height() // 2))
        if btn_strict.collidepoint(mx, my): cursor_hover = True

        cx = bx
        for l, c in btns:
            r = pygame.Rect(cx, 100, 120, 40)
            if r.collidepoint(mx, my): cursor_hover = True
            draw_btn(r, l, r.collidepoint(mx,my), mode==c)
            cx += 130
        
        if btn_sort.collidepoint(mx, my): cursor_hover = True
        symbol = "^" if SORT_ASCENDING else "v"
        draw_btn(btn_sort, f"Tri: {SORT_MODE.capitalize()} {symbol}", btn_sort.collidepoint(mx,my))

        if mode == "favoris":
            sb = pygame.Rect(bx - 170, 100, 160, 40)
            if sb.collidepoint(mx, my): cursor_hover = True
            draw_btn(sb, "Liste Courses", sb.collidepoint(mx,my))

        screen.set_clip(pygame.Rect(0, 150, W, H-150))
        if not res:
            e = font_M.render("Aucune recette trouvée 🤷‍♂️", True, C["dim"])
            screen.blit(e, (W//2 - e.get_width()//2, 300))

        sy = 170
        all_d = get_all_recipes()
        for i, n in enumerate(res):
            y = sy + i*90 - scroll_l
            if y > H: break
            if y < 80: continue
            r = pygame.Rect(50, y, W-100, 80)
            hov = r.collidepoint(mx,my)
            if hov: cursor_hover = True
            
            # Carte avec Ombre
            shadow_rect = r.copy(); shadow_rect.x += 2; shadow_rect.y += 2
            s_shadow = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(s_shadow, (0, 0, 0, 80), s_shadow.get_rect(), border_radius=10)
            screen.blit(s_shadow, (shadow_rect.x, shadow_rect.y))
            
            base_col = C["card_hover"] if hov else C["card"]
            pygame.draw.rect(screen, base_col, r, border_radius=10)
            
            # Image avec bordure
            img = get_img(n, 60, 60)
            pygame.draw.rect(screen, C["text"], (r.x+8, r.y+8, 64, 64), border_radius=6) 
            screen.blit(img, (r.x+10, r.y+10))
            
            title_col = C["accent"] if hov else C["text"]
            screen.blit(font_M.render(n, True, title_col), (r.x+85, r.y+10))
            
            dt = all_d.get(n, {})
            tx = r.x+85
            if dt.get("temps"): tx += draw_tag(tx, r.y+45, f"Temps: {dt['temps']}", C["bg"])[0]
            
            col = C["accent"] if n in FAVORITES else C["dim"]
            pygame.draw.circle(screen, col, (r.right-30, r.centery), 8)
            if n not in FAVORITES and not hov: pygame.draw.circle(screen, C["card"], (r.right-30, r.centery), 6)
        screen.set_clip(None)

    # ==========================================
    #                ETAT : DETAILS
    # ==========================================
    elif etat == "details":
        d = get_all_recipes().get(sel, {})
        cat = "sauces" if sel in DATABASE.get("sauces") else "plats"
        
        b_back = pygame.Rect(W-120, 20, 100, 40)
        b_edit = pygame.Rect(W-230, 20, 100, 40)
        b_fav = pygame.Rect(W-340, 20, 100, 40)
        
        if b_back.collidepoint(mx, my): cursor_hover = True
        if b_edit.collidepoint(mx, my): cursor_hover = True
        if b_fav.collidepoint(mx, my): cursor_hover = True
        
        b_minus = pygame.Rect(50, 200, 40, 40)
        b_plus = pygame.Rect(150, 200, 40, 40)
        if b_minus.collidepoint(mx, my): cursor_hover = True
        if b_plus.collidepoint(mx, my): cursor_hover = True

        if CACHE_SURFACE is None or sel != LAST_SEL:
            CACHE_SURFACE, CACHE_HEIGHT = prepare_details_surface(d, W-100)
            LAST_SEL = sel

        tags_rects = []

        for e in evs:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    if b_back.collidepoint(e.pos): etat = "menu"
                    if b_fav.collidepoint(e.pos): toggle_fav(sel, e.pos[0], e.pos[1])
                    if b_edit.collidepoint(e.pos): 
                        if open_recipe_editor(cat, sel):
                            CACHE_SURFACE = None
                    
                    if b_minus.collidepoint(e.pos) and PORTION_FACTOR > 0.5:
                        PORTION_FACTOR -= 0.5
                        CACHE_SURFACE = None
                    if b_plus.collidepoint(e.pos):
                        PORTION_FACTOR += 0.5
                        CACHE_SURFACE = None

                    for item in tags_rects:
                        if item["rect"].collidepoint(e.pos):
                            if item["type"] == "timer":
                                m = re.search(r"(\d+)", item["val"])
                                if m: start_timer(int(m.group(1)))
                            elif item["type"] == "tag":
                                etat = "menu"
                                mode = "tout"
                                inp_txt = item["val"]
                                cursor_pos = len(inp_txt)
                                res = recherche(mode, inp_txt, strict_mode)
                                res = reorder_results(res)
                                scroll_l = 0
                                target_scroll_l = 0

        # Molette Détails
        if e.type == pygame.MOUSEWHEEL: 
            view_h = H - 280
            max_scroll = max(0, CACHE_HEIGHT - view_h)
            target_scroll_d = max(0, min(target_scroll_d - e.y * 80, max_scroll))

        draw_btn(b_back, "Retour", b_back.collidepoint(mx,my))
        draw_btn(b_edit, "Edit", b_edit.collidepoint(mx,my))
        
        fav = sel in FAVORITES
        draw_card_bg(b_fav, C["card"], 8)
        heart_col = C["accent"] if fav else C["dim"]
        hx, hy = b_fav.centerx - 15, b_fav.centery - 15
        draw_heart(screen, hx, hy, 30, heart_col, filled=fav)
        if not fav:
            draw_heart(screen, hx, hy, 30, heart_col, filled=True)
            draw_heart(screen, hx+2, hy+2, 26, C["card"], filled=True)
        
        screen.blit(get_img(sel, 120, 120), (50, 70))
        screen.blit(font_L.render(sel, True, C["text"]), (190, 70))
        
        tx, ty = 190, 120
        if d.get("temps"): 
            w, r = draw_tag(tx, ty, f"Temps: {d['temps']}", C["blue"], True)
            tags_rects.append({"type": "timer", "val": d['temps'], "rect": r})
            tx += w
        if d.get("difficulte"): 
            w, r = draw_tag(tx, ty, f"Diff: {d['difficulte']}", C["bg"], False)
            tx += w
        
        for t in d.get("tags", []):
            w, r = draw_tag(tx, ty, t, C["card_hover"], clickable=True)
            if r.collidepoint(mx, my): cursor_hover = True
            tags_rects.append({"type": "tag", "val": t, "rect": r})
            tx += w
        
        for item in tags_rects:
            if item["type"] == "timer" and item["rect"].collidepoint(mx, my): cursor_hover = True

        draw_btn(b_minus, "-", b_minus.collidepoint(mx,my))
        draw_btn(b_plus, "+", b_plus.collidepoint(mx,my))
        
        lbl_p = font_bold.render(f"x{PORTION_FACTOR:g}", True, C["text"])
        screen.blit(lbl_p, lbl_p.get_rect(center=(120, 220)))

        content_rect = pygame.Rect(50, 260, W-100, H-280)
        draw_card_bg(content_rect, C["card"])
        
        screen.set_clip(content_rect.inflate(-20, -20))
        if CACHE_SURFACE:
            screen.blit(CACHE_SURFACE, (70, 280 - scroll_d))
        screen.set_clip(None)
        
        if CACHE_HEIGHT > content_rect.h:
            bar_h = (content_rect.h / CACHE_HEIGHT) * content_rect.h
            bar_y = content_rect.y + (scroll_d / CACHE_HEIGHT) * content_rect.h
            pygame.draw.rect(screen, C["accent"], (W-60, bar_y, 5, bar_h), border_radius=2)

    if cursor_hover: pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    else: pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    update_draw_particles()
    pygame.display.flip()
    clock.tick(60)