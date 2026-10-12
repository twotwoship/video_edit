"""동영상을 2배속으로 변환해 새 파일로 저장한다.

사용 예:
    python speedup_video.py input.mp4
    python speedup_video.py input.mp4 output.mp4 --overwrite

이 스크립트를 실행하려면 FFmpeg와 FFprobe가 PATH에 등록되어 있어야 한다.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_tool(name: str) -> str | None:
    """PATH 또는 이 스크립트와 같은 폴더에서 FFmpeg 도구를 찾는다."""
    installed = shutil.which(name)
    if installed:
        return installed
    local_name = f"{name}.exe" if sys.platform == "win32" else name
    local_tool = Path(__file__).resolve().with_name(local_name)
    return str(local_tool) if local_tool.is_file() else None


def has_audio_stream(ffprobe: str, input_path: Path) -> bool:
    """입력 파일에 오디오 스트림이 있는지 확인한다."""
    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(input_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return bool(result.stdout.strip())


def make_double_speed(
    input_path: Path, output_path: Path, *, overwrite: bool = False
) -> None:
    """영상과 오디오를 2배속으로 인코딩한다."""
    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError(
            "FFmpeg를 찾을 수 없습니다. FFmpeg를 설치하고 ffmpeg/ffprobe를 "
            "PATH에 등록해 주세요."
        )

    if not input_path.is_file():
        raise FileNotFoundError(f"입력 파일이 없습니다: {input_path}")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("입력 파일과 출력 파일은 서로 달라야 합니다.")

    audio_exists = has_audio_stream(ffprobe, input_path)
    command = [ffmpeg, "-hide_banner", "-y" if overwrite else "-n", "-i", str(input_path)]
    command += [
        "-map",
        "0:v:0",
        "-vf",
        "setpts=0.5*PTS",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
    ]

    if audio_exists:
        command += [
            "-map",
            "0:a:0",
            "-af",
            "atempo=2.0",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
        ]

    command += [
        "-map_metadata",
        "0",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="동영상과 오디오를 2배속으로 변환해 파일로 저장합니다."
    )
    parser.add_argument("input", type=Path, help="원본 동영상 경로")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="저장 경로(생략 시 원본 파일명 뒤에 _2x를 붙임)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="출력 파일이 이미 있으면 덮어쓰기",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path: Path = args.input
    output_path: Path = args.output or input_path.with_name(
        f"{input_path.stem}_2x.mp4"
    )

    try:
        make_double_speed(input_path, output_path, overwrite=args.overwrite)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1

    print(f"저장 완료: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
