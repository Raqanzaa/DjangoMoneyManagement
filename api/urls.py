from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategorizeTransactionView, GeneratePlanView, TransactionViewSet, 
    BudgetViewSet, CategoryViewSet, GoalViewSet, RecurringTransactionViewSet,
    GoogleLoginCallbackView, UserProfileView, DashboardStatsView,
    BulkTransactionUploadView
)
from rest_framework_simplejwt.views import TokenRefreshView

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'goals', GoalViewSet, basename='goal')
router.register(r'recurring-transactions', RecurringTransactionViewSet, basename='recurring-transaction')

urlpatterns = [
    # Include all the router URLs
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/callback/', GoogleLoginCallbackView.as_view(), name='google-callback'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # AI-powered features
    path('analyze/categorize/', CategorizeTransactionView.as_view(), name='categorize-transaction'),
    path('plan/generate/', GeneratePlanView.as_view(), name='generate-plan'),
    
    # User profile and dashboard
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    
    # Data import/export
    path('transactions/bulk-upload/', BulkTransactionUploadView.as_view(), name='bulk-upload'),
]