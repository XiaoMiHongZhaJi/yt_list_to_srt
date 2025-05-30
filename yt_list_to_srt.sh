#!/bin/bash

HISTORY_DIR="history"      # 历史文件目录

mkdir -p audio $HISTORY_DIR

audio_files=$(find audio -type f \( -iname "*.aac" -o -iname "*.m4a" -o -iname "*.wav" -o -iname "*.mp3" -o -iname "*.webm" -o -iname "*.mp4" \))

if [ "$audio_files" ]; then

  echo "audio 中存在音频文件，将直接上传至通义，ctrl + c 可取消: "
  echo $audio_files
  sleep 5

else

  playlist='https://www.youtube.com/playlist?list=PLi3zrmUZHiY-eH8eNJiwj-viwP3ngIkcd'
  playlist_index=$1
  if [ -z "$playlist_index" ]; then

    echo "未传入 url 或 index，下载播放列表中的最新一个音频"
    command="--playlist-items 1 "$playlist

  elif [[ "$playlist_index" =~ ^[0-9]+$ ]]; then

    echo "下载播放列表中第 $playlist_index 个音频"
    command="--playlist-items $playlist_index "$playlist

  elif [[ "$playlist_index" =~ ^[0-9]+-[0-9]+$ ]]; then

    start=$(echo "$playlist_index" | cut -d '-' -f 1)
    end=$(echo "$playlist_index" | cut -d '-' -f 2)

    if [[ "$start" -gt "$end" ]]; then
      echo "输入有误，应为 start-end"
    else
      count=$((end - start + 1))
    fi

    echo "下载播放列表中 $count 个音频"
    command="--playlist-items $playlist_index "$playlist

  else

    echo "下载 $playlist_index 中的音频"
    command="$playlist_index"

  fi

  sleep 2

  # 如果 -f 249/250/251 下载出错，可以改为 -f wa 让 yt-dlp 自动选择最小体积音频（比较慢）
  # 存在问题： upload_date 为上传日期，不一定为直播日期
  yt-dlp $command -f 249/250/251 -o "audio/%(upload_date>%Y-%m-%d)s_%(id)s.%(ext)s" --cookies yt_cookies.txt

  if [ $? -ne 0 ]; then

    echo "yt-dlp 下载出错"
    exit 1

  fi

  echo "$(ls audio) 下载完成"
  audio_files=$(find audio -type f \( -iname "*.aac" -o -iname "*.m4a" -o -iname "*.wav" -o -iname "*.mp3" -o -iname "*.webm" -o -iname "*.mp4" \))

fi

echo "检测视频时长是否超过6小时"

MAX_DURATION=21599       # 最大时长（秒） 6小时

# 遍历音频文件
for file in $audio_files; do

  # 获取文件名（不包含扩展名）
  filename=$(basename "$file")
  filename_no_ext="${filename%.*}"
  extension="${filename##*.}"

  # 获取音频时长 (秒)
  duration=$(ffmpeg -i "$file" 2>&1 | grep "Duration" | cut -d " " -f 4 | sed s/,//)

  echo " $filename 时长 $duration"

  # 将duration转换为秒
  duration_seconds=$(echo "$duration" | awk -F ":" '{print ($1 * 3600) + ($2 * 60) + $3}')

  # 检查时长是否超过 6 小时
  if (( $(echo "$duration_seconds > $MAX_DURATION" | bc -l) )); then
    echo " $filename 时长超过 6 小时，截取前 6 小时"

    # 截取前 6 小时
    output_file="$AUDIO_DIR/${filename_no_ext}_6.${extension}"
    ffmpeg -i "$file" -t "$MAX_DURATION" -c copy "audio/$output_file"

    # 移动原始文件到 history 目录
    mv "$file" "$HISTORY_DIR/$filename"
    echo " $filename 已截取并移动原始文件"

  fi

done

echo "检测时长处理完成"

sleep 2

echo "准备启动 podcast_server"

python3 podcast_server.py > podcast_server.log 2>&1 &

if [ $? -ne 0 ]; then

  echo "启动 podcast_server 出错"
  exit 1

fi

sleep 2

echo "podcast_server 启动完成"
echo "准备上传至通义"

python3 podcast_upload.py

if [ $? -ne 0 ]; then

  echo "上传至通义出错"
  echo "结束 podcast_server"
  pkill -f "python3 podcast_server.py"
  exit 1

fi

sleep 2

echo "结束 podcast_server"
pkill -f "python3 podcast_server.py"

sleep 2

echo "移动 $(ls audio) 到 $HISTORY_DIR/"
mv audio/* $HISTORY_DIR/

echo "准备导出"

sleep 2

python3 betch_export.py $count

if [ $? -ne 0 ]; then

  echo "导出出错"
  exit 1

fi

echo "导出完成"