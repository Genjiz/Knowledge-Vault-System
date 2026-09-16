import subprocess
from pathlib import Path

from app.video_notes.runtime.process import decode_process_output


class DownloadService:
    def download_audio(self, source_url, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_template = output_path.with_suffix(".%(ext)s")
        command = [
            "yt-dlp",
            "-x",
            "--audio-format",
            "wav",
            "--no-progress",
            "--no-warnings",
            "--no-simulate",
            "--print",
            "title",
            "-o",
            str(output_template),
            source_url,
        ]
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
        )

        stdout_text = decode_process_output(completed.stdout)
        stderr_text = decode_process_output(completed.stderr)

        if not output_path.exists():
            raise RuntimeError(stderr_text.strip() or "yt-dlp did not produce the expected audio file")

        title = ""
        for line in reversed(stdout_text.splitlines()):
            if line.strip():
                title = line.strip()
                break

        return {
            "audio_path": str(output_path),
            "video_title": title,
        }
