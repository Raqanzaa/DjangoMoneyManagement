# api/serializers.py

from rest_framework import serializers
from .models import Transaction, Budget

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'description', 'date', 'is_expense', 'category', 'user']
        # We mark 'user' as read_only because it will be set automatically
        # based on the logged-in user, not sent in the request body.
        read_only_fields = ['user']

        pass

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'category', 'amount', 'start_date', 'end_date', 'user']
        # Again, the user is set automatically, not provided by the user.
        read_only_fields = ['user']