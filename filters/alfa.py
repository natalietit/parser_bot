from . import common
import re
import pandas as pd

def parse(df):
    data = []
    
    # 1. Регулярка "ЧИСЛО перед RUR"
    # Ищет: (плюс/минус) (цифры и пробелы) (точка/запятая) (2 цифры) (пробелы) (RUR или RUB)
    # Пример: "-2 532,30 RUR" или "883.00 RUR"
    AMOUNT_REGEX = re.compile(r'([\-\+]?[\d\s]+[.,]\d{2})\s*(?:RUR|RUB)', re.IGNORECASE)
    
    # 2. Регулярка для ДАТЫ
    DATE_REGEX = re.compile(r'(\d{2}\.\d{2}\.\d{2,4})')

    # --- ЧЕРНЫЙ СПИСОК (ФИЛЬТРЫ) ---
    # Строки, содержащие эти фразы, будут полностью игнорироваться.
    BLACKLIST = [
        "входящий остаток", 
        "исходящий остаток", 
        "платежный лимит", 
        "текущий баланс", 
        "общая задолженность", 
        "на дату формирования",
        "дата формирования",    # Ваш маркер
        "доступный лимит",
        "заблокировано",
        "всего поступлений",
        "всего списаний",
        "сальдо",
        "обороты за период",
        "валюта счета"          # Ваш маркер
    ]
    
    # Слова для жесткого начала строки (чтобы не удалить случайно "Поступления от Ивана")
    # Но в Альфе "Поступления" и "Расходы" в шапке обычно стоят в начале.
    # Добавим их в общий список проверки.
    BLACKLIST_EXACT = ["поступления", "расходы"]

    # Читаем все строки из 1-й колонки
    rows = [str(x).strip() for x in df.iloc[:, 0].tolist() if str(x).lower() != 'nan']
    
    for line in rows:
        line_lower = line.lower()
        
        # --- ФИЛЬТРАЦИЯ ---
        
        # 1. Проверка по общему черному списку (если фраза есть где угодно в строке)
        if any(b in line_lower for b in BLACKLIST):
            continue
            
        # 2. Проверка агрегатных сумм "Поступления" и "Расходы"
        # Проверяем, есть ли эти слова в строке. 
        # (Обычно в шапке это выглядит как "Поступления 1 500 000 RUR")
        if any(b in line_lower for b in BLACKLIST_EXACT):
            # Дополнительная защита: если это шапка, там обычно нет даты операции
            # Но лучше просто исключить, как вы просили.
            continue
            
        # 3. Фильтр заголовка неподтвержденных операций
        # "Неподтвержденные операции 4 809,16 RUR" -> Мусор
        # "HOLD Неподтвержденная операция..." -> Полезное
        if "неподтвержденные операции" in line_lower and "hold" not in line_lower:
            continue

        # --- ПОИСК ДЕНЕГ ---
        matches = list(AMOUNT_REGEX.finditer(line))
        
        for match in matches:
            raw_amount = match.group(1)
            amount = common.normalize_money(raw_amount)
            
            if amount == 0: continue
            
            # --- ПОИСК ДАТЫ ---
            date_val = ""
            date_search = DATE_REGEX.search(line)
            if date_search:
                date_val = date_search.group(1)
                # Исправляем год 25 -> 2025
                parts = date_val.split('.')
                if len(parts) == 3 and len(parts[2]) == 2:
                    date_val = f"{parts[0]}.{parts[1]}.20{parts[2]}"
            else:
                if "HOLD" in line: date_val = "HOLD"
            
            # --- ОПИСАНИЕ ---
            desc = line.replace(match.group(0), "")
            
            if date_val and date_val != "HOLD":
                desc = desc.replace(date_val, "")
                short_d = date_val[:-4] + date_val[-2:]
                desc = desc.replace(short_d, "")

            # Чистим мусорные слова
            garbage = ["HOLD", "Неподтвержденная операция:", "дата операции:", 
                       "дата предполагаемого", "снятия блокировки", "Vid", "CRD", ">"]
            for g in garbage:
                desc = desc.replace(g, "")
            
            # Убираем технические коды
            desc = re.sub(r'\b[A-Z0-9]{5,}\b', '', desc)
            
            desc = common.clean_text(desc)
            if len(desc) < 2: desc = "Транзакция Альфа-Банк"
            
            data.append({
                "Дата": date_val,
                "Описание": desc,
                "Сумма": amount
            })
            
    return data