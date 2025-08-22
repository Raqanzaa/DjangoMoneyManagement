# api/ai_analyzer.py

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# In a real app, this data would come from a large database of transactions.
# For our example, we'll use this small sample to "train" our model.
data = {
    'description': [
        'Starbucks coffee', 'Monthly rent payment', 'Grocery shopping at Whole Foods',
        'Uber ride to airport', 'Netflix subscription', 'Dinner with friends at restaurant',
        'Gasoline for car', 'Electricity bill', 'New shirt from store'
    ],
    'category': [
        'Food & Drink', 'Housing', 'Groceries',
        'Transport', 'Entertainment', 'Food & Drink',
        'Transport', 'Utilities', 'Shopping'
    ]
}
df = pd.DataFrame(data)

# Create a machine learning "pipeline". This is a series of steps our data will go through.
# 1. TfidfVectorizer: Converts text descriptions into a matrix of numbers that the model can understand.
# 2. MultinomialNB: A classic and effective algorithm for text classification (categorization).
model = make_pipeline(TfidfVectorizer(), MultinomialNB())

# Train the model on our sample data.
model.fit(df['description'], df['category'])

def predict_category(description):
    """
    Takes a new transaction description and predicts its category using our trained model.
    """
    # The model expects a list of items to predict on, so we pass [description].
    prediction = model.predict([description])
    # The result is an array, so we return the first item.
    return prediction[0]