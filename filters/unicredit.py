import re
from . import common

# Ищем дату DD.MM.YYYY
DATE_START = re.compile(r'(\d{2}\.\d{2}\.\d{4})')
# Ищем английские деньги: число, запятая, число, точка, 2 цифры (300,000.00)
# Или просто число точка 2 цифры (500.00)
MONEY_ENG = re.compile(r'([\d,]+\.\d{2})')

def parse(df):
    data = []
    # Читаем первую колонку как список строк
    rows = df.iloc[:, 0].astype(str).tolist()
    
    for line in rows:
        line = line.strip()
        if not line or line == "nan": continue
        
        # Строка начинается с даты?
        date_matches = list(DATE_START.finditer(line))
        if date_matches:
            # Обычно первая дата - проводки, вторая - операции. Берем первую.
            date_val = date_matches[0].group(1)
            
            # Ищем деньги в конце строки
            money_matches = list(MONEY_ENG.finditer(line))
            
            if money_matches:
                # В ЮниКредит строка: Дата ... Описание ... СуммаОриг СуммаВВалютеСчета
                # Берем ПОСЛЕДНЕЕ число (валюта счета)
                amount_str = money_matches[-1].group(1)
                
                # ВАЖНО: Принудительно считаем, что это английский формат (удаляем запятые)
                clean_amount_str = amount_str.replace(',', '')
                amount = 0.0
                try:
                    amount = float(clean_amount_str)
                    # Проверяем знак минуса перед числом в исходной строке
                    # Находим позицию числа в строке
                    start_pos = money_matches[-1].start()
                    if start_pos > 0 and line[start_pos-1] == '-':
                        amount = -amount
                    elif start_pos > 1 and line[start_pos-2:start_pos].strip() == '-':
                         amount = -amount
                except: pass
                
                # Описание: всё между датой и деньгами
                # Берем конец последней найденной даты
                desc_start = date_matches[-1].end()
                # Берем начало первого денежного числа (из последних двух, т.к. там Сумма и СуммаСчета)
                desc_end = money_matches[0].start() if len(money_matches) > 0 else len(line)
                
                # Если чисел несколько, берем начало предпоследнего (чтобы захватить валюту RUB если она есть)
                if len(money_matches) >= 2:
                     desc_end = money_matches[-2].start()
                
                desc = line[desc_start:desc_end].strip()
                # Убираем RUB/USD из описания, если приклеилось
                desc = re.sub(r'\b(RUB|USD|EUR)\b', '', desc).strip()

                if amount != 0:
                    data.append({
                        "Дата": date_val,
                        "Описание": desc,
                        "Сумма": amount
                    })
    return data