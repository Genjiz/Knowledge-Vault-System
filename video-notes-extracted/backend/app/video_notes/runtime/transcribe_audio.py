import argparse
import os

from faster_whisper import WhisperModel


def srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole_seconds = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio to SRT using faster-whisper.")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument("--lang", default="zh")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--compute", default="int8_float16")
    parser.add_argument("--vad", action="store_true")
    parser.add_argument("--outdir", default="")
    args = parser.parse_args()

    audio_path = os.path.abspath(args.audio)
    if not os.path.exists(audio_path):
        raise FileNotFoundError(audio_path)

    outdir = args.outdir.strip() or os.path.dirname(audio_path)
    os.makedirs(outdir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    output_path = os.path.join(outdir, base_name + ".srt")

    language = None if args.lang == "auto" else args.lang
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute)
    segments, info = model.transcribe(audio_path, language=language, vad_filter=args.vad)

    with open(output_path, "w", encoding="utf-8") as handle:
        for index, segment in enumerate(segments, start=1):
            handle.write(f"{index}\n")
            handle.write(f"{srt_time(segment.start)} --> {srt_time(segment.end)}\n")
            handle.write(f"{segment.text.strip()}\n\n")

    print(f"Wrote: {output_path}")
    print(f"Detected language: {info.language} Prob: {info.language_probability}")


if __name__ == "__main__":
    main()
