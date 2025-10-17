FROM python:3.11-slim

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash truputi

# Set working directory
WORKDIR /app

# Copy server script
COPY server.py /app/server.py

# Make script executable
RUN chmod +x /app/server.py && \
    chown truputi:truputi /app/server.py

# Switch to non-root user
USER truputi

# Expose default port
EXPOSE 32201

# Set environment variables (can be overridden)
ENV TRUPUTI_PORT=32201

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('localhost', int('${TRUPUTI_PORT}'))); s.close()" || exit 1

# Run the server
CMD ["python3", "-u", "/app/server.py"]
