from django.db import models
from django.contrib.auth.models import User

# Blueprint for the 'Transaction' table in our database
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateField()
    is_expense = models.BooleanField(default=True)
    category = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        # This is how the transaction will be displayed in the Django admin panel
        return f"{self.description} - ${self.amount}"

# Blueprint for the 'Budget' table in our database
class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"Budget for {self.category}"