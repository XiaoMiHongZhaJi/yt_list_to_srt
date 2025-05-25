#!/bin/bash

mkdir -p audio history
audio_files=$(find audio -type f | grep -E '.(aac|m4a|wav|mp3|webm|mp4)$')

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

  # 如果 -f 249 下载出错，可以改为 -f wa 让yt-dlp自动选择最小体积音频
  # 存在问题： upload_date 不一定准确
  yt-dlp $command -f 249 -o "audio/%(upload_date>%Y-%m-%d)s_%(id)s.%(ext)s" --cookies yt_cookies.txt

  if [ $? -ne 0 ]; then

    echo "yt-dlp 下载出错"
    exit 1

  fi

  echo "$(ls audio) 下载完成"

fi


echo "准备启动 podcast_server"

python3 podcast_server.py &

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

echo "移动 $(ls audio) 到 history/"
mv audio/* history/

echo "准备导出"

sleep 2

python3 betch_export.py $count

if [ $? -ne 0 ]; then

  echo "导出出错"
  exit 1

fi

echo "导出完成"