# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from .database import SessionLocal, Lesson, User, Homework, TopicMastery, HomeworkStatus
from sqlalchemy import func
import os

def generate_progress_chart(student_id: int):
    """
    Генерирует и сохраняет комплексный график прогресса ученика,
    включая динамику баллов и уровень усвоения тем.
    """
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            return None

        # 1. Собираем все события, влияющие на баллы, за всё время
        events = []
        
        # Уроки (посещение)
        attended_lessons = db.query(Lesson).filter(
            Lesson.student_id == student_id,
            Lesson.is_attended == True
        ).order_by(Lesson.date).all()
        for lesson in attended_lessons:
            events.append({'date': lesson.date, 'points': 10, 'label': 'Посещение урока'})

        # Уроки (закрепление темы)
        mastered_lessons = db.query(Lesson).filter(
            Lesson.student_id == student_id,
            Lesson.mastery_level == TopicMastery.MASTERED
        ).order_by(Lesson.date).all()
        for lesson in mastered_lessons:
            # Предполагаем, что дата события - это дата урока
            events.append({'date': lesson.date, 'points': 25, 'label': 'Тема закреплена'})

        # Проверенные ДЗ
        checked_homeworks = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student_id,
            Homework.status == HomeworkStatus.CHECKED,
            Homework.checked_at.isnot(None)
        ).order_by(Homework.checked_at).all()
        for hw in checked_homeworks:
            events.append({'date': hw.checked_at, 'points': 15, 'label': 'ДЗ принято'})

        if not events:
            return None

        # Сортируем все события по дате
        events.sort(key=lambda x: x['date'])

        # 2. Считаем кумулятивные баллы
        dates = [events[0]['date'] - timedelta(days=1)]
        cumulative_points = [0]
        current_points = 0
        for event in events:
            current_points += event['points']
            dates.append(event['date'])
            cumulative_points.append(current_points)
        
        # Убедимся, что последняя точка соответствует текущему общему количеству баллов
        if student.points != cumulative_points[-1]:
             # Это может произойти, если есть баллы, не связанные с событиями, или расхождения.
             # Добавляем текущее состояние как последнюю точку.
             dates.append(datetime.now())
             cumulative_points.append(student.points)


        # 3. Готовим данные для графика усвоения тем (за последние 90 дней для наглядности)
        ninety_days_ago = datetime.now() - timedelta(days=90)
        recent_lessons = db.query(Lesson).filter(
            Lesson.student_id == student_id,
            Lesson.date >= ninety_days_ago
        ).order_by(Lesson.date).all()
        
        lesson_dates = [l.date for l in recent_lessons]
        mastery_map = {
            TopicMastery.NOT_LEARNED: 1,
            TopicMastery.LEARNED: 2,
            TopicMastery.MASTERED: 3
        }
        mastery_levels = [mastery_map.get(l.mastery_level, 0) for l in recent_lessons]
        mastery_colors = [
            '#d9534f' if m == 1 else '#5bc0de' if m == 2 else '#5cb85c'
            for m in mastery_levels
        ]

        # 4. Стилизация и построение графика
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax1 = plt.subplots(figsize=(14, 8))

        # --- График баллов (левая ось Y) ---
        ax1.plot(dates, cumulative_points, color='#4a4a4a', linestyle='-', marker='', lw=2.5, label='Динамика баллов')
        ax1.set_xlabel('Дата', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Накопленные баллы', fontsize=12, fontweight='bold', color='#4a4a4a')
        ax1.tick_params(axis='y', labelcolor='#4a4a4a', labelsize=10)
        ax1.fill_between(dates, cumulative_points, color='#4a4a4a', alpha=0.1)

        # --- График усвоения (правая ось Y) ---
        ax2 = ax1.twinx()
        ax2.scatter(lesson_dates, mastery_levels, c=mastery_colors, s=100, alpha=0.8, edgecolors='black', linewidth=0.5, label='Усвоение тем')
        ax2.set_ylabel('Уровень усвоения темы', fontsize=12, fontweight='bold', color='navy')
        ax2.set_ylim(0.5, 3.5)
        ax2.set_yticks([1, 2, 3])
        ax2.set_yticklabels(['Не усвоено', 'Усвоено', 'Закреплено'], fontsize=10)
        ax2.tick_params(axis='y', colors='navy')
        
        # Добавляем маркеры для легенды
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='#4a4a4a', lw=2.5, label='Динамика баллов'),
            Line2D([0], [0], marker='o', color='w', label='Не усвоено', markerfacecolor='#d9534f', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Усвоено', markerfacecolor='#5bc0de', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Закреплено', markerfacecolor='#5cb85c', markersize=10)
        ]
        ax1.legend(handles=legend_elements, loc='upper left', fontsize=10)

        # --- Общие настройки ---
        plt.title(f'Комплексный отчет по прогрессу: {student.full_name}', fontsize=16, fontweight='bold', pad=20)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate() # Автоматический наклон дат
        
        ax1.grid(True, which='major', linestyle='--', linewidth='0.5', color='grey')
        fig.tight_layout()

        # 5. Сохранение файла
        chart_dir = "charts"
        if not os.path.exists(chart_dir):
            os.makedirs(chart_dir)
        chart_path = os.path.join(chart_dir, f"progress_chart_{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png")
        
        plt.savefig(chart_path, dpi=150)
        plt.close()
        
        return chart_path
    except Exception as e:
        # В реальном приложении здесь должно быть логирование
        print(f"Ошибка при генерации графика: {e}")
        return None
    finally:
        db.close()