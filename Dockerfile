FROM python:3.13.0-alpine3.20

COPY requirements.txt /
COPY decode-config.py /usr/local/bin/decode-config.py

RUN pip install -r /requirements.txt && \
  rm -f /requirements.txt

ENTRYPOINT ["/usr/local/bin/decode-config.py"]
