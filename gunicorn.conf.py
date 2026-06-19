# gunicorn.conf.py — конфиг для продакшена на Beget VPS
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
keepalive = 5
accesslog = "data/logs/gunicorn_access.log"
errorlog = "data/logs/gunicorn_error.log"
loglevel = "info"
