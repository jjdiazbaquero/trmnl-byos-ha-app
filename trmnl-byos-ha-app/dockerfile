FROM python:3.12-alpine

# Create a non‑root user
RUN addgroup -S app && adduser -S app -G app

WORKDIR /app
COPY server.py /app/server.py
RUN chown -R app:app /app
USER app

EXPOSE 10001
CMD ["python", "-u", "server.py"]
