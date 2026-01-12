import re

# === СПИСКИ ===
TRIGGER_KEEP_DETAILS = [
    "Перевод", "Снятие наличных", "Оплата товаров"
]

# === РЕГУЛЯРКИ ===
DATE_REGEX = re.compile(r'(\d{2}\.\d{2}\.\d{4})')
# Деньги в Озоне: точка как разделитель в исходнике (300 000.00)
MONEY_REGEX = re.compile(r'([+\-]?\s?\d[\d\s]*\.\d{2})\s*₽?') 
# Мусор в начале строки: Время и длинные ID
HEAD_JUNK_REGEX = re.compile(r'\b\d{2}:\d{2}:\d{2}\b|\b\d{8,}\b')

def parse(df):
    data = []
    raw_rows = df.iloc[:, 0].astype(str).tolist()
    
    # === 1. ГРУППИРОВКА СТРОК (БЛОКИ) ===
    blocks = []
    current_block = ""
    start_found = False 
    
    for line in raw_rows:
        line = line.strip()
        if not line or line.lower() == "nan": continue

        if re.match(r'^\d{2}\.\d{2}\.\d{4}', line):
            start_found = True
            if current_block:
                blocks.append(current_block)
            current_block = line
        else:
            if start_found: 
                current_block += " " + line
                
    if current_block:
        blocks.append(current_block)

    # === 2. ОБРАБОТКА БЛОКОВ ===
    for block in blocks:
        row = process_block(block)
        if row:
            data.append(row)

    # Сортировка: Старые -> Новые
    return data[::-1]

def process_block(text):
    dates = list(DATE_REGEX.finditer(text))
    moneys = list(MONEY_REGEX.finditer(text))
    
    if not dates or not moneys:
        return None

    # Дата операции
    date_str = dates[0].group(1)

    # --- ОПРЕДЕЛЯЕМ СУММУ ---
    plus_match = next((m for m in moneys if "+" in m.group(1)), None)
    minus_match = next((m for m in moneys if "-" in m.group(1)), None)
    
    amount_match = None
    is_income = False
    
    if plus_match:
        is_income = True
        amount_match = plus_match
    elif minus_match:
        is_income = False
        amount_match = minus_match
    else:
        amount_match = moneys[-1]
        is_income = False

    # Чистим сумму: убираем пробелы, знаки и МЕНЯЕМ ТОЧКУ НА ЗАПЯТУЮ
    amount_raw = amount_match.group(1)
    amount_clean = (
        amount_raw
        .replace(" ", "")
        .replace("+", "")
        .replace("-", "")
        .replace(".", ",") # Важно: меняем точку на запятую
    )

    # --- ВЫТАСКИВАЕМ ОПИСАНИЕ ---
    desc_start = dates[0].end()
    desc_end = amount_match.start()
    
    raw_desc = text[desc_start:desc_end].strip()
    
    # 1. Убираем "Мусор" в начале
    while True:
        match = HEAD_JUNK_REGEX.search(raw_desc)
        if match and match.start() < 5:
            raw_desc = raw_desc[match.end():].strip()
        else:
            break

    # 2. Убираем "хвост" с технической датой
    split_parts = re.split(r'\s+дата \d{4}-\d{2}-\d{2}', raw_desc)
    clean_desc = split_parts[0].strip()

    # 3. Убираем длинный номер перевода (буквы+цифры > 15 символов)
    clean_desc = re.sub(r'\b[A-Za-z0-9]{15,}\b', '', clean_desc)
    
    # Убираем лишние пробелы
    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip(" .")
    
    # Косметика для переводов
    clean_desc = clean_desc.replace("Перевод через", "Перевод через")

    if is_income:
        clean_desc += " +"

    return {
        "Дата": date_str,
        "Описание": clean_desc,
        "Сумма": amount_clean
    }