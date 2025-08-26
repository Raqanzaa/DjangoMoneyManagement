from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from api.models import Budget
from datetime import date
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send budget alert notifications to users'

    def handle(self, *args, **options):
        today = date.today()
        
        # Get all active budgets
        active_budgets = Budget.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).select_related('user', 'category')
        
        alerts_sent = 0
        
        for budget in active_budgets:
            user_profile = getattr(budget.user, 'userprofile', None)
            
            # Check if user wants notifications
            if not user_profile or not user_profile.notification_preferences.get('budget_alerts', True):
                continue
            
            alert_sent = False
            
            # Check for over-budget condition
            if budget.is_over_budget:
                self.send_over_budget_alert(budget)
                alert_sent = True
            
            # Check for near-limit condition (and not already over budget)
            elif budget.is_near_limit:
                self.send_near_limit_alert(budget)
                alert_sent = True
            
            if alert_sent:
                alerts_sent += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Sent {alerts_sent} budget alert notifications')
        )

    def send_over_budget_alert(self, budget):
        """Send alert when budget is exceeded"""
        subject = f'⚠️ Budget Alert: {budget.category.name} Over Budget'
        
        message = f"""
        Hi {budget.user.first_name or budget.user.username},
        
        Your budget for "{budget.category.name}" has been exceeded.
        
        Budget Details:
        • Budget Amount: ${budget.amount:,.2f}
        • Amount Spent: ${budget.spent_amount:,.2f}
        • Over Budget By: ${budget.spent_amount - budget.amount:,.2f}
        • Period: {budget.start_date} to {budget.end_date}
        
        Consider reviewing your spending in this category or adjusting your budget.
        
        Best regards,
        Your Financial Management App
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[budget.user.email],
                fail_silently=False
            )
            
            self.stdout.write(
                self.style.WARNING(
                    f'Sent over-budget alert to {budget.user.email} for {budget.category.name}'
                )
            )
            
        except Exception as e:
            logger.error(f'Failed to send over-budget alert to {budget.user.email}: {str(e)}')

    def send_near_limit_alert(self, budget):
        """Send alert when approaching budget limit"""
        subject = f'💡 Budget Alert: {budget.category.name} Approaching Limit'
        
        percentage_used = budget.percentage_used
        
        message = f"""
        Hi {budget.user.first_name or budget.user.username},
        
        You're approaching your budget limit for "{budget.category.name}".
        
        Budget Status:
        • Budget Amount: ${budget.amount:,.2f}
        • Amount Spent: ${budget.spent_amount:,.2f}
        • Remaining: ${budget.remaining_amount:,.2f}
        • Usage: {percentage_used:.1f}% of budget used
        • Period: {budget.start_date} to {budget.end_date}
        
        Consider monitoring your spending in this category to stay within budget.
        
        Best regards,
        Your Financial Management App
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[budget.user.email],
                fail_silently=False
            )
            
            self.stdout.write(
                self.style.WARNING(
                    f'Sent near-limit alert to {budget.user.email} for {budget.category.name}'
                )
            )
            
        except Exception as e:
            logger.error(f'Failed to send near-limit alert to {budget.user.email}: {str(e)}')