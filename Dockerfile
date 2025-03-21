# Use the official Python image as the base
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory inside the container
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-cache

# Copy the rest of the application code
COPY app/ ./app
RUN mkdir -p ./assets

# ENV PORT=8000

# Expose port 8000
EXPOSE 8000

# Command to run the FastAPI application
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["sh", "-c", "/app/.venv/bin/fastapi run app/main.py --host 0.0.0.0 --port ${PORT:-8000}"]

