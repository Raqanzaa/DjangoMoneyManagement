from rest_framework import serializers
from .models import Transaction, Budget, Category, Goal, RecurringTransaction, UserProfile
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'color', 'icon', 'is_default', 'created_at', 'transaction_count']
        read_only_fields = ['created_at']

    def get_transaction_count(self, obj):
        return obj.transaction_set.count()

class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'description', 'category', 'category_name', 
            'category_color', 'category_icon', 'transaction_type', 
            'date', 'notes', 'receipt_image', 'is_recurring', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_category(self, value):
        """Ensure the category belongs to the authenticated user"""
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("You can only use your own categories.")
        return value

class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    spent_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    percentage_used = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    is_over_budget = serializers.BooleanField(read_only=True)
    is_near_limit = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'category_name', 'amount', 'period', 
            'start_date', 'end_date', 'alert_threshold', 'is_active',
            'spent_amount', 'remaining_amount', 'percentage_used',
            'is_over_budget', 'is_near_limit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_category(self, value):
        """Ensure the category belongs to the authenticated user"""
        if value.user != self.context['request'].user:
            raise serializers.ValidationError("You can only create budgets for your own categories.")
        return value

    def validate(self, data):
        """Validate that start_date is before end_date"""
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("Start date must be before end date.")
        return data

class GoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    monthly_savings_needed = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Goal
        fields = [
            'id', 'name', 'description', 'goal_type', 'target_amount', 
            'current_amount', 'target_date', 'is_achieved', 
            'progress_percentage', 'remaining_amount', 'days_remaining',
            'monthly_savings_needed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        """Validate that target_date is in the future for new goals"""
        from datetime import date
        if not self.instance and data['target_date'] <= date.today():
            raise serializers.ValidationError("Target date must be in the future.")
        return data

class RecurringTransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = RecurringTransaction
        fields = [
            'id', 'amount', 'description', 'category', 'category_name',
            'transaction_type', 'frequency', 'start_date', 'end_date',
            'next_occurrence', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at', 'next_occurrence']

    def validate_category(self, value):
        """Ensure the category belongs to the authenticated user"""
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("You can only use your own categories.")
        return value

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'currency', 'timezone', 'notification_preferences', 
            'monthly_income', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class TransactionSummarySerializer(serializers.Serializer):
    """Serializer for transaction summary statistics"""
    period = serializers.CharField()
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()
    top_categories = serializers.ListField(child=serializers.DictField())

class CategorySpendingSerializer(serializers.Serializer):
    """Serializer for category spending analysis"""
    category_name = serializers.CharField()
    category_color = serializers.CharField()
    category_icon = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()
    percentage_of_total = serializers.DecimalField(max_digits=5, decimal_places=2)