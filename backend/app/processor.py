from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_ROOT / "models"
SWAPPER_PATH = MODELS_DIR / "inswapper_128.onnx"
BUFFALO_PATH = MODELS_DIR / "buffalo_l"
BIN_DIR = BACKEND_ROOT / "bin"
SIMILARITY_THRESHOLD = float(__import__("os").getenv("FACE_MATCH_THRESHOLD", "0.40"))

_models = None
_models_lock = threading.Lock()
PROCESSING_LOCK = threading.Lock()


def model_files_ready() -> bool:
    required = ["1k3d68.onnx", "2d106det.onnx", "det_10g.onnx", "genderage.onnx", "w600k_r50.onnx"]
    return SWAPPER_PATH.exists() and all((BUFFALO_PATH / name).exists() for name in required)


def get_models():
    global _models
    if _models is not None:
        return _models
    with _models_lock:
        if _models is None:
            if not model_files_ready():
                raise FileNotFoundError("AI models are missing. Run: python download_models.py")
            providers = ["CPUExecutionProvider"]
            analyser = FaceAnalysis(name="buffalo_l", root=str(BACKEND_ROOT), providers=providers)
            analyser.prepare(ctx_id=-1, det_size=(640, 640))
            swapper = get_model(str(SWAPPER_PATH), providers=providers)
            _models = (analyser, swapper)
    return _models


def largest_face(analyser, image_path: Path, label: str):
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not read the {label} image.")
    faces = analyser.get(image)
    if not faces:
        raise ValueError(f"No face was detected in the {label} image.")
    return max(faces, key=lambda face: float((face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])))


def embedding(face) -> np.ndarray:
    vector = np.asarray(face.embedding, dtype=np.float32)
    length = np.linalg.norm(vector)
    if length == 0:
        raise ValueError("A face identity vector could not be created.")
    return vector / length


def find_target(faces: list, target_vector: np.ndarray):
    if not faces:
        return None
    scores = [(float(np.dot(embedding(face), target_vector)), face) for face in faces]
    score, face = max(scores, key=lambda item: item[0])
    return face if score >= SIMILARITY_THRESHOLD else None


def find_ffmpeg() -> Path:
    bundled = BIN_DIR / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if bundled.exists():
        return bundled
    installed = shutil.which("ffmpeg")
    if installed:
        return Path(installed)
    raise FileNotFoundError("FFmpeg was not found in backend/bin or the system PATH.")


def run_face_morph(
    video_path: Path,
    source_path: Path,
    target_path: Path,
    output_path: Path,
    progress: Callable[[str, int, int, int, str], None],
) -> None:
    with PROCESSING_LOCK:
        progress("queued", 0, 0, 0, "Loading face-analysis and morphing models...")
        analyser, swapper = get_models()
        source_face = largest_face(analyser, source_path, "source face")
        target_face = largest_face(analyser, target_path, "target face")
        target_vector = embedding(target_face)

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ValueError("The uploaded video could not be opened.")
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if width <= 0 or height <= 0:
            capture.release()
            raise ValueError("The uploaded video has an invalid resolution.")

        silent_path = output_path.with_name("processed_video_no_audio.mp4")
        writer = cv2.VideoWriter(str(silent_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        if not writer.isOpened():
            capture.release()
            raise RuntimeError("The temporary output video could not be created.")

        processed = matched = 0
        progress("processing", 0, total, 0, "Detecting and morphing the selected identity...")
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                selected = find_target(analyser.get(frame), target_vector)
                if selected is not None:
                    frame = swapper.get(frame, selected, source_face, paste_back=True)
                    matched += 1
                writer.write(frame)
                processed += 1
                if processed % 5 == 0 or processed == total:
                    progress("processing", processed, total, matched, "Changing the selected face frame by frame...")
        finally:
            capture.release()
            writer.release()

        if processed == 0:
            silent_path.unlink(missing_ok=True)
            raise ValueError("The uploaded video did not contain readable frames.")

        progress("finalizing", processed, total, matched, "Restoring the original audio with FFmpeg...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            str(find_ffmpeg()), "-y", "-i", str(silent_path), "-i", str(video_path),
            "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264", "-c:a", "aac",
            "-shortest", "-movflags", "+faststart", str(output_path),
        ], check=True, capture_output=True)
        silent_path.unlink(missing_ok=True)
        progress("completed", processed, total, matched, "Your face-morphed video is ready.")
