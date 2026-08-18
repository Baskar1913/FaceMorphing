from pathlib import Path
import shutil
from huggingface_hub import hf_hub_download, snapshot_download

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"

def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    hf_hub_download(repo_id="ezioruan/inswapper_128.onnx", filename="inswapper_128.onnx", local_dir=MODELS)
    temp = MODELS / "_download"
    snapshot_download(repo_id="yolkailtd/face-swap-models", allow_patterns="insightface/models/buffalo_l/*.onnx", local_dir=temp)
    source = temp / "insightface" / "models" / "buffalo_l"
    target = MODELS / "buffalo_l"
    target.mkdir(exist_ok=True)
    for model in source.glob("*.onnx"):
        shutil.move(str(model), target / model.name)
    shutil.rmtree(temp, ignore_errors=True)
    print(f"Models ready in {MODELS}")

if __name__ == "__main__":
    main()
