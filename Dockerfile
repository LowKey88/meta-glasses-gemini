FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

# RUN apt-get -y update
# RUN apt-get -y upgrade
LABEL org.opencontainers.image.authors="marcpata@gmail.com"
RUN apt-get -y update
RUN apt-get -y install ffmpeg cron
COPY . /app
COPY creds-cron /etc/cron.d
RUN chmod 0644 /etc/cron.d/creds-cron
RUN pip install -r requirements.txt
EXPOSE 8080
RUN cron
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]