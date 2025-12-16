import streamlit as st
import os
import requests
import xml.etree.ElementTree as ET
from rembg import remove
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="Magic Feed Generator", layout="wide")

# --- ФУНКЦІЇ ---

@st.cache_data
def load_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()

def clean_price(price_str):
    if not price_str: return None
    cleaned = price_str.replace('UAH', '').replace('uah', '').replace('грн', '').strip()
    return cleaned

def download_image_to_memory(url):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except:
        return None
    return None

def process_single_image(image_bytes, title, price, settings, logo_bytes=None):
    # Константи з налаштувань
    W, H = 1080, 1350
    GRAY_W = int(W * 0.6)
    
    # Створення полотна
    canvas = Image.new('RGB', (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # Фони
    draw.rectangle([(0, 0), (GRAY_W, H - settings['footer_height'])], fill=(235, 235, 235))
    draw.rectangle([(0, H - settings['footer_height']), (W, H)], fill=(0, 0, 0)) # Footer
    
    # 1. Товар (Видалення фону + вставка)
    try:
        original = Image.open(image_bytes)
        no_bg = remove(original)
        bbox = no_bg.getbbox()
        if bbox: no_bg = no_bg.crop(bbox)
        
        # Масштабування
        padding = 50
        avail_w = GRAY_W - (padding * 2)
        avail_h = (H - settings['footer_height']) - (padding * 2)
        
        scale = min(avail_w / no_bg.width, avail_h / no_bg.height)
        new_w = int(no_bg.width * scale)
        new_h = int(no_bg.height * scale)
        product_img = no_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Центрування в сірій зоні
        x_prod = (GRAY_W - new_w) // 2
        y_prod = ((H - settings['footer_height']) - new_h) // 2
        canvas.paste(product_img, (x_prod, y_prod), product_img)
    except Exception as e:
        st.error(f"Error processing image: {e}")

    # 2. Тексти та Лого
    font_file = "myfont.ttf" if os.path.exists("myfont.ttf") else None
    
    # --- ЛОГОТИП ---
    if logo_bytes:
        try:
            logo_img = Image.open(logo_bytes)
            # Масштабування лого (settings['logo_size'] тут виступає як ширина)
            base_width = settings['logo_size']
            w_percent = (base_width / float(logo_img.size[0]))
            h_size = int((float(logo_img.size[1]) * float(w_percent)))
            logo_img = logo_img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            
            # Вставка з урахуванням прозорості (mask=logo_img if png)
            mask = logo_img if 'A' in logo_img.getbands() else None
            canvas.paste(logo_img, (settings['text_x'], settings['logo_y']), mask)
        except Exception as e:
            st.error(f"Error loading logo: {e}")
    else:
        # Старий варіант (Текст)
        f_logo = load_font(font_file, settings['logo_size']) # Тут це розмір шрифту
        draw.text((settings['text_x'], settings['logo_y']), "BRAND", font=f_logo, fill=(30,30,30))
    
    # Ціна
    f_price = load_font(font_file, settings['price_size'])
    draw.text((settings['text_x'], settings['price_y']), f"{price} UAH", font=f_price, fill=(0,0,0))
    
    # Назва
    f_title = load_font(font_file, settings['title_size'])
    # Простий перенос слів
    words = title.split()
    current_line = ""
    y_text = settings['title_y']
    for word in words:
        test_line = current_line + word + " "
        bbox = draw.textbbox((0, 0), test_line, font=f_title)
        if (settings['text_x'] + bbox[2]) < (W - 20):
            current_line = test_line
        else:
            draw.text((settings['text_x'], y_text), current_line, font=f_title, fill=(30,30,30))
            y_text += settings['title_size'] + 10
            current_line = word + " "
    draw.text((settings['text_x'], y_text), current_line, font=f_title, fill=(30,30,30))
    
    # Футер
    f_footer = load_font(font_file, settings['footer_size'])
    
    draw.text((settings['footer_text_left_x'], H - settings['footer_height'] + 40), 
              settings['footer_text_left'], font=f_footer, fill=(255,255,255))
              
    draw.text((settings['footer_text_right_x'], H - settings['footer_height'] + 40), 
              settings['footer_text_right'], font=f_footer, fill=(255,255,255))
              
    return canvas

# --- ІНТЕРФЕЙС (SIDEBAR) ---
st.sidebar.header("⚙️ Налаштування")

# Завантаження логотипа
uploaded_logo = st.sidebar.file_uploader("🖼️ Завантажити Логотип (PNG)", type=['png', 'jpg', 'jpeg'])

settings = {}
settings['text_x'] = st.sidebar.slider("Відступ контенту зліва (X)", 600, 1000, 700)

st.sidebar.subheader("Логотип")
settings['logo_y'] = st.sidebar.slider("Позиція Лого (Y)", 0, 500, 80)
# Якщо є лого, це ширина в px. Якщо немає - розмір шрифту.
settings['logo_size'] = st.sidebar.number_input("Розмір Лого (Ширина/Шрифт)", 50, 500, 200)

st.sidebar.subheader("Ціна")
settings['price_y'] = st.sidebar.slider("Позиція Ціни (Y)", 0, 1000, 500)
settings['price_size'] = st.sidebar.number_input("Розмір шрифту Ціни", 50, 300, 180)

st.sidebar.subheader("Назва товару")
settings['title_y'] = st.sidebar.slider("Позиція Назви (Y)", 0, 1200, 750)
settings['title_size'] = st.sidebar.number_input("Розмір шрифту Назви", 20, 150, 95)

st.sidebar.subheader("Футер")
settings['footer_height'] = st.sidebar.slider("Висота футера", 50, 300, 150)
settings['footer_size'] = st.sidebar.number_input("Розмір шрифту футера", 20, 100, 65)
settings['footer_text_left'] = st.sidebar.text_input("Текст зліва", "🚚 FREE DELIVERY")
settings['footer_text_left_x'] = st.sidebar.slider("X зліва", 0, 500, 50)
settings['footer_text_right'] = st.sidebar.text_input("Текст справа", "↩️ 30 DAYS")
settings['footer_text_right_x'] = st.sidebar.slider("X справа", 500, 1000, 600)

# --- ОСНОВНА ЧАСТИНА ---
st.title("Magic Feed Generator 🪄")

feed_url = st.text_input("Вставте посилання на XML фід:", "")

if feed_url:
    if st.button("📥 Завантажити Фід"):
        try:
            r = requests.get(feed_url)
            root = ET.fromstring(r.content)
            items = list(root.iter('item'))
            st.success(f"Знайдено {len(items)} товарів!")
            st.session_state['items'] = items
            st.session_state['root'] = root
        except Exception as e:
            st.error(f"Помилка: {e}")

# PREVIEW
if 'items' in st.session_state and len(st.session_state['items']) > 0:
    st.divider()
    st.subheader("👁️ Попередній перегляд")
    
    item = st.session_state['items'][0]
    ns = {'g': 'http://base.google.com/ns/1.0'}
    
    # Спробуємо знайти поля з namespace або без
    try:
        title = item.find('g:title', ns).text
        img_node = item.find('g:image_link', ns)
        price_node = item.find('g:price', ns)
        
        # Fallback якщо namespace не спрацював
        if title is None: title = item.find('title').text
        if img_node is None: img_node = item.find('image_link')
        if price_node is None: price_node = item.find('price')

        image_url = img_node.text
        price = clean_price(price_node.text)
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("Оригінал")
            st.image(image_url, width=300)
            
        with col2:
            st.success("Результат")
            img_bytes = download_image_to_memory(image_url)
            if img_bytes:
                # ПЕРЕДАЄМО UPLOADED_LOGO
                processed_img = process_single_image(img_bytes, title, price, settings, uploaded_logo)
                st.image(processed_img, width=300)
            else:
                st.error("Не вдалося завантажити фото")
                
    except Exception as e:
        st.error(f"Помилка читання товару: {e}")

    # BUTTON TO RUN ALL
    st.divider()
    if st.button("🚀 ОБРОБИТИ ВСІ ТОВАРИ (ZIP)"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            items = st.session_state['items'] # [:5] # Зніміть комент [:5] для тесту
            
            for i, item in enumerate(items):
                try:
                    # Повтор пошуку полів (можна винести в функцію)
                    title = item.find('g:title', ns).text
                    img_node = item.find('g:image_link', ns)
                    price = clean_price(item.find('g:price', ns).text)
                    
                    status_text.text(f"Обробка {i+1}/{len(items)}")
                    
                    img_bytes = download_image_to_memory(img_node.text)
                    if img_bytes:
                        # Передаємо логотип (якщо він є, треба зчитати байт з початку)
                        if uploaded_logo: uploaded_logo.seek(0)
                        
                        res = process_single_image(img_bytes, title, price, settings, uploaded_logo)
                        
                        fname = f"img_{i}.jpg"
                        buf = io.BytesIO()
                        res.save(buf, format='JPEG', quality=95)
                        zip_file.writestr(f"images/{fname}", buf.getvalue())
                        
                        # Оновлюємо лінк (приклад)
                        img_node.text = f"https://YOUR-SITE/images/{fname}"
                except:
                    pass
                progress_bar.progress((i + 1) / len(items))
            
            xml_str = ET.tostring(st.session_state['root'], encoding='utf8', method='xml')
            zip_file.writestr("new_feed.xml", xml_str)

        st.download_button(
            "💾 СКАЧАТИ ZIP",
            data=zip_buffer.getvalue(),
            file_name="feed_images.zip",
            mime="application/zip"
        )
