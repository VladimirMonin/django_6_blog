"""Gunicorn configuration for the systemd socket boundary."""
bind = "unix:/run/django-6-blog/gunicorn.sock"
workers = 2
timeout = 30
accesslog = "-"
errorlog = "-"
