import json
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .ai_analyzer import predict_category
from .gemini_analyzer import generate_financial_plan
from rest_framework import viewsets
from .models import Transaction, Budget
from .serializers import TransactionSerializer, BudgetSerializer

class CategorizeTransactionView(APIView):
    # This ensures only logged-in users can access this endpoint.
    permission_classes = [IsAuthenticated]

    def post(self, request):
        description = request.data.get('description')
        if not description:
            return Response({'error': 'Description is required'}, status=400)

        # Call our AI function to get the category
        category = predict_category(description)
        
        # Return the result as a JSON response
        return Response({'description': description, 'suggested_category': category})

class GeneratePlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get data from the request
        income = request.data.get('income')
        expenses = request.data.get('expenses')
        savings = request.data.get('savings')
        goal = request.data.get('goal')

        # Basic validation
        if not all([income, expenses, savings, goal]):
            return Response({'error': 'Missing required fields'}, status=400)

        # Call our Gemini service function
        plan_json_str = generate_financial_plan(income, expenses, savings, goal)

        try:
            # Convert the JSON string response into a Python dictionary
            plan_data = json.loads(plan_json_str)
            if "error" in plan_data:
                return Response(plan_data, status=500)
            return Response(plan_data)
        except json.JSONDecodeError:
            return Response({'error': 'Failed to parse the response from AI service.'}, status=500)

class TransactionViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update`, and `destroy` actions.
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the transactions
        for the currently authenticated user.
        """
        return Transaction.objects.filter(user=self.request.user).order_by('-date')

    def perform_create(self, serializer):
        """
        Assign the logged-in user to the transaction upon creation.
        """
        serializer.save(user=self.request.user)

class BudgetViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides CRUD actions for Budgets.
    """
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Ensure users can only see their own budgets.
        """
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Assign the logged-in user to the budget when creating it.
        """
        serializer.save(user=self.request.user)