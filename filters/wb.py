from . import common
import re

def parse(df):
    data = []
    header_idx = -1
    col_map = {} 
    
    # 1. Поиск заголовков
    for i in range(min(50, len(df))):
        row = df.iloc[i].astype(str).tolist()
        row_str = " ".join(row).lower()
        if ("дебет" in row_str or "кредит" in row_str) and "дата" in row_str:
            header_idx = i
            for idx, val in enumerate(row):
                col_map[idx] = val.lower()
            break
            
    if header_idx == -1: return [] 
    
    # 2. Чтение
    for i in range(header_idx + 1, len(df)):
        row = df.iloc[i]
        row_str = " ".join(row.astype(str))
        
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', row_str)
        if date_match:
            amount = 0.0
            desc = ""
            
            for col_idx, cell_val in enumerate(row):
                header = col_map.get(col_idx, "")
                val_str = str(cell_val)
                
                if "назначение" in header: desc = val_str
                if "остаток" in header or "balance" in header: continue
                
                if "дебет" in header or "кредит" in header or "сумма" in header:
                    try:
                        v = common.normalize_money(val_str)
                        if v > 0: amount = v
                    except: pass
            
            if amount > 0:
                data.append({
                    "Дата": date_match.group(1),
                    "Описание": common.clean_text(desc),
                    "Сумма": amount
                })
    return data