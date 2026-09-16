import subprocess
from pathlib import Path

from app.video_notes.runtime.process import decode_process_output


class TranscriptionService:
    def transcribe_audio(self, audio_path, transcript_path, **kwargs):
        audio_path = Path(audio_path)
        transcript_path = Path(transcript_path)
        script_path = Path(__file__).resolve().parents[1] / "runtime" / "transcribe_audio.py"

        command = [
            "conda",
            "run",
            "-n",
            "whisper",
            "python",
            str(script_path),
            str(audio_path),
            "--model",
            kwargs.get("whisper_model", "large-v3-turbo"),
            "--lang",
            kwargs.get("language", "zh"),
            "--device",
            kwargs.get("device", "cuda"),
            "--compute",
            kwargs.get("compute_type", "int8_float16"),
            "--outdir",
            str(transcript_path.parent),
        ]
        if kwargs.get("use_vad", True):
            command.append("--vad")

        completed = subprocess.run(command, capture_output=True)
        if completed.returncode != 0:
            stderr_text = decode_process_output(completed.stderr).strip()
            raise RuntimeError(stderr_text or "Whisper transcription failed")

        if not transcript_path.exists():
            raise RuntimeError("Whisper transcription did not produce the expected SRT file")

        return str(transcript_path)
