FROM python:3.12-slim

RUN useradd --create-home --uid 10001 kbsync
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY src ./src
RUN chown -R kbsync:kbsync /app

USER kbsync
ENV PYTHONUNBUFFERED=1

# ENTRYPOINT/CMD split so both `docker run <image>` and the brief's
# `docker run <image> main.py` resolve to the same single run.
ENTRYPOINT ["python"]
CMD ["main.py"]
