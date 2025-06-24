# yt_list_to_srt

#### 自动将yt播放列表中的视频转换为音频并上传到通义，生成字幕、总结、脑图，然后自动导出

## 实现原理

通义的 <b>链接速读 -> 播客链接转写</b> 功能支持传入一个播客（podcast）链接地址，因此只需要在本地搭建一个 podcast 服务，即可实现自动提交。再配合导出接口，即可自动导出。

## 使用前的准备

<b>⚠️ 由于通义官方的限制，自动上传至通义需要一台国内的服务器和一个域名解析到这个服务器</b>

<b>⚠️ 如果自己宽带有公网ip，且打开端口映射充当服务器也可以</b>

⬇️ 在 <code>config.py</code> 中配置如下内容：

➡️ 自己服务器的域名 (podcast_url)

➡️ 自己通义账号的 cookie (在通义页面按 F12，request headder 中的 Cookie 值)

➡️ podcast 服务监听的端口号

⚠️ 如果被 youtube 黑名单，则需要新建一个 <code>yt_cookies.txt</code> 并配置自己的 youtube cookie (使用 Get cookies.txt LOCALLY 等插件即可获取)

## 使用方式

1、<code>yt_list_to_srt.sh</code>

➡️ 若 audio 中存在音频文件，则将其上传至通义，生成并导出字幕、导读、脑图

➡️ 若没有，则下载播放列表中的第一个视频的音频，上传至通义，生成并导出字幕、导读、脑图

<b>如需指定播放列表，请在<code>yt_list_to_srt.sh</code>中修改</b>

<hr>

2、<code>yt_list_to_srt.sh 5</code>

下载播放列表中的第 5 个视频的音频，上传至通义，生成并导出字幕、导读、脑图

<hr>

3、<code>yt_list_to_srt.sh 1-5</code>

下载播放列表中的第 1 到第 5 个视频的音频，上传至通义，生成并导出字幕、导读、脑图

<hr>

4、<code>yt_list_to_srt.sh https://www.youtube.com/watch?v=c5Nr_iD-s7Y </code>

下载指定视频的音频，上传至通义，生成并导出字幕、导读、脑图

<hr>

5、<code>python podcast_server.py</code>

启动本地 podcast 服务，默认将 audio 中的音频文件发布到 podcast

<hr>

6、<code>python podcast_upload.py</code>

将本地 podcast 服务中的音频提交到通义，并生成字幕、导读、脑图

<hr>

7、<code>python betch_export.py</code>

获取通义最新的 1 条转写任务并导出字幕、导读、脑图

<hr>

8、<code>python betch_export.py 3</code>

获取通义最新的 3 条转写任务并导出字幕、导读、脑图

<hr>

9、<code>python betch_export.py get_list_to_file</code>

获取通义所有已完成的转写任务并保存到 record_info.txt

<hr>

10、<code>python betch_export.py export_from_text</code>

从 record_info.txt 中读取所有的 record_id_list 并导出字幕、导读、脑图

<hr>

11、<code>python betch_export.py record_id</code>

从指定 record_id 导出字幕、导读、脑图

