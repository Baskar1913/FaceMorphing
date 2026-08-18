# FaceMorph Studio

A complete React + FastAPI application for consent-based, identity-aware face morphing. Users upload an original video, a source face and a target-person reference photo. The frontend previews all inputs, starts the job, displays processed and total frame counts, plays the final MP4 and provides a download button.

## Architecture

```text
React / Next frontend (Vercel)
          │ HTTPS API
          ▼
FastAPI backend (Python server)
          │
          ├── Buffalo_L: detection, landmarks and target recognition
          ├── InSwapper: source-identity face replacement
          ├── OpenCV: frame reading and writing
          └── FFmpeg: original-audio restoration and final MP4
```

Vercel hosts the React interface only. The Python AI backend must run on a separate server because face morphing is a long CPU/GPU job and the ONNX models are large.

## Project structure

```text
face-morph-studio/
├── app/                    # React/Next frontend
├── public/                 # Replaceable logo/banner assets
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI routes and job management
│   │   └── processor.py    # Face recognition/morphing pipeline
│   ├── bin/                # Windows FFmpeg executables
│   ├── models/             # Downloaded Hugging Face ONNX models
│   ├── jobs/               # Per-job inputs and outputs
│   ├── download_models.py
│   ├── Dockerfile
│   └── requirements.txt
├── .env.example
├── package.json
└── vercel.json
```

## Run locally in VS Code

### 1. Backend

Open terminal 1:

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python download_models.py
```

On Windows, download `ffmpeg-release-essentials.zip` from <https://www.gyan.dev/ffmpeg/builds/>, extract it and copy `ffmpeg.exe`, `ffplay.exe` and `ffprobe.exe` into `backend\bin`.

Start the API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation: <http://localhost:8000/docs>

### 2. Frontend

Open terminal 2 in the project root:

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev:next
```

Open <http://localhost:3000>.

## Use the application

1. Upload the original video.
2. Upload the source face—the new identity to apply.
3. Upload the target face—a clear reference of the person to replace in the video.
4. Confirm consent.
5. Select **Start face morphing**.
6. Keep both terminals open while the frame counter advances.
7. When completed, play or download the final video from the result panel.

## GitHub and Vercel frontend deployment

1. Push this project to a GitHub repository.
2. Import that repository in Vercel.
3. Keep the project root as the Vercel root directory.
4. Add the environment variable:

```text
NEXT_PUBLIC_API_URL=https://YOUR-BACKEND-DOMAIN
```

5. Deploy the frontend.

## Backend deployment

Deploy the `backend` directory to a service that supports Docker and long-running Python processes. The included Dockerfile installs FFmpeg, installs Python packages and downloads both Hugging Face model groups during the image build.

Set this backend environment variable after the Vercel URL is known:

```text
CORS_ORIGINS=https://YOUR-VERCEL-SITE.vercel.app
```

For a five-minute video, use a backend plan with enough memory, disk space and execution time. CPU processing may take considerably longer than the video's duration.

## Model downloads

`backend/download_models.py` automatically downloads:

- InSwapper: <https://huggingface.co/ezioruan/inswapper_128.onnx/tree/main>
- Buffalo_L: <https://huggingface.co/yolkailtd/face-swap-models/tree/main/insightface/models/buffalo_l>

The large model files are intentionally excluded from Git.

## Manual logo and banner replacement

The current interface includes a complete code-based logo and hero visual, so it works immediately without external images. If you want your own branding later, add files such as `public/logo.png` and `public/banner.jpg`, then replace the `Logo` component and hero visual in `app/page.tsx`. This does not affect the upload or face-morphing logic.

## Safety

Use the application only when everyone shown has consented and only for lawful, non-deceptive purposes. The interface requires an explicit consent confirmation before a job can start.
