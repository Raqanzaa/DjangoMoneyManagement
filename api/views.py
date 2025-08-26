import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken

from .ai_analyzer import predict_category
from .gemini_analyzer import generate_financial_plan
from .models import (
    Transaction, Budget, Category, Goal, 
    RecurringTransaction, UserProfile
)
from .serializers import (
    TransactionSerializer, BudgetSerializer, CategorySerializer,
    GoalSerializer, RecurringTransactionSerializer, UserProfileSerializer,
    TransactionSummarySerializer, CategorySpendingSerializer
)

class GoogleLoginCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Create user profile if it doesn't exist
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Create default categories for new users
        if created:
            default_categories = [
                {'name': 'Food & Dining', 'color': '#EF4444', 'icon': '🍽️'},
                {'name': 'Transportation', 'color': '#3B82F6', 'icon': '🚗'},
                {'name': 'Shopping', 'color': '#8B5CF6', 'icon': '🛍️'},
                {'name': 'Entertainment', 'color': '#F59E0B', 'icon': '🎬'},
                {'name': 'Bills & Utilities', 'color': '#10B981', 'icon': '💡'},
                {'name': 'Health & Medical', 'color': '#EC4899', 'icon': '🏥'},
                {'name': 'Income', 'color': '#059669', 'icon': '💰'},
                {'name': 'Other', 'color': '#6B7280', 'icon': '📋'},
            ]
            
            for cat_data in default_categories:
                Category.objects.create(
                    user=user,
                    name=cat_data['name'],
                    color=cat_data['color'],
                    icon=cat_data['icon'],
                    is_default=True
                )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        redirect_url = f"{settings.FRONTEND_URL}/login/success/"
        response = redirect(f"{redirect_url}?access_token={access_token}&refresh_token={refresh_token}")
        return response

class CategorizeTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        description = request.data.get('description')
        if not description:
            return Response({'error': 'Description is required'}, status=400)

        # Get user's categories for better matching
        user_categories = Category.objects.filter(user=request.user).values_list('name', flat=True)
        
        # Call AI function with user's categories context
        category = predict_category(description, list(user_categories))
        
        # Try to find matching category
        suggested_category = Category.objects.filter(
            user=request.user, 
            name__iexact=category
        ).first()
        
        response_data = {
            'description': description, 
            'suggested_category': category,
            'category_id': suggested_category.id if suggested_category else None
        }
        
        return Response(response_data)

class GeneratePlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        income = request.data.get('income')
        expenses = request.data.get('expenses')
        savings = request.data.get('savings')
        goal = request.data.get('goal')

        if not all([income, expenses, savings, goal]):
            return Response({'error': 'Missing required fields'}, status=400)

        # Get user's transaction history for better recommendations
        recent_transactions = Transaction.objects.filter(
            user=request.user,
            date__gte=date.today() - timedelta(days=90)
        ).select_related('category')
        
        # Create context from user's spending patterns
        spending_context = {}
        for transaction in recent_transactions:
            category = transaction.category.name if transaction.category else 'Other'
            spending_context[category] = spending_context.get(category, 0) + float(transaction.amount)

        plan_json_str = generate_financial_plan(income, expenses, savings, goal, spending_context)

        try:
            plan_data = json.loads(plan_json_str)
            if "error" in plan_data:
                return Response(plan_data, status=500)
            return Response(plan_data)
        except json.JSONDecodeError:
            return Response({'error': 'Failed to parse the response from AI service.'}, status=500)

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user).select_related('category')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
            
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # Filter by transaction type
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset.order_by('-date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary for different time periods"""
        period = request.query_params.get('period', 'monthly')  # daily, weekly, monthly, yearly
        
        queryset = self.get_queryset()
        
        if period == 'daily':
            # Last 30 days
            start_date = date.today() - timedelta(days=30)
            queryset = queryset.filter(date__gte=start_date)
            truncate_func = TruncDay
        elif period == 'weekly':
            # Last 12 weeks
            start_date = date.today() - timedelta(weeks=12)
            queryset = queryset.filter(date__gte=start_date)
            truncate_func = TruncWeek
        elif period == 'yearly':
            # Last 5 years
            start_date = date.today() - timedelta(days=365*5)
            queryset = queryset.filter(date__gte=start_date)
            truncate_func = TruncMonth  # Group by month for yearly view
        else:  # monthly
            # Last 12 months
            start_date = date.today() - timedelta(days=365)
            queryset = queryset.filter(date__gte=start_date)
            truncate_func = TruncMonth

        # Calculate summary statistics
        summary = queryset.aggregate(
            total_income=Sum('amount', filter=Q(transaction_type='INCOME')),
            total_expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
            transaction_count=Count('id')
        )
        
        # Handle None values
        total_income = summary['total_income'] or Decimal('0')
        total_expenses = summary['total_expenses'] or Decimal('0')
        
        # Get top categories
        top_categories = queryset.filter(
            transaction_type='EXPENSE'
        ).values(
            'category__name', 'category__color', 'category__icon'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total')[:5]

        response_data = {
            'period': period,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_amount': total_income - total_expenses,
            'transaction_count': summary['transaction_count'],
            'top_categories': list(top_categories)
        }

        serializer = TransactionSummarySerializer(response_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def category_analysis(self, request):
        """Get spending analysis by category"""
        start_date = request.query_params.get('start_date', date.today() - timedelta(days=30))
        end_date = request.query_params.get('end_date', date.today())
        
        expenses = self.get_queryset().filter(
            transaction_type='EXPENSE',
            date__gte=start_date,
            date__lte=end_date
        )
        
        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        category_data = expenses.values(
            'category__name', 'category__color', 'category__icon'
        ).annotate(
            total_amount=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-total_amount')
        
        # Calculate percentages
        for item in category_data:
            if total_expenses > 0:
                item['percentage_of_total'] = (item['total_amount'] / total_expenses) * 100
            else:
                item['percentage_of_total'] = 0
        
        serializer = CategorySpendingSerializer(category_data, many=True)
        return Response(serializer.data)

class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related('category')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """Get budget alerts for over-budget and near-limit budgets"""
        budgets = self.get_queryset().filter(is_active=True)
        
        over_budget = []
        near_limit = []
        
        for budget in budgets:
            if budget.is_over_budget:
                over_budget.append(self.get_serializer(budget).data)
            elif budget.is_near_limit:
                near_limit.append(self.get_serializer(budget).data)
        
        return Response({
            'over_budget': over_budget,
            'near_limit': near_limit
        })

class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update progress towards a goal"""
        goal = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = Decimal(str(amount))
            goal.current_amount += amount
            
            # Check if goal is achieved
            if goal.current_amount >= goal.target_amount:
                goal.is_achieved = True
                goal.current_amount = goal.target_amount  # Don't exceed target
            
            goal.save()
            
            return Response(self.get_serializer(goal).data)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

class RecurringTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user).select_related('category')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = date.today()
        
        # Current month stats
        current_month_start = today.replace(day=1)
        
        current_month_transactions = Transaction.objects.filter(
            user=user,
            date__gte=current_month_start,
            date__lte=today
        )
        
        # Calculate current month totals
        current_month_income = current_month_transactions.filter(
            transaction_type='INCOME'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        current_month_expenses = current_month_transactions.filter(
            transaction_type='EXPENSE'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Previous month for comparison
        if current_month_start.month == 1:
            prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
            prev_month_end = current_month_start - timedelta(days=1)
        else:
            prev_month_start = current_month_start.replace(month=current_month_start.month - 1)
            prev_month_end = current_month_start - timedelta(days=1)
        
        prev_month_expenses = Transaction.objects.filter(
            user=user,
            transaction_type='EXPENSE',
            date__gte=prev_month_start,
            date__lte=prev_month_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Calculate percentage change
        if prev_month_expenses > 0:
            expense_change = ((current_month_expenses - prev_month_expenses) / prev_month_expenses) * 100
        else:
            expense_change = 0
        
        # Active budgets status
        active_budgets = Budget.objects.filter(
            user=user,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).count()
        
        over_budget_count = 0
        near_limit_count = 0
        
        for budget in Budget.objects.filter(user=user, is_active=True):
            if budget.is_over_budget:
                over_budget_count += 1
            elif budget.is_near_limit:
                near_limit_count += 1
        
        # Goal progress
        active_goals = Goal.objects.filter(user=user, is_achieved=False)
        total_goals = active_goals.count()
        
        goals_on_track = 0
        for goal in active_goals:
            days_elapsed = (today - goal.created_at.date()).days
            expected_progress = min(100, (days_elapsed / max(1, goal.days_remaining + days_elapsed)) * 100)
            actual_progress = float(goal.progress_percentage)
            
            if actual_progress >= expected_progress * 0.8:  # Within 80% of expected progress
                goals_on_track += 1
        
        # Recent transactions
        recent_transactions = Transaction.objects.filter(
            user=user
        ).select_related('category').order_by('-date', '-created_at')[:5]
        
        # Top spending categories this month
        top_categories = current_month_transactions.filter(
            transaction_type='EXPENSE'
        ).values(
            'category__name', 'category__color', 'category__icon'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total')[:3]
        
        dashboard_data = {
            'current_month': {
                'income': current_month_income,
                'expenses': current_month_expenses,
                'net': current_month_income - current_month_expenses,
                'expense_change_percentage': round(float(expense_change), 2)
            },
            'budgets': {
                'active_count': active_budgets,
                'over_budget_count': over_budget_count,
                'near_limit_count': near_limit_count
            },
            'goals': {
                'total_count': total_goals,
                'on_track_count': goals_on_track
            },
            'recent_transactions': TransactionSerializer(recent_transactions, many=True).data,
            'top_categories': list(top_categories)
        }
        
        return Response(dashboard_data)

class BulkTransactionUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Handle CSV upload for bulk transaction import"""
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        csv_file = request.FILES['file']
        
        if not csv_file.name.endswith('.csv'):
            return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import csv
            import io
            
            # Read CSV file
            file_data = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            csv_reader = csv.DictReader(io_string)
            
            created_transactions = []
            errors = []
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header
                try:
                    # Expected CSV format: date, description, amount, category, type
                    transaction_data = {
                        'date': datetime.strptime(row['date'], '%Y-%m-%d').date(),
                        'description': row['description'],
                        'amount': Decimal(row['amount']),
                        'transaction_type': row.get('type', 'EXPENSE').upper(),
                        'user': request.user
                    }
                    
                    # Try to find matching category
                    category_name = row.get('category', '').strip()
                    if category_name:
                        category = Category.objects.filter(
                            user=request.user,
                            name__iexact=category_name
                        ).first()
                        if category:
                            transaction_data['category'] = category
                    
                    # Create transaction
                    transaction = Transaction.objects.create(**transaction_data)
                    created_transactions.append(transaction)
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return Response({
                'created_count': len(created_transactions),
                'errors': errors,
                'transactions': TransactionSerializer(created_transactions, many=True).data
            })
            
        except Exception as e:
            return Response({'error': f'Failed to process CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)