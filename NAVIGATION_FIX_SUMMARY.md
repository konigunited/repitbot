# ✅ Исправление ошибки "There is no text in the message to edit"

## 🔧 Проблема:
При генерации графика родительского интерфейса отправлялось фото-сообщение, а затем при нажатии кнопки "Назад к ребенку" система пыталась отредактировать это фото-сообщение как текст, что вызывало ошибку.

## 💡 Решение:
Создана универсальная функция `safe_edit_or_reply()` которая:

1. **Проверяет тип сообщения** - есть ли в нем текст
2. **Если текст есть** - редактирует сообщение обычным способом  
3. **Если текста нет** (фото, документ и т.д.) - удаляет старое сообщение и отправляет новое
4. **При ошибках** - использует fallback методы отправки

## 🔧 Внесенные изменения:

### 1. **Добавлена функция `safe_edit_or_reply()`**
```python
async def safe_edit_or_reply(update, text, reply_markup=None, parse_mode=None):
    """Безопасно редактирует сообщение или отправляет новое"""
    try:
        if update.callback_query.message.text:
            await update.callback_query.edit_message_text(...)
        else:
            # Удаляем фото и отправляем новое текстовое сообщение
            await update.callback_query.message.delete()
            await update.callback_query.message.reply_text(...)
    except Exception as e:
        # Fallback варианты при ошибках
        ...
```

### 2. **Заменены все `edit_message_text()` на `safe_edit_or_reply()`**
- ✅ `show_child_menu()` - меню ребенка
- ✅ `show_child_progress()` - прогресс ребенка  
- ✅ `parent_generate_chart()` - генерация графиков

## 📊 Результат тестирования:

### Тест функции безопасного редактирования:
```
Test 1: Message with text
  edit_message_text: Test message with text...

Test 2: Message without text (photo)  
  message deleted
  reply_text: Test message after photo...

SUCCESS: safe_edit_or_reply works correctly
```

### Тест навигации после графика:
```
Simulating navigation from photo message to child menu...
  photo message deleted
  new message sent: **Ваня Иванович**...
  callback answered

SUCCESS: Navigation after chart works
```

## 🎯 **СТАТУС: ПОЛНОСТЬЮ ИСПРАВЛЕНО!**

### ✅ Что теперь работает:
1. **Генерация графиков** - отправляется фото с графиком
2. **Навигация из графика** - кнопка "Назад к ребенку" корректно работает
3. **Универсальная совместимость** - функция работает с любыми типами сообщений
4. **Обработка ошибок** - fallback механизмы при сбоях

### 🚀 Пользователи больше не увидят ошибку:
❌ `"There is no text in the message to edit"`

Все переходы в родительском интерфейсе теперь работают безупречно!