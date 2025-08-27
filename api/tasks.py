from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from .models import Budget, Goal, RecurringTransaction, Transaction
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_recurring_transactions():
    """Process all due recurring transactions"""
    from django.core.management import call_command
    call_command('process_recurring')
    return "Recurring transactions processed successfully"

@shared_task
def send_budget_alerts():
    """Send budget alert notifications"""
    from django.core.management import call_command
    call_command('send_budget_alerts')
    return "Budget alerts sent successfully"

@shared_task
def generate_monthly_reports():
    """Generate and send monthly financial reports to users"""
    today = date.today()
    
    # First day of previous month
    if today.month == 1:
        prev_month_start = date(today.year - 1, 12, 1)
        prev_month_end = date(today.year, 1, 1) - timedelta(days=1)
    else:
        prev_month_start = date(today.year, today.month - 1, 1)
        prev_month_end = date(today.year, today.month, 1) - timedelta(days=1)
    
    users_processed = 0
    
    for user in User.objects.filter(is_active=True):
        try:
            # Check if user wants monthly reports
            user_profile = getattr(user, 'userprofile', None)
            if not user_profile or not user_profile.notification_preferences.get('monthly_reports', True):
                continue
            
            # Get user's transactions for the month
            transactions = Transaction.objects.filter(
                user=user,
                date__gte=prev_month_start,
                date__lte=prev_month_end
            )
            
            if not transactions.exists():
                continue
            
            # Calculate monthly statistics
            from django.db.models import Sum, Count, Q
            
            stats = transactions.aggregate(
                total_income=Sum('amount', filter=Q(transaction_type='INCOME')),
                total_expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
                transaction_count=Count('id')
            )
            
            total_income = stats['total_income'] or 0
            total_expenses = stats['total_expenses'] or 0
            net_amount = total_income - total_expenses
            
            # Top spending categories
            top_categories = transactions.filter(
                transaction_type='EXPENSE'
            ).values('category__name').annotate(
                total=Sum('amount')
            ).order_by('-total')[:5]
            
            # Generate email content
            month_name = prev_month_start.strftime('%B %Y')
            subject = f'📊 Your Monthly Financial Report - {month_name}'
            
            categories_text = '\n'.join([
                f"• {cat['category__name'] or 'Uncategorized'}: ${cat['total']:,.2f}"
                for cat in top_categories
            ])
            
            message = f"""
            Hi {user.first_name or user.username},
            
            Here's your financial summary for {month_name}:
            
            💰 INCOME & EXPENSES
            • Total Income: ${total_income:,.2f}
            • Total Expenses: ${total_expenses:,.2f}
            • Net Amount: ${net_amount:,.2f}
            • Transactions: {stats['transaction_count']}
            
            📈 TOP SPENDING CATEGORIES
            {categories_text}
            
            Keep up the great work managing your finances!
            
            Best regards,
            Your Financial Management App
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            
            users_processed += 1
            
        except Exception as e:
            logger.error(f'Failed to send monthly report to {user.email}: {str(e)}')
    
    return f"Monthly reports sent to {users_processed} users"

@shared_task
def check_goal_deadlines():
    """Check for goals approaching their deadlines"""
    today = date.today()
    warning_date = today + timedelta(days=30)  # 30 days warning
    
    approaching_goals = Goal.objects.filter(
        is_achieved=False,
        target_date__lte=warning_date,
        target_date__gte=today
    ).select_related('user')
    
    notifications_sent = 0
    
    for goal in approaching_goals:
        try:
            user_profile = getattr(goal.user, 'userprofile', None)
            if not user_profile or not user_profile.notification_preferences.get('goal_reminders', True):
                continue
            
            days_remaining = (goal.target_date - today).days
            progress_percentage = goal.progress_percentage
            
            subject = f'🎯 Goal Deadline Approaching: {goal.name}'
            
            message = f"""
            Hi {goal.user.first_name or goal.user.username},
            
            Your goal "{goal.name}" is approaching its deadline.
            
            Goal Details:
            • Target Amount: ${goal.target_amount:,.2f}
            • Current Progress: ${goal.current_amount:,.2f} ({progress_percentage:.1f}%)
            • Remaining: ${goal.remaining_amount:,.2f}
            • Days Left: {days_remaining} days
            • Target Date: {goal.target_date}
            
            Monthly savings needed: ${goal.monthly_savings_needed:,.2f}
            
            Stay focused and keep working towards your goal!
            
            Best regards,
            Your Financial Management App
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[goal.user.email],
                fail_silently=False
            )
            
            notifications_sent += 1
            
        except Exception as e:
            logger.error(f'Failed to send goal deadline notification to {goal.user.email}: {str(e)}')
    
    return f"Goal deadline notifications sent to {notifications_sent} users"

@shared_task
def cleanup_old_data():
    """Clean up old data to maintain database performance"""
    from django.utils import timezone
    
    # Delete transactions older than 7 years (keeping 7 years for tax purposes)
    cutoff_date = timezone.now() - timedelta(days=7*365)
    
    old_transactions = Transaction.objects.filter(created_at__lt=cutoff_date)
    deleted_count = old_transactions.count()
    old_transactions.delete()
    
    return f"Cleaned up {deleted_count} old transactions"

