FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    cmake \
    git \
    git-lfs \
    && git lfs install --system \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
    https://github.com/Baskar1913/FaceMorphing.git /tmp/facemorph \
    && cd /tmp/facemorph \
    && git lfs pull \
    && rm -rf /app/models \
    && cp -r /tmp/facemorph/backend/models /app/models \
    && rm -rf /tmp/facemorph

RUN python -c "from pathlib import Path; files=list(Path('models').rglob('*.onnx')); assert len(files) == 6, f'Expected 6 ONNX models, found {len(files)}'; assert min(f.stat().st_size for f in files) > 1000000, 'Git LFS models were not retrieved correctly'"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]