from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

class Category(models.Model):
    """Custom categories that users can create"""
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    color = models.CharField(max_length=7, default='#3B82F6')  # Hex color
    icon = models.CharField(max_length=50, default='💰')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['name', 'user']
        ordering = ['name']

    def __str__(self):
        return f"{self.user.username} - {self.name}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('TRANSFER', 'Transfer'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='EXPENSE')
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.description}: ${self.amount}"

class Budget(models.Model):
    BUDGET_PERIODS = [
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    period = models.CharField(max_length=10, choices=BUDGET_PERIODS, default='MONTHLY')
    start_date = models.DateField()
    end_date = models.DateField()
    alert_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('80.00'))  # Percentage
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'category', 'start_date']
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.user.username} - {self.category.name}: ${self.amount}"

    @property
    def spent_amount(self):
        """Calculate how much has been spent in this budget period"""
        from django.db.models import Sum
        spent = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            transaction_type='EXPENSE',
            date__gte=self.start_date,
            date__lte=self.end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return spent

    @property
    def remaining_amount(self):
        """Calculate remaining budget amount"""
        return self.amount - self.spent_amount

    @property
    def percentage_used(self):
        """Calculate percentage of budget used"""
        if self.amount > 0:
            return (self.spent_amount / self.amount) * 100
        return Decimal('0')

    @property
    def is_over_budget(self):
        """Check if budget has been exceeded"""
        return self.spent_amount > self.amount

    @property
    def is_near_limit(self):
        """Check if spending is near the alert threshold"""
        return self.percentage_used >= self.alert_threshold

class Goal(models.Model):
    GOAL_TYPES = [
        ('SAVING', 'Saving Goal'),
        ('DEBT', 'Debt Payment'),
        ('INVESTMENT', 'Investment Target'),
        ('EMERGENCY', 'Emergency Fund'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    goal_type = models.CharField(max_length=15, choices=GOAL_TYPES)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    target_date = models.DateField()
    is_achieved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['target_date', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    @property
    def progress_percentage(self):
        """Calculate progress towards goal as percentage"""
        if self.target_amount > 0:
            return (self.current_amount / self.target_amount) * 100
        return Decimal('0')

    @property
    def remaining_amount(self):
        """Calculate amount still needed to reach goal"""
        return max(Decimal('0'), self.target_amount - self.current_amount)

    @property
    def days_remaining(self):
        """Calculate days remaining to reach target date"""
        from datetime import date
        today = date.today()
        if self.target_date > today:
            return (self.target_date - today).days
        return 0

    @property
    def monthly_savings_needed(self):
        """Calculate monthly savings needed to reach goal"""
        if self.days_remaining > 0:
            months_remaining = max(1, self.days_remaining / 30.44)  # Average days per month
            return self.remaining_amount / Decimal(str(months_remaining))
        return Decimal('0')

class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('BIWEEKLY', 'Bi-weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    transaction_type = models.CharField(max_length=10, choices=Transaction.TRANSACTION_TYPES)
    frequency = models.CharField(max_length=15, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_occurrence = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.description} ({self.frequency})"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    currency = models.CharField(max_length=3, default='USD')
    timezone = models.CharField(max_length=50, default='UTC')
    notification_preferences = models.JSONField(default=dict)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Profile"