@shared_task
def backup_user_data(user_id):
    """Create a backup of user's financial data"""
    import json
    from django.core import serializers
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    
    try:
        user = User.objects.get(id=user_id)
        
        # Gather all user data
        data = {
            'user_info': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat(),
            },
            'transactions': list(Transaction.objects.filter(user=user).values()),
            'budgets': list(Budget.objects.filter(user=user).values()),
            'categories': list(user.category_set.values()),
            'goals': list(Goal.objects.filter(user=user).values()),
            'recurring_transactions': list(RecurringTransaction.objects.filter(user=user).values()),
        }
        
        # Convert datetime and decimal objects to strings
        def convert_special_types(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, '__str__') and 'Decimal' in str(type(obj)):
                return str(obj)
            return obj
        
        # Process the data to handle special types
        json_data = json.dumps(data, default=convert_special_types, indent=2)
        
        # Save backup file
        filename = f"backup_{user.username}_{date.today().isoformat()}.json"
        file_content = ContentFile(json_data.encode('utf-8'))
        backup_path = default_storage.save(f"backups/{filename}", file_content)
        
        return f"Backup created successfully: {backup_path}"
        
    except Exception as e:
        logger.error(f'Failed to backup data for user {user_id}: {str(e)}')
        return f"Backup failed: {str(e)}"

@shared_task
def calculate_spending_insights(user_id):
    """Calculate personalized spending insights for a user"""
    try:
        user = User.objects.get(id=user_id)
        
        # Get transactions from last 6 months
        six_months_ago = date.today() - timedelta(days=180)
        transactions = Transaction.objects.filter(
            user=user,
            date__gte=six_months_ago,
            transaction_type='EXPENSE'
        ).select_related('category')
        
        if not transactions.exists():
            return "No transaction data available for insights"
        
        from django.db.models import Sum, Avg, Count
        from collections import defaultdict
        import calendar
        
        insights = {}
        
        # 1. Monthly spending trends
        monthly_spending = transactions.values(
            'date__year', 'date__month'
        ).annotate(
            total=Sum('amount')
        ).order_by('date__year', 'date__month')
        
        insights['monthly_trends'] = [
            {
                'month': f"{calendar.month_name[item['date__month']]} {item['date__year']}",
                'amount': float(item['total'])
            }
            for item in monthly_spending
        ]
        
        # 2. Category analysis
        category_spending = transactions.values(
            'category__name'
        ).annotate(
            total=Sum('amount'),
            avg_transaction=Avg('amount'),
            transaction_count=Count('id')
        ).order_by('-total')
        
        insights['category_breakdown'] = [
            {
                'category': item['category__name'] or 'Uncategorized',
                'total_spent': float(item['total']),
                'avg_transaction': float(item['avg_transaction']),
                'frequency': item['transaction_count']
            }
            for item in category_spending
        ]
        
        # 3. Day of week patterns
        day_patterns = defaultdict(list)
        for transaction in transactions:
            day_name = transaction.date.strftime('%A')
            day_patterns[day_name].append(float(transaction.amount))
        
        insights['day_of_week_patterns'] = {
            day: {
                'avg_spending': sum(amounts) / len(amounts) if amounts else 0,
                'total_transactions': len(amounts)
            }
            for day, amounts in day_patterns.items()
        }
        
        # 4. Spending velocity (how spending rate changes over time)
        recent_month = transactions.filter(date__gte=date.today() - timedelta(days=30))
        previous_month = transactions.filter(
            date__gte=date.today() - timedelta(days=60),
            date__lte=date.today() - timedelta(days=30)
        )
        
        recent_total = recent_month.aggregate(total=Sum('amount'))['total'] or 0
        previous_total = previous_month.aggregate(total=Sum('amount'))['total'] or 0
        
        if previous_total > 0:
            spending_change = ((recent_total - previous_total) / previous_total) * 100
        else:
            spending_change = 0
        
        insights['spending_velocity'] = {
            'recent_month_total': float(recent_total),
            'previous_month_total': float(previous_total),
            'percentage_change': round(spending_change, 2)
        }
        
        # Store insights in user profile (you might want to add an insights field)
        # For now, just return the insights
        return f"Insights calculated successfully for user {user.username}"
        
    except Exception as e:
        logger.error(f'Failed to calculate insights for user {user_id}: {str(e)}')
        return f"Insights calculation failed: {str(e)}"

@shared_task
def sync_bank_transactions(user_id, bank_connection_id):
    """
    Placeholder for bank API integration
    This would sync transactions from external banking APIs like Plaid, Yodlee, etc.
    """
    # This is a placeholder - in real implementation, you would:
    # 1. Connect to banking API
    # 2. Fetch new transactions
    # 3. Use AI to categorize them
    # 4. Import into the system
    # 5. Notify user of new transactions
    
    return f"Bank sync placeholder - would sync for user {user_id}, connection {bank_connection_id}"