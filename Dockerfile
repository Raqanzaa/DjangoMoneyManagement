# Stage 1: Use an official Python runtime as a parent image
FROM python:3.11-slim-bullseye

# Stage 2: Set environment variables (Corrected Format)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Stage 3: Set the working directory inside the container
WORKDIR /app

# Stage 4: Install dependencies using requirements.txt
# Copy the requirements file
COPY requirements.txt /app/
# Upgrade pip and install the packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Stage 5: Copy the project code into the container
COPY . /app/

# Stage 6: Expose the port the app runs on
EXPOSE 8000

# Stage 7: Define the command to run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]