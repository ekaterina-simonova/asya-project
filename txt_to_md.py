import re

def clean_product_text(text):
    """Очищает текст от навигации и дубликатов"""
    # Убираем навигационные ссылки
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Пропускаем строки с навигацией
        if any(nav in line for nav in [
            'Продукция', 'Огнезащита', 'Воздуховодов', 'Металлоконструкций', 
            'Мастика', 'Услуги', 'Поддержка', 'Блог', 'Поиск', 'Производство',
            'Объекты', 'Энергетика', 'Судостроение', 'Частное домостроение',
            'Проектировщикам', 'Монтажникам', 'Снабженцам', 'Нормативные документы',
            'Полезные статьи', 'Применяемые на данном интернет-сайте'
        ]):
            continue
        # Пропускаем пустые строки
        if not line:
            continue
        # Пропускаем строки с "Купить на OZON"
        if 'Купить на OZON' in line:
            continue
        # Пропускаем строки с дублированными заголовками
        if line.startswith('Описание') or line.startswith('Преимущества') or \
           line.startswith('Технические характеристики') or line.startswith('Инструкция'):
            continue
            
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def extract_title(text):
    """Извлекает заголовок продукта"""
    match = re.search(r'^\d*\.\s*(.+)', text.strip())
    if match:
        return match.group(1)
    match = re.search(r'#\s*(.+)', text)
    if match:
        return match.group(1)
    return "Продукт"

def extract_contacts(text):
    """Извлекает контакты"""
    urls = re.findall(r'https?://[^\s]+', text)
    phones = re.findall(r'\+7\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2}', text)
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return urls, phones, emails

def extract_description(text):
    """Извлекает описание и характеристики"""
    # Убираем заголовок, контакты и лишнее
    lines = text.split('\n')
    desc_lines = []
    
    in_description = False
    for line in lines:
        if any(keyword in line for keyword in [
            'Шнур применяется', 'Обрезь – это', 'Маты прошивные',
            'Универсальность', 'Экологичность', 'Прочность', 'Пожаробезопасность'
        ]):
            in_description = True
        
        if in_description and not any(skip in line for skip in [
            'https://', '+7 (', 'crm@', 'Сертификаты:', 'Производится в соответствии',
            'Срок годности', 'При транспортировке'
        ]):
            desc_lines.append(line)
    
    return '\n'.join(desc_lines).strip()

def extract_specs(text):
    """Извлекает технические характеристики"""
    specs = []
    
    # Ищем таблицы
    table_match = re.search(r'\|.*\|\s*\|.*\|', text, re.DOTALL)
    if table_match:
        specs.append(table_match.group(0))
    
    # Ищем списки характеристик
    spec_lines = re.findall(r'(.*?:\s*[-+\d\s,°СВтмК%]+)', text)
    if spec_lines:
        specs.extend(spec_lines)
    
    return specs

def convert_to_markdown(input_file, output_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Разделяем по ===PRODUCT===
        product_blocks = re.split(r'={3,}PRODUCT={3,}', content)
        product_blocks = [b.strip() for b in product_blocks if b.strip()]
        
        markdown_parts = ["# Продукты компании\n\n"]
        
        for i, block in enumerate(product_blocks, 1):
            # Очищаем блок
            clean_block = clean_product_text(block)
            if not clean_block:
                continue
            
            # Извлекаем данные
            title = extract_title(clean_block)
            urls, phones, emails = extract_contacts(clean_block)
            description = extract_description(clean_block)
            specs = extract_specs(clean_block)
            
            # Формируем Markdown
            markdown_parts.append(f"## {i}. {title}\n\n")
            
            # Контакты
            for url in urls:
                markdown_parts.append(f"🔗 [Ссылка на продукт]({url})\n\n")
            
            for phone in phones:
                markdown_parts.append(f"📞 **{phone}** — звонок по России бесплатный\n\n")
            
            for email in emails:
                markdown_parts.append(f"📧 {email}\n\n")
            
            # Описание
            if description:
                # Разбиваем на абзацы
                paragraphs = re.split(r'\n\s*\n', description)
                for para in paragraphs:
                    para = para.strip()
                    if para and not para.startswith('#') and len(para) > 20:
                        markdown_parts.append(f"{para}\n\n")
            
            # Характеристики
            if specs:
                markdown_parts.append("### Технические характеристики\n\n")
                for spec in specs:
                    if '|' in spec:  # Таблица
                        markdown_parts.append(f"{spec}\n\n")
                    else:  # Текст
                        markdown_parts.append(f"- {spec}\n")
                markdown_parts.append("\n")
            
            markdown_parts.append("---\n\n")
        
        # Сохраняем
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(''.join(markdown_parts))
        
        print(f"✅ Преобразовано {len([p for p in product_blocks if p.strip()])} продуктов")
        print(f"📁 Результат сохранён в: {output_file}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# Использование
convert_to_markdown('products.txt', 'products.md')