# Рефакторинг модуля handlers.py - Извлечение функций репетитора

## Описание

Выполнен рефакторинг большого файла `src/handlers.py` (2082+ строк) с извлечением всех функций репетитора в отдельный модуль `src/handlers/tutor.py`. Это улучшает организацию кода и облегчает его поддержку.

## Созданные файлы

### `src/handlers/tutor.py`
Новый модуль содержит все функции репетитора:

#### Управление учениками
- `show_student_list()` - показывает список всех учеников
- `show_student_profile()` - профиль конкретного ученика
- `tutor_add_student_start()` - начало добавления нового ученика
- `tutor_get_student_name()` - получение имени ученика
- `tutor_get_parent_code()` - создание ученика и родителя
- `tutor_edit_name_start()` - редактирование имени ученика
- `tutor_get_new_name()` - сохранение нового имени
- `tutor_add_parent_start()` - добавление родителя к ученику
- `tutor_get_parent_name()` - создание и привязка родителя
- `tutor_delete_student_start()` - запрос подтверждения удаления
- `tutor_delete_student_confirm()` - окончательное удаление ученика

#### Управление уроками
- `show_tutor_lessons()` - список уроков ученика
- `show_lesson_details()` - детали конкретного урока
- `tutor_add_lesson_start()` - создание нового урока
- `tutor_get_lesson_topic()` - получение темы урока
- `tutor_get_lesson_date()` - получение даты урока
- `tutor_get_lesson_skills()` - получение навыков и создание урока
- `tutor_edit_lesson_start()` - редактирование урока
- `tutor_edit_lesson_get_status()` - получение нового статуса
- `tutor_edit_lesson_get_comment()` - получение комментария
- `tutor_mark_lesson_attended()` - отметка о посещении (legacy)
- `tutor_set_lesson_attendance()` - установка статуса посещаемости
- `tutor_reschedule_lesson_start()` - перенос урока
- `tutor_reschedule_lesson_get_date()` - обработка новой даты
- `tutor_set_lesson_mastery()` - установка уровня усвоения

#### Управление домашними заданиями
- `tutor_add_hw_start()` - создание ДЗ
- `tutor_get_hw_description()` - получение описания ДЗ
- `tutor_get_hw_deadline()` - получение дедлайна
- `tutor_get_hw_link()` - получение ссылки
- `tutor_get_hw_photos()` - получение фотографий
- `tutor_finalize_homework()` - создание ДЗ с данными
- `tutor_check_homework()` - проверка ДЗ
- `tutor_set_homework_status()` - установка статуса ДЗ

#### Управление оплатами
- `tutor_add_payment_start()` - добавление оплаты
- `tutor_get_payment_amount()` - получение суммы и создание записи

#### Аналитика и отчеты
- `show_analytics_chart()` - генерация графика прогресса
- `show_tutor_dashboard()` - панель статистики
- `show_tutor_stats()` - алиас для dashboard
- `report_start()` - начало создания отчета
- `report_select_student()` - выбор ученика для отчета
- `report_select_month_and_generate()` - генерация отчета
- `report_cancel()` - отмена создания отчета

#### Управление библиотекой материалов
- `tutor_manage_library()` - интерфейс управления
- `tutor_add_material_start()` - добавление материала
- `tutor_get_material_title()` - получение названия
- `tutor_get_material_link()` - получение ссылки
- `tutor_get_material_description()` - получение описания
- `tutor_delete_material_start()` - список для удаления
- `tutor_delete_material_confirm()` - удаление материала

#### Система рассылки
- `broadcast_start()` - создание рассылки
- `broadcast_get_message()` - получение сообщения
- `broadcast_send()` - отправка рассылки
- `broadcast_cancel()` - отмена рассылки

#### Коммуникация
- `handle_tutor_reply()` - обработка ответов репетитора

#### Вспомогательные функции
- `generate_access_code()` - генерация кодов доступа
- `check_user_role()` - проверка роли пользователя
- `cancel_conversation()` - отмена диалогов
- `show_material_details()` - детали материала

### `src/handlers/__init__.py`
Обновленный файл для правильного экспорта всех функций из подмодулей.

### Константы и состояния ConversationHandler
Все необходимые константы перенесены в модуль:
- `TOPIC_MASTERY_RU` - перевод статусов усвоения
- `HOMEWORK_STATUS_RU` - перевод статусов ДЗ
- `ATTENDANCE_STATUS_RU` - перевод статусов посещаемости
- Состояния диалогов: `ADD_STUDENT_NAME`, `ADD_LESSON_TOPIC`, и т.д.

## Преимущества рефакторинга

1. **Лучшая организация кода** - функции репетитора логически сгруппированы
2. **Упрощение поддержки** - легче найти и изменить нужную функцию
3. **Модульность** - каждый модуль отвечает за свою область функциональности
4. **Масштабируемость** - проще добавлять новые функции в соответствующие модули
5. **Читаемость** - код стал более структурированным и понятным

## Совместимость

Модуль полностью совместим с существующим кодом благодаря:
- Правильному экспорту через `__init__.py`
- Сохранению всех сигнатур функций
- Сохранению всех импортов и зависимостей
- Корректной обработке состояний ConversationHandler

## Тестирование

Создан тестовый файл `test_tutor_module.py` для проверки корректности импорта всех функций. Все тесты пройдены успешно.

## Следующие шаги

1. Аналогично можно вынести функции студентов в `src/handlers/student.py`
2. Функции родителей в `src/handlers/parent.py`
3. Общие функции оставить в `src/handlers/common.py`

Это создаст четкую структуру модулей по ролям пользователей.