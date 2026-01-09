FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
COPY main.py .

ENV REST_BASE_URL=http://api-rest:8080
ENV DEFAULT_LOW_STOCK=25
ENV DEFAULT_DISCOUNT=10

EXPOSE 5000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]