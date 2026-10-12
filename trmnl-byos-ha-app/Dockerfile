FROM python:3.12-alpine

WORKDIR /app

# Copy and prepare the entrypoint script as root
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Copy application files and set ownership
COPY server.py /app/server.py

EXPOSE 10001
CMD ["/run.sh"]