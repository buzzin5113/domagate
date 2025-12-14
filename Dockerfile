FROM python:3.12-alpine3.12
RUN mkdir /logs
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
CMD python dg-main.py