import logging

# 配置文件
# 音频文件存放位置
episodes_dir = 'audio/'

# 导出结果存放位置
result_dir = 'result/'

# podcast 服务监听端口
port = 55001

# podcast 服务地址（必须使用域名，且解析ip是国内ip，否则会失败）
podcast_url = f"http://你的域名:{port}/podcast/"

# 传入的cookie
cookie = "你的通义cookies"

# 是否等待思维导图（生成可能很慢）
wait_mind_map_summary = True

# 等待思维导图时间（分钟）
wait_mind_map_summary_minutes = 30

# 需要导出的文件类型
exportDetails = [
    {"docType": 1, "fileType": 3, "withSpeaker": True, "withTimeStamp": True},  # md格式 原文
    {"docType": 1, "fileType": 2, "withSpeaker": True, "withTimeStamp": True},  # srt格式 字幕
    {"docType": 7, "fileType": 3},  # md格式 导读
    {"docType": 8, "fileType": 3},  # md格式 脑图
    {"docType": 8, "fileType": 6},  # jpg格式 脑图
]

log_level = logging.INFO
log_format = '%(asctime)s %(levelname)s: %(message)s'
log_datefmt = '%Y-%m-%d %H:%M:%S'

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json',
    'cookie': cookie,
    'dnt': '1',
    'origin': 'https://tongyi.aliyun.com',
    'priority': 'u=1, i',
    'referer': 'https://tongyi.aliyun.com/efficiency/folders/0',
    'sec-ch-ua': '"Not;A=Brand";v="24", "Chromium";v="128"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'x-b3-sampled': '1',
    'x-b3-spanid': 'b60c493cb704bb52',
    'x-b3-traceid': 'd6c6403e8d3088ec0503929088363c22',
    'x-tw-canary': '',
    'x-tw-from': 'tongyi'
}