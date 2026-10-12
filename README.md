# video_edit
video_edit

## speedup_video.py 2배속
현재 PC에는 winget, choco도 없어서 FFmpeg를 직접 설치하면 됩니다.
1. FFmpeg Windows 빌드(https://www.gyan.dev/ffmpeg/builds/)에서 **ffmpeg-release-essentials.zip**을 다운로드합니다.
FFmpeg 공식 다운로드 페이지에서도 이 Windows 빌드를 안내합니다. (공식 페이지)

4. 압축을 풀고 폴더 이름을 정리해 아래처럼 배치합니다.
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe

6. 지금 열려 있는 PowerShell에서 다음을 실행합니다. /다운받은곳에 패스설정
$env:Path += ";C:\ffmpeg\bin"

7. 설치 확인:
ffmpeg -version
ffprobe -version

8. 다시 변환:
cd D:\project\해당폴더이동
py speedup_video.py "원본.mp4"

그러면 같은 폴더에 원본_2x.mp4가 생성됩니다. 새 PowerShell을 열 때도 사용하려면 Windows의 환경 변수 → 사용자 변수 Path → 새로 만들기에서 C:\ffmpeg\bin을 추가하세요.

## remove_video_segment.py 중간 짜르기
다시 실행할 때:
python remove_video_segment.py "원본_2x.mp4" "편집완료.mp4"
다른 구간을 제거할 때:
python remove_video_segment.py "원본_2x.mp4" "편집완료.mp4" --start 00:00:30 --end 00:00:40
