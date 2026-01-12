from . import common
import re

def parse(df):
    data = []
    
    # Регулярка для поиска даты в начале строки
    DATE_START = re.compile(r'^(\d{2}\.\d{2}\.\d{4})')
    
    # 1. Проход по всем строкам (Слепой метод, так как заголовки часто кривые)
    for i in range(len(df)):
        row = df.iloc[i].astype(str).tolist()
        
        # Первая колонка (Дата)
        c0 = str(row[0]).strip()
        
        # Если начинается с даты (07.11.2025...)
        date_match = DATE_START.search(c0)
        
        if date_match:
            date_val = date_match.group(1)
            amount = 0.0
            desc = ""
            
            # --- ИЩЕМ ДЕНЬГИ ---
            # Обычно это 3-я колонка (Сумма счета) или 2-я (Сумма операции)
            # В вашем файле: "+ 560,94 ₽"
            
            # Пробуем колонки 3, 2, 4
            for idx in [3, 2, 4]:
                if idx < len(row):
                    val = str(row[idx])
                    # Проверяем, есть ли там цифры
                    if any(char.isdigit() for char in val):
                        clean = common.normalize_money(val)
                        if clean != 0:
                            amount = clean
                            break
            
            # --- ИЩЕМ ОПИСАНИЕ ---
            # Обычно колонка 4
            if len(row) > 4:
                desc = str(row[4])
            
            # Если в 4-й пусто или 'nan', собираем из остальных
            if not common.clean_text(desc) or desc.lower() == 'nan':
                parts = []
                for k, cell in enumerate(row):
                    if k == 0: continue # Дата
                    c_txt = str(cell).strip()
                    # Не берем саму сумму
                    if common.normalize_money(c_txt) == amount and amount != 0: continue
                    
                    if c_txt and c_txt.lower() != 'nan':
                        parts.append(c_txt)
                desc = " ".join(parts)

            if amount != 0:
                data.append({
                    "Дата": date_val,
                    "Описание": common.clean_text(desc),
                    "Сумма": amount
                })
                
    return data