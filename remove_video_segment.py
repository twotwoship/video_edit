"""동영상에서 지정한 시간 구간을 제거하고 앞뒤를 이어 저장한다.

기본 실행은 45초부터 1분 5초(65초)까지를 제거한다.

사용 예:
    py remove_video_segment.py "원본_2x.mp4"
    py remove_video_segment.py "원본_2x.mp4" "편집완료.mp4"
    py remove_video_segment.py input.mp4 output.mp4 --start 00:00:45 --end 00:01:05
"""

from __future__ import annotations

import argparse
import json
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


def parse_time(value: str) -> float:
    """초 또는 HH:MM:SS 형식의 시간을 초 단위 숫자로 변환한다."""
    try:
        if ":" not in value:
            seconds = float(value)
        else:
            parts = value.split(":")
            if len(parts) == 2:
                minutes, seconds_part = parts
                seconds = float(minutes) * 60 + float(seconds_part)
            elif len(parts) == 3:
                hours, minutes, seconds_part = parts
                seconds = (
                    float(hours) * 3600
                    + float(minutes) * 60
                    + float(seconds_part)
                )
            else:
                raise ValueError
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"잘못된 시간 형식입니다: {value} (예: 45, 01:05, 00:01:05)"
        ) from error

    if seconds < 0:
        raise argparse.ArgumentTypeError("시간은 0 이상이어야 합니다.")
    return seconds


def inspect_media(ffprobe: str, input_path: Path) -> tuple[float, bool]:
    """영상 길이와 오디오 스트림 존재 여부를 반환한다."""
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "json",
        str(input_path),
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", check=True
    )
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    has_audio = any(
        stream.get("codec_type") == "audio" for stream in data.get("streams", [])
    )
    return duration, has_audio


def remove_segment(
    input_path: Path,
    output_path: Path,
    start: float,
    end: float,
    *,
    overwrite: bool = False,
) -> None:
    """start부터 end까지를 제거하고 나머지 두 구간을 연결한다."""
    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError(
            "FFmpeg를 찾을 수 없습니다. ffmpeg와 ffprobe의 bin 폴더를 "
            "PATH에 등록해 주세요."
        )
    if not input_path.is_file():
        raise FileNotFoundError(f"입력 파일이 없습니다: {input_path}")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("입력 파일과 출력 파일은 서로 달라야 합니다.")
    if start >= end:
        raise ValueError("종료 시간은 시작 시간보다 뒤여야 합니다.")

    duration, has_audio = inspect_media(ffprobe, input_path)
    if start >= duration:
        raise ValueError(f"시작 시간이 영상 길이({duration:.2f}초)를 벗어났습니다.")
    if end >= duration:
        raise ValueError(f"종료 시간이 영상 길이({duration:.2f}초)를 벗어났습니다.")

    # trim/atrim으로 제거 구간의 앞뒤를 분리한 뒤 concat으로 다시 연결한다.
    if has_audio:
        filter_graph = (
            f"[0:v:0]trim=start=0:end={start},setpts=PTS-STARTPTS[v1];"
            f"[0:a:0]atrim=start=0:end={start},asetpts=PTS-STARTPTS[a1];"
            f"[0:v:0]trim=start={end},setpts=PTS-STARTPTS[v2];"
            f"[0:a:0]atrim=start={end},asetpts=PTS-STARTPTS[a2];"
            "[v1][a1][v2][a2]concat=n=2:v=1:a=1[outv][outa]"
        )
    else:
        filter_graph = (
            f"[0:v:0]trim=start=0:end={start},setpts=PTS-STARTPTS[v1];"
            f"[0:v:0]trim=start={end},setpts=PTS-STARTPTS[v2];"
            "[v1][v2]concat=n=2:v=1:a=0[outv]"
        )

    command = [
        ffmpeg,
        "-hide_banner",
        "-y" if overwrite else "-n",
        "-i",
        str(input_path),
        "-filter_complex",
        filter_graph,
        "-map",
        "[outv]",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
    ]
    if has_audio:
        command += ["-map", "[outa]", "-c:a", "aac", "-b:a", "192k"]
    command += ["-movflags", "+faststart", str(output_path)]
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="동영상에서 지정한 구간을 제거한 뒤 앞뒤 영상을 연결합니다."
    )
    parser.add_argument("input", type=Path, help="편집할 동영상 경로")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="저장 경로(생략 시 원본 파일명 뒤에 _edited를 붙임)",
    )
    parser.add_argument(
        "--start", type=parse_time, default=45.0, help="제거 시작 시간(기본값: 45초)"
    )
    parser.add_argument(
        "--end", type=parse_time, default=65.0, help="제거 종료 시간(기본값: 65초)"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="기존 출력 파일 덮어쓰기"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output or args.input.with_name(f"{args.input.stem}_edited.mp4")
    try:
        remove_segment(
            args.input,
            output_path,
            args.start,
            args.end,
            overwrite=args.overwrite,
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1

    print(f"편집 완료: {output_path.resolve()}")
    print(f"제거한 구간: {args.start:g}초 ~ {args.end:g}초")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
