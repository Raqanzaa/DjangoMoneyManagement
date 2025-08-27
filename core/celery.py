from celery.schedules import crontab

app.conf.beat_schedule = {
    'process-recurring-transactions': {
        'task': 'api.tasks.process_recurring_transactions',
        'schedule': crontab(hour=0, minute=30),  # Daily at 12:30 AM
    },
    'send-budget-alerts': {
        'task': 'api.tasks.send_budget_alerts',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9:00 AM
    },
    'generate-monthly-reports': {
        'task': 'api.tasks.generate_monthly_reports',
        'schedule': crontab(hour=8, minute=0, day_of_month=1),  # 1st of month at 8:00 AM
    },
}