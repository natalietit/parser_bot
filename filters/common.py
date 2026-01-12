import re
import pandas as pd

# --- ФУНКЦИЯ ОПРЕДЕЛЕНИЯ БАНКА ---
def detect_bank_smart(df, filename):
    fn = filename.lower()
    
    # 1. ПРОВЕРКА ПО ИМЕНИ ФАЙЛА
    if "сбер" in fn or "sber" in fn: return "СБЕРБАНК"
    if "выписка_по_сч" in fn and "дебет" in fn: return "СБЕРБАНК" 
    
    if "ozon" in fn or "озон" in fn: return "OZON БАНК"
    if "wildberries" in fn or "wb" in fn: return "WILDBERRIES"
    if "райф" in fn or "raiff" in fn: return "РАЙФФАЙЗЕН"
    if "газпром" in fn or "gpb" in fn: return "ГАЗПРОМБАНК"
    if "точк" in fn or "tochka" in fn: return "ТОЧКА"
    if "unicredit" in fn or "юникредит" in fn or "statement" in fn: return "ЮНИКРЕДИТ"
    if "alfa" in fn or "альфа" in fn: return "АЛЬФА-БАНК"
    
    # 2. ПРОВЕРКА ПО СОДЕРЖИМОМУ
    try:
        content = df.iloc[:60].to_string().lower()
        
        if "сбербанк" in content or "пао сбер" in content or "sberbank" in content: return "СБЕРБАНК"
        if "озон банк" in content or "ozon bank" in content: return "OZON БАНК"
        if "еком банк" in content or "ecom bank" in content: return "OZON БАНК"
        if "интернет решения" in content and "бик" in content: return "OZON БАНК"
        if "российские рубли" in content and "документ" in content: return "OZON БАНК"
        if "вайлдберриз" in content and "банк" in content: return "WILDBERRIES"
        if "альфа-банк" in content or "alfa-bank" in content: return "АЛЬФА-БАНК"
        if " rur" in content: return "АЛЬФА-БАНК"
        if "газпромбанк" in content or "банк гпб" in content: return "ГАЗПРОМБАНК"
        if "райффайзен" in content or "raiffeisen" in content: return "РАЙФФАЙЗЕН"
        if "сумма в валюте счета" in content: return "РАЙФФАЙЗЕН"
        if "юникредит" in content or "unicredit" in content or "prime visa" in content: return "ЮНИКРЕДИТ"
        if "банк точка" in content or "tochka" in content: return "ТОЧКА"
    except: pass
    
    return "СБЕРБАНК"


def normalize_money(value):
    """Превращает строку '1 234,56' в float."""
    if not value: return 0.0
    val = str(value)
    val = val.replace(' ', '').replace('\xa0', '').replace(',', '.')
    val = re.sub(r'[^\d.-]', '', val)
    try:
        return float(val)
    except ValueError:
        return 0.0


def clean_text(text):
    """Убирает переносы строк и лишние пробелы."""
    if not text: return ""
    text = str(text).replace('\n', ' ').replace('\r', ' ')
    return re.sub(r'\s+', ' ', text).strip()


# --- ДОБАВЛЯЕМ ОТСУТСТВУЮЩУЮ ФУНКЦИЮ ---
def is_garbage_row(date, amount, desc):
    """
    Проверяет, является ли строка мусором (например, нулевая сумма или неверная дата).
    """
    if amount == 0:
        return True
    
    # Проверка формата даты (DD.MM.YYYY)
    if not re.match(r'\d{2}\.\d{2}\.\d{4}', str(date)):
        return True
        
    return False