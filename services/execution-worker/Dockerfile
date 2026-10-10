FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    gcovr \
    clang \
    cmake \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /worker

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages pydantic pydantic-settings

COPY worker.py .

ENTRYPOINT ["python3", "worker.py"]
