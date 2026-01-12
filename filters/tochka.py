from . import common
import re

def parse(df):
    data = []
    header_idx = -1
    col_map = {}
    
    # Точка: "Дата", "Контрагент", "Назначение", "Сумма" (иногда Дебет/Кредит)
    for i in range(min(20, len(df))):
        row = df.iloc[i].astype(str).tolist()
        row_str = " ".join(row).lower()
        if "дата" in row_str and ("сумма" in row_str or "дебет" in row_str):
            header_idx = i
            for idx, val in enumerate(row):
                v = val.lower()
                if "дата" in v: col_map['date'] = idx
                elif "назначение" in v or "контрагент" in v: 
                    # Если есть и то и то, лучше назначение. Но пока берем что первое нашли
                    if 'desc' not in col_map: col_map['desc'] = idx
                elif "сумма" in v: col_map['amount'] = idx
                elif "дебет" in v: col_map['debit'] = idx
                elif "кредит" in v: col_map['credit'] = idx
            break
            
    if header_idx == -1: return []

    for i in range(header_idx + 1, len(df)):
        row = df.iloc[i]
        d_idx = col_map.get('date', 0)
        if d_idx >= len(row): continue
        
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', str(row[d_idx]))
        if date_match:
            amount = 0.0
            desc = ""
            
            # Сумма (или Дебет-Кредит)
            if 'amount' in col_map:
                amount = common.normalize_money(row[col_map['amount']])
            else:
                # Если раздельно Дебет/Кредит
                deb = common.normalize_money(row[col_map.get('debit', -1)]) if 'debit' in col_map else 0
                cred = common.normalize_money(row[col_map.get('credit', -1)]) if 'credit' in col_map else 0
                amount = cred - deb if cred > 0 else -deb # Расход с минусом, приход с плюсом
            
            # Описание
            if 'desc' in col_map and col_map['desc'] < len(row):
                desc = str(row[col_map['desc']])
            
            if amount != 0:
                data.append({
                    "Дата": date_match.group(1),
                    "Описание": common.clean_text(desc),
                    "Сумма": amount
                })
    return data