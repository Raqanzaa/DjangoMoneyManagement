# api/gemini_analyzer.py
import google.generativeai as genai
from django.conf import settings

# Configure the Gemini API client with our key from settings.py
genai.configure(api_key=settings.GEMINI_API_KEY)

def generate_financial_plan(income, expenses, current_savings, financial_goal):
    """
    Generates a personalized financial plan using the Gemini API.
    """
    # This is the "prompt" we send to the AI. It's a detailed instruction.
    # Crafting a good prompt is the key to getting a good response.
    prompt = f"""
    You are an expert financial planner AI. Your task is to create a clear, actionable, and personalized financial plan for a user.
    Provide the output in a structured JSON format.

    Here is the user's financial data:
    - Monthly Income: ${income}
    - Monthly Expenses: ${expenses}
    - Current Savings: ${current_savings}
    - Financial Goal: {financial_goal}

    Based on this data, create a plan with the following JSON structure:
    {{
      "monthly_surplus": number,
      "emergency_fund": {{
        "target_amount": number,
        "monthly_contribution": number,
        "timeline_months": number,
        "recommendation": "string"
      }},
      "goal_savings": {{
        "goal_name": "string",
        "monthly_contribution": number,
        "timeline_months": number,
        "recommendation": "string"
      }},
      "investment_plan": {{
        "monthly_contribution": number,
        "recommendation": "string describing a simple investment strategy like index funds for long-term growth"
      }},
      "summary": "string providing a brief, encouraging overview of the plan"
    }}

    Calculate the monthly surplus (income - expenses).
    For the emergency fund, target 3-6 months of expenses. Prioritize this first.
    For the goal savings, calculate contributions needed to meet the user's goal.
    Allocate the remaining surplus to investments.
    Ensure all monthly contributions (emergency, goal, investment) add up to the monthly surplus.
    The recommendations should be encouraging and easy for a beginner to understand.
    """

    try:
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        # The AI can sometimes return markdown backticks with JSON, so we clean them.
        response_text = (
            model.generate_content(prompt)
            .text.replace("```json", "")
            .replace("```", "")
            .strip()
        )
        return response_text
    except Exception as e:
        # Handle potential API errors gracefully
        return f'{{"error": "Could not generate plan. Error: {str(e)}"}}'
