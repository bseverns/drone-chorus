FROM python:3.11-slim

WORKDIR /app

COPY software/midi-bridge/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY software/midi-bridge /app/software/midi-bridge
COPY config /app/config

ENTRYPOINT ["python", "software/midi-bridge/msp_to_midi.py"]
