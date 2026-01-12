from . import common
import re

def parse(df):
    data = []
    header_idx = -1
    col_map = {}
    
    # 1. Попытка найти заголовки
    for i in range(min(40, len(df))):
        row = df.iloc[i].astype(str).tolist()
        row_str = " ".join(row).lower()
        if "дата" in row_str and ("сумма" in row_str or "списание" in row_str):
            header_idx = i
            for idx, val in enumerate(row):
                v = val.lower()
                if "дата" in v and "совершения" in v: col_map['date'] = idx
                elif "сумма" in v and "операции" in v: col_map['amount'] = idx
                elif "описание" in v: col_map['desc'] = idx
            break
            
    # 2. Если заголовки не найдены, используем жесткую структуру ГПБ (она стабильная)
    # Обычно: Col 0 (Дата), Col 2 (Описание), Col 3 (Приход), Col 4 (Расход)
    if header_idx == -1:
        # Проверяем гипотезу на первых строках с данными
        # Ищем строку, где в 0-й колонке дата
        start_row = -1
        for i in range(min(50, len(df))):
            val = str(df.iloc[i, 0])
            if re.search(r'\d{2}\.\d{2}\.\d{4}', val):
                start_row = i
                break
        
        if start_row != -1:
            # Читаем по жестким индексам
            for i in range(start_row, len(df)):
                row = df.iloc[i]
                if len(row) < 5: continue
                
                date_val = str(row[0])
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_val)
                
                if date_match:
                    # В ГПБ часто две колонки с деньгами (пополнение и списание)
                    # Col 3 (+0,00), Col 4 (-34 000,00)
                    amount = 0.0
                    
                    try:
                        v3 = common.normalize_money(row[3])
                        v4 = common.normalize_money(row[4])
                        # Складываем (обычно одно 0, второе со значением)
                        amount = v3 + v4 
                    except: pass
                    
                    desc = str(row[2]) # Описание обычно в 3-й колонке (индекс 2)
                    
                    if amount != 0:
                        data.append({
                            "Дата": date_match.group(1),
                            "Описание": common.clean_text(desc),
                            "Сумма": amount
                        })
            return data

    # 3. Если заголовки были найдены (редкий случай для этого PDF)
    for i in range(header_idx + 1, len(df)):
        row = df.iloc[i]
        d_idx = col_map.get('date', 0)
        if d_idx >= len(row): continue
        
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', str(row[d_idx]))
        if date_match:
            amount = 0.0
            desc = ""
            
            a_idx = col_map.get('amount', -1)
            if a_idx != -1 and a_idx < len(row):
                amount = common.normalize_money(row[a_idx])
            
            d_desc_idx = col_map.get('desc', -1)
            if d_desc_idx != -1 and d_desc_idx < len(row):
                desc = str(row[d_desc_idx])
            
            if amount != 0:
                data.append({
                    "Дата": date_match.group(1),
                    "Описание": common.clean_text(desc),
                    "Сумма": amount
                })
    return data