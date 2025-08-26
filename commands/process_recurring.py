from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from api.models import RecurringTransaction, Transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process recurring transactions that are due'

    def handle(self, *args, **options):
        today = date.today()
        
        # Find all recurring transactions that are due today
        due_recurring = RecurringTransaction.objects.filter(
            is_active=True,
            next_occurrence__lte=today
        )
        
        processed_count = 0
        
        for recurring in due_recurring:
            try:
                # Create the actual transaction
                Transaction.objects.create(
                    user=recurring.user,
                    amount=recurring.amount,
                    description=recurring.description,
                    category=recurring.category,
                    transaction_type=recurring.transaction_type,
                    date=recurring.next_occurrence,
                    notes=f"Auto-generated from recurring transaction: {recurring.id}",
                    is_recurring=True
                )
                
                # Calculate next occurrence
                next_date = self.calculate_next_occurrence(recurring)
                
                if next_date and (not recurring.end_date or next_date <= recurring.end_date):
                    recurring.next_occurrence = next_date
                    recurring.save()
                else:
                    # End date reached or no more occurrences
                    recurring.is_active = False
                    recurring.save()
                
                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Processed recurring transaction: {recurring.description} for {recurring.user.username}'
                    )
                )
                
            except Exception as e:
                logger.error(f'Error processing recurring transaction {recurring.id}: {str(e)}')
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing recurring transaction {recurring.id}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {processed_count} recurring transactions')
        )

    def calculate_next_occurrence(self, recurring):
        """Calculate the next occurrence date based on frequency"""
        current_date = recurring.next_occurrence
        
        if recurring.frequency == 'DAILY':
            return current_date + timedelta(days=1)
        elif recurring.frequency == 'WEEKLY':
            return current_date + timedelta(weeks=1)
        elif recurring.frequency == 'BIWEEKLY':
            return current_date + timedelta(weeks=2)
        elif recurring.frequency == 'MONTHLY':
            # Handle month-end dates properly
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1)
            
            # Handle cases where the day doesn't exist in the next month (e.g., Jan 31 -> Feb 31)
            try:
                return next_month
            except ValueError:
                # Go to the last day of the month
                import calendar
                last_day = calendar.monthrange(next_month.year, next_month.month)[1]
                return next_month.replace(day=last_day)
        elif recurring.frequency == 'QUARTERLY':
            # Add 3 months
            month = current_date.month
            year = current_date.year
            month += 3
            if month > 12:
                month -= 12
                year += 1
            try:
                return current_date.replace(year=year, month=month)
            except ValueError:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                return current_date.replace(year=year, month=month, day=min(current_date.day, last_day))
        elif recurring.frequency == 'YEARLY':
            try:
                return current_date.replace(year=current_date.year + 1)
            except ValueError:
                # Handle leap year edge case (Feb 29)
                return current_date.replace(year=current_date.year + 1, day=28)
        
        return None