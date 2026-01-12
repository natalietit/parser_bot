import re

# === СПИСКИ ===

# 1. Если встречаем это в первой части -> Ищем описание в ХВОСТЕ (desc2)
TRIGGER_KEEP_DETAILS = [
    "Перевод с карты", 
    "Перевод на карту", 
    "Перевод СБП", 
    "Оплата по QR-коду СБП", 
    "Оплата по QR–коду СБП", 
    "Прочие расходы", 
    "Прочие операции", 
    "Прочие выплаты",
    "Пополнение"
]

# 2. Если встречаем это в первой части -> Оставляем КАТЕГОРИЮ (из списка), хвост игнорируем
TRIGGER_USE_CATEGORY = [
    "Рестораны и кафе", 
    "Автомобиль", 
    "Супермаркеты", 
    "Здоровье и красота", 
    "Транспорт", 
    "Отдых и развлечения", 
    "Выдача наличных", 
    "Все для дома", 
    "Коммунальные платежи", 
    "Одежда и аксессуары",
    "Связь, телеком",
    "Фастфуд"
]

# === РЕГУЛЯРКИ ===
DATE_REGEX = re.compile(r'(\d{2}\.\d{2}\.\d{4})')
MONEY_REGEX = re.compile(r'([+\-]?\d[\d\s]*,\d{2})\b')
HEAD_JUNK_REGEX = re.compile(r'\b\d{2}:\d{2}\b|\b\d{6,8}\b')

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

        # Новая запись: начинается с Даты + содержит Деньги
        has_date_start = re.match(r'^\d{2}\.\d{2}\.\d{4}', line)
        has_money = MONEY_REGEX.search(line)
        is_new_record = has_date_start and has_money

        if is_new_record:
            start_found = True
            if current_block:
                blocks.append(current_block)
            current_block = line
        else:
            if start_found: 
                current_block += " " + line
                
    if current_block:
        blocks.append(current_block)

    # === 2. ОБРАБОТКА ===
    for block in blocks:
        row = process_block(block)
        if row:
            data.append(row)

    return data[::-1]

def process_block(text):
    dates = list(DATE_REGEX.finditer(text))
    moneys = list(MONEY_REGEX.finditer(text))
    
    if not dates or not moneys:
        return None

    first_date = dates[0]

    # --- СУММА ---
    plus_match = next((m for m in moneys if "+" in m.group(1)), None)
    if plus_match:
        is_income = True
        amount_match = plus_match
    else:
        is_income = False
        amount_match = moneys[-2] if len(moneys) >= 2 else moneys[0]

    amount_clean = (
        amount_match.group(1)
        .replace(" ", "")
        .replace("+", "")
        .replace("-", "")
    )

    # --- ОПИСАНИЕ 1 (Категория из начала) ---
    desc1_start = first_date.end()
    desc1_end = amount_match.start()
    desc1_raw = text[desc1_start:desc1_end]
    desc1 = HEAD_JUNK_REGEX.sub("", desc1_raw).strip()

    # --- ОПИСАНИЕ 2 (Хвост после последнего числа) ---
    last_money_end = moneys[-1].end()
    raw_tail = text[last_money_end:].strip()
    
    raw_tail = re.sub(r'^\d{2}\.\d{2}\.\d{4}\s*', '', raw_tail) # Удаляем дату в хвосте
    parts = re.split(r'\.?\s*[ОO]перация\s', raw_tail, flags=re.IGNORECASE)
    desc2 = parts[0].strip(" .,")

    # === ЛОГИКА ВЫБОРА (ИСПРАВЛЕНА) ===
    final_desc = desc1 # Значение по умолчанию
    
    # 1. ПРОВЕРКА НА ПЕРЕВОДЫ (Нужны детали)
    is_transfer = False
    for trig in TRIGGER_KEEP_DETAILS:
        if trig.lower() in desc1.lower():
            is_transfer = True
            break
            
    if is_transfer:
        # Если это перевод -> берем desc2 (детали), если они есть
        if desc2:
            final_desc = desc2
    else:
        # 2. ЭТО НЕ ПЕРЕВОД. ПРОВЕРЯЕМ, ЭТО КАТЕГОРИЯ?
        is_category = False
        for cat in TRIGGER_USE_CATEGORY:
            # Если описание начинается с категории (напр. "Рестораны и кафе")
            if desc1.lower().startswith(cat.lower()):
                final_desc = cat # Принудительно ставим чистую категорию
                is_category = True
                break
        
        # 3. ЕСЛИ ЭТО НЕ ПЕРЕВОД И НЕ КАТЕГОРИЯ ИЗ СПИСКА
        # (Например, просто название магазина, которого нет в списках)
        if not is_category:
            # Тогда берем хвост (обычно там название магазина), если он есть
            if desc2:
                final_desc = desc2

    if is_income:
        final_desc += " +"

    return {
        "Дата": first_date.group(1),
        "Описание": final_desc,
        "Сумма": amount_clean
    }