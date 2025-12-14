FROM python:3.12-slim
RUN mkdir /app
RUN mkdir /app/logs
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
CMD python dg-main.py