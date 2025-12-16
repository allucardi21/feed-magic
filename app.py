import streamlit as st
import os
import requests
import xml.etree.ElementTree as ET
from rembg import remove
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
from streamlit_image_coordinates import streamlit_image_coordinates

# --- НАЛАШТУВАННЯ ---
st.set_page_config(page_title="Magic Feed Editor", layout="wide")

# --- ІНІЦІАЛІЗАЦІЯ КООРДИНАТ (SESSION STATE) ---
# Ми зберігаємо всі позиції в пам'яті, щоб вони не збивалися
defaults = {
    'logo_x': 700, 'logo_y': 80, 'logo_sz': 200,
    'price_x': 700, 'price_y': 500, 'price_sz': 180,
    'title_x': 700, 'title_y': 750, 'title_sz': 95,
    'foot_l_x': 50, 'foot_l_y': 1240, 'foot_l_sz': 65,
    'foot_r_x': 600, 'foot_r_y': 1240, 'foot_r_sz': 65,
    'footer_h': 150
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- ФУНКЦІЇ ---
@st.cache_data
def load_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()

def clean_price(price_str):
    if not price_str: return "000"
    return price_str.replace('UAH', '').replace('uah', '').replace('грн', '').strip()

def download_image_to_memory(url):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except: return None
    return None

def draw_canvas(image_bytes, title, price, logo_bytes=None):
    # Константи
    W, H = 1080, 1350
    GRAY_W = int(W * 0.6)
    
    # Створюємо полотно
    canvas = Image.new('RGB', (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # Фони
    fh = st.session_state['footer_h']
    draw.rectangle([(0, 0), (GRAY_W, H - fh)], fill=(235, 235, 235))
    draw.rectangle([(0, H - fh), (W, H)], fill=(0, 0, 0))
    
    # 1. Товар
    try:
        if image_bytes:
            no_bg = remove(Image.open(image_bytes))
            bbox = no_bg.getbbox()
            if bbox: no_bg = no_bg.crop(bbox)
            
            padding = 50
            avail_w = GRAY_W - (padding * 2)
            avail_h = (H - fh) - (padding * 2)
            scale = min(avail_w / no_bg.width, avail_h / no_bg.height)
            new_w = int(no_bg.width * scale)
            new_h = int(no_bg.height * scale)
            product_img = no_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            x_prod = (GRAY_W - new_w) // 2
            y_prod = ((H - fh) - new_h) // 2
            canvas.paste(product_img, (x_prod, y_prod), product_img)
    except: pass

    font_file = "myfont.ttf" if os.path.exists("myfont.ttf") else None

    # 2. Логотип
    lx, ly, lsz = st.session_state['logo_x'], st.session_state['logo_y'], st.session_state['logo_sz']
    if logo_bytes:
        try:
            if isinstance(logo_bytes, bytes): logo_img = Image.open(io.BytesIO(logo_bytes))
            else: logo_img = Image.open(logo_bytes)
            
            base_width = lsz
            w_percent = (base_width / float(logo_img.size[0]))
            h_size = int((float(logo_img.size[1]) * float(w_percent)))
            logo_img = logo_img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            mask = logo_img if 'A' in logo_img.getbands() else None
            canvas.paste(logo_img, (lx, ly), mask)
        except: pass
    else:
        f_logo = load_font(font_file, lsz) # тут lsz як розмір шрифту
        draw.text((lx, ly), "BRAND", font=f_logo, fill=(30,30,30))

    # 3. Ціна
    px, py, psz = st.session_state['price_x'], st.session_state['price_y'], st.session_state['price_sz']
    f_price = load_font(font_file, psz)
    draw.text((px, py), f"{price} UAH", font=f_price, fill=(0,0,0))

    # 4. Назва
    tx, ty, tsz = st.session_state['title_x'], st.session_state['title_y'], st.session_state['title_sz']
    f_title = load_font(font_file, tsz)
    words = title.split()
    current_line = ""
    y_cursor = ty
    for word in words:
        test_line = current_line + word + " "
        bbox = draw.textbbox((0, 0), test_line, font=f_title)
        if (tx + bbox[2]) < (W - 20):
            current_line = test_line
        else:
            draw.text((tx, y_cursor), current_line, font=f_title, fill=(30,30,30))
            y_cursor += tsz + 10
            current_line = word + " "
    draw.text((tx, y_cursor), current_line, font=f_title, fill=(30,30,30))

    # 5. Футер
    f_footer = load_font(font_file, st.session_state['foot_l_sz']) # однаковий шрифт для обох
    
    # Лівий текст
    flx, fly = st.session_state['foot_l_x'], st.session_state['foot_l_y']
    draw.text((flx, fly), st.session_state.get('txt_foot_l', '🚚 FREE DELIVERY'), font=f_footer, fill=(255,255,255))
    
    # Правий текст
    frx, fry = st.session_state['foot_r_x'], st.session_state['foot_r_y']
    draw.text((frx, fry), st.session_state.get('txt_foot_r', '↩️ 30 DAYS'), font=f_footer, fill=(255,255,255))

    return canvas

# --- SIDEBAR UI ---
st.sidebar.header("🛠 Налаштування")
uploaded_logo = st.sidebar.file_uploader("Логотип (PNG)", type=['png', 'jpg'])

# Введення текстів футера
st.session_state['txt_foot_l'] = st.sidebar.text_input("Текст футера (зліва)", "🚚 FREE DELIVERY")
st.session_state['txt_foot_r'] = st.sidebar.text_input("Текст футера (справа)", "↩️ 30 DAYS")

st.sidebar.divider()
st.sidebar.subheader("Розміри елементів")
st.session_state['logo_sz'] = st.sidebar.number_input("Розмір Лого", 50, 500, st.session_state['logo_sz'])
st.session_state['price_sz'] = st.sidebar.number_input("Розмір Ціни", 50, 300, st.session_state['price_sz'])
st.session_state['title_sz'] = st.sidebar.number_input("Розмір Назви", 20, 150, st.session_state['title_sz'])
st.session_state['foot_l_sz'] = st.sidebar.number_input("Розмір Футера", 20, 100, st.session_state['foot_l_sz'])
st.session_state['footer_h'] = st.sidebar.slider("Висота чорної смуги", 50, 300, st.session_state['footer_h'])

# --- MAIN PAGE ---
st.title("Magic Feed Editor 🪄")

# Вибір режиму редагування
edit_target = st.radio(
    "🎯 Оберіть елемент, який хочете перемістити, і клікніть по картинці:",
    ["Логотип", "Ціна", "Назва", "Футер (ліво)", "Футер (право)"],
    horizontal=True
)

feed_url = st.text_input("XML Feed URL:", "")

if feed_url:
    if st.button("Завантажити"):
        try:
            r = requests.get(feed_url)
            st.session_state['root'] = ET.fromstring(r.content)
            st.session_state['items'] = list(st.session_state['root'].iter('item'))
            st.success("Фід завантажено!")
        except: st.error("Помилка фіда")

if 'items' in st.session_state and st.session_state['items']:
    st.divider()
    col1, col2 = st.columns([1, 2])
    
    item = st.session_state['items'][0]
    ns = {'g': 'http://base.google.com/ns/1.0'}
    
    try:
        title = item.find('g:title', ns).text
        img_url = item.find('g:image_link', ns).text
        price = clean_price(item.find('g:price', ns).text)
    except:
        title = "Sample Product Title"
        img_url = ""
        price = "1234"

    with col1:
        st.info("Оригінал")
        if img_url: st.image(img_url, width=200)
    
    with col2:
        st.write(f"👉 **Режим:** Переміщуємо **{edit_target}**. Клікніть на зображення!")
        
        img_bytes = download_image_to_memory(img_url)
        if img_bytes:
            # Малюємо картинку з поточними координатами
            if uploaded_logo: uploaded_logo.seek(0)
            final_img = draw_canvas(img_bytes, title, price, uploaded_logo)
            
            # Відслідковуємо клік
            clicked = streamlit_image_coordinates(final_img, width=500)
            
            if clicked:
                # Масштабуємо координати (екранні -> реальні)
                scale = 1080 / 500
                rx = int(clicked['x'] * scale)
                ry = int(clicked['y'] * scale)
                
                # Оновлюємо координати обраного елемента
                updated = False
                
                if edit_target == "Логотип":
                    # Центруємо лого по кліку
                    offset = st.session_state['logo_sz'] // 2
                    st.session_state['logo_x'] = rx - offset
                    st.session_state['logo_y'] = ry - offset
                    updated = True
                    
                elif edit_target == "Ціна":
                    st.session_state['price_x'] = rx
                    st.session_state['price_y'] = ry
                    updated = True
                    
                elif edit_target == "Назва":
                    st.session_state['title_x'] = rx
                    st.session_state['title_y'] = ry
                    updated = True
                
                elif edit_target == "Футер (ліво)":
                    st.session_state['foot_l_x'] = rx
                    st.session_state['foot_l_y'] = ry
                    updated = True

                elif edit_target == "Футер (право)":
                    st.session_state['foot_r_x'] = rx
                    st.session_state['foot_r_y'] = ry
                    updated = True
                
                if updated:
                    st.rerun()

    st.divider()
    if st.button("🚀 Згенерувати Архів (ZIP)"):
        progress_bar = st.progress(0)
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            items = st.session_state['items']
            for i, item in enumerate(items):
                try:
                    t = item.find('g:title', ns).text
                    im = item.find('g:image_link', ns).text
                    p = clean_price(item.find('g:price', ns).text)
                    
                    ib = download_image_to_memory(im)
                    if ib:
                        if uploaded_logo: uploaded_logo.seek(0)
                        res = draw_canvas(ib, t, p, uploaded_logo)
                        
                        fname = f"img_{i}.jpg"
                        buf = io.BytesIO()
                        res.save(buf, format='JPEG', quality=95)
                        zip_file.writestr(f"images/{fname}", buf.getvalue())
                except: pass
                progress_bar.progress((i + 1) / len(items))
        
        st.download_button("💾 СКАЧАТИ ZIP", zip_buffer.getvalue(), "feed.zip", "application/zip")
