# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategorizeTransactionView, GeneratePlanView, TransactionViewSet, BudgetViewSet, GoogleLoginCallbackView
from rest_framework_simplejwt.views import TokenRefreshView

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'budgets', BudgetViewSet, basename='budget')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/callback/', GoogleLoginCallbackView.as_view(), name='google-callback'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('analyze/categorize/', CategorizeTransactionView.as_view(), name='categorize-transaction'),
    path('plan/generate/', GeneratePlanView.as_view(), name='generate-plan'),
]