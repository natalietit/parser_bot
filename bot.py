import os
import logging
import traceback  # <--- Добавили для вывода ошибок
import pandas as pd
import pdfplumber
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters as tg_filters

# === ИМПОРТ ФИЛЬТРОВ ===
# Если тут падает ошибка, значит нет __init__.py в папке filters
try:
    from filters import common, sber, wb, ozon, raif, gpb, tochka, unicredit, alfa
    print("✅ Фильтры успешно загружены")
except ImportError as e:
    print(f"❌ ОШИБКА ИМПОРТА ФИЛЬТРОВ: {e}")
    print("Убедитесь, что в папке 'filters' есть файл '__init__.py'")

TOKEN = "8168590811:AAEQ3LifuaQYyBgifdqGmrp2yQSK3N_J__4"  # <--- НЕ ЗАБУДЬ ВСТАВИТЬ ТОКЕН

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def pdf_to_df(pdf_path):
    text_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_lines.extend(text.split('\n'))
            
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    clean_row = [str(cell) if cell else "" for cell in row]
                    text_lines.append(" ".join(clean_row))
    return pd.DataFrame(text_lines)

def process_bank_file(input_path, output_path):
    print(f"📂 Начало обработки файла: {input_path}")
    
    # 1. Читаем файл
    try:
        if input_path.lower().endswith('.pdf'):
            df = pdf_to_df(input_path)
        else:
            # Тут может упасть, если нет openpyxl
            df = pd.read_excel(input_path, header=None)
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return f"Не могу прочитать файл. Ошибка: {e}"

    if df.empty:
        return "Файл пустой."

    # 2. Определяем банк
    try:
        filename = os.path.basename(input_path)
        bank_name = common.detect_bank_smart(df, filename)
        print(f"🏦 Банк определен как: {bank_name}")
    except Exception as e:
        print(f"❌ Ошибка в common.detect_bank_smart: {e}")
        traceback.print_exc()
        return "Ошибка при определении банка."

    # 3. Применяем фильтр
    try:
        rows = []
        if bank_name == "СБЕРБАНК": rows = sber.parse(df)
        elif bank_name == "WILDBERRIES": rows = wb.parse(df)
        elif bank_name == "OZON БАНК": rows = ozon.parse(df)
        elif bank_name == "РАЙФФАЙЗЕН": rows = raif.parse(df)
        elif bank_name == "ГАЗПРОМБАНК": rows = gpb.parse(df)
        elif bank_name == "ТОЧКА": rows = tochka.parse(df)
        elif bank_name == "ЮНИКРЕДИТ": rows = unicredit.parse(df)
        elif bank_name == "АЛЬФА-БАНК": rows = alfa.parse(df)
        else:
            rows = sber.parse(df)
    except Exception as e:
        print(f"❌ Ошибка внутри парсера {bank_name}: {e}")
        traceback.print_exc()
        return f"Сбой парсера банка {bank_name}."

    if not rows:
        return f"Банк {bank_name}: Транзакции не найдены."

    # 4. Сохраняем
    try:
        clean_df = pd.DataFrame(rows)
        if not clean_df.empty and "Дата" in clean_df.columns:
            clean_df = clean_df[["Дата", "Описание", "Сумма"]]
        
        clean_df.to_excel(output_path, index=False)
        print(f"✅ Файл сохранен: {output_path}")
        return "OK"
    except Exception as e:
        print(f"❌ Ошибка сохранения Excel: {e}")
        return "Не удалось сохранить итоговый файл."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот готов! Пришлите файл.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_name = update.message.document.file_name
    await update.message.reply_text("⏳ Думаю...")

    input_path = f"temp_{file_name}"
    # Генерируем имя, очищая его от пробелов, чтобы избежать проблем
    safe_name = os.path.splitext(file_name)[0].replace(" ", "_")
    output_path = f"CLEAN_{safe_name}.xlsx"

    try:
        await file.download_to_drive(input_path)
        result_msg = process_bank_file(input_path, output_path)
        
        if result_msg == "OK":
            # ИСПРАВЛЕНИЕ ЗДЕСЬ: Используем with, чтобы файл закрылся сам
            with open(output_path, 'rb') as f:
                await update.message.reply_document(document=f)
        else:
            await update.message.reply_text(f"⚠️ {result_msg}")

    except Exception as e:
        print(f"❌ Глобальная ошибка: {e}")
        traceback.print_exc()
        await update.message.reply_text("Произошла системная ошибка.")
        
    finally:
        # Теперь удаление сработает, так как файл уже закрыт блоком with
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except Exception:
                pass # Если не удалился - не страшно
                
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(tg_filters.Document.ALL, handle_document))
    
    print("🚀 Бот запущен в режиме отладки...")
    application.run_polling()