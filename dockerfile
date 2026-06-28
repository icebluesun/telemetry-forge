FROM python:3.11-slim
WORKDIR /app/dashboard
COPY . .
RUN pip install -r requirements.txt
CMD ["streamlit", "run", "dashboard/app.py"]