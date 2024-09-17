FROM python:3.10
EXPOSE 8080
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY requirements.txt .
RUN pip install -r /app/requirements.txt
COPY . ./
CMD ["python", "main.py"]