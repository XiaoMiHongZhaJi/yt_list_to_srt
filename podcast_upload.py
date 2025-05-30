import sys
import time
import requests
import logging
import os
import json
import re
from tqdm import tqdm  # 导入tqdm
from config import episodes_dir, podcast_url, log_level, log_format, log_datefmt, headers


# 设置兼容 tqdm 的 logging
class TqdmLoggingHandler(logging.Handler):
    def emit(self, record):
        tqdm.write(self.format(record))


# 设置日志
logging.basicConfig(level=log_level, handlers=[TqdmLoggingHandler()], format=log_format, datefmt=log_datefmt)


# 请求1：提交podcast地址
def request_1(podcast_url):
    url = "https://tw-efficiency.biz.aliyun.com/api/trans/parseNetSourceUrl?c=tongyi-web"
    payload = {
        "action": "parseNetSourceUrl",
        "version": "1.0",
        "url": podcast_url
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        logging.debug(f"Request 1 response: {data}")
        if data.get('success', False):  # Use .get for safer access
            return data.get('data', {}).get('taskId')  # Safer access
        else:
            logging.warning("Request 1 failed: " + data.get('message', json.dumps(data)))
            return None
    else:
        logging.warning(f"Request 1 failed with status code {response.status_code}: {response.text}")
        return None


# 请求2：查询podcast音频列表
def request_2(task_id):
    url = "https://tw-efficiency.biz.aliyun.com/api/trans/queryNetSourceParse?c=tongyi-web"
    payload = {
        "action": "queryNetSourceParse",
        "version": "1.0",
        "taskId": task_id
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        logging.debug(f"Request 2 response: {data}")
        # Ensure 'data' key exists before trying to return it
        if 'data' in data:
            return data['data']
        else:
            logging.warning(f"Request 2 response missing 'data' key: {data}")
            return None
    else:
        logging.warning(f"Request 2 failed with status code {response.status_code}: {response.text}")
        return None


# 请求3：提交podcast音频解析任务
def request_3(file_id, file_size, show_name):
    url = "https://qianwen.biz.aliyun.com/assistant/api/record/blog/start?c=tongyi-web"
    payload = {
        "dirIdStr": "",
        "files": [{
            "fileId": file_id,
            "dirId": 0,
            "fileSize": file_size,
            "tag": {
                "fileType": "net_source",
                "showName": show_name,
                "lang": "cn",
                "roleSplitNum": -1,
                "translateSwitch": 0,
                "transTargetValue": 0,
                "client": "web",
                "originalTag": ""
            }
        }],
        "taskType": "net_source",
        "bizTerminal": "web"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        logging.debug(f"Request 3 response: {data}")
        if data.get('success', False) and data.get('data') and data['data'].get('recordIdList'):
            return data['data']['recordIdList'][0]
        else:
            logging.warning("Request 3 failed or missing data: " + data.get('errorMsg', json.dumps(data)))
            return None
    else:
        logging.warning(f"Request 3 failed with status code {response.status_code}: {response.text}")
        return None


# 请求4：查询音频解析状态
def request_4(page_size=1):
    url = "https://qianwen.biz.aliyun.com/assistant/api/record/list/poll?c=tongyi-web"
    payload = {
        "status": [10, 20, 30, 40, 41],
        "recordSources": ["chat", "zhiwen", "tingwu"],
        "taskTypes": ["local", "net_source", "doc_read", "url_read", "paper_read", "book_read", "doc_convert"],
        "terminal": "web",
        "module": "uploadhistory",
        "pageNo": 1,
        "pageSize": page_size
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        logging.debug(f"Request 4 response: {data}")
        if data.get('success', False) and 'data' in data:
            return data['data']
        else:
            logging.warning(f"Request 4 failed or missing data: {data.get('errorMsg', json.dumps(data))}")
            return None
    else:
        logging.warning(f"Request 4 failed with status code {response.status_code}: {response.text}")
        return None


# 执行流程：顺序调用请求
def process_podcast(podcast_url):
    try:
        # 请求1：提交podcast地址
        logging.info(f"step 1: 准备提交 podcast 地址: {podcast_url}")
        time.sleep(2)
        task_id = request_1(podcast_url)
        if task_id is None:
            logging.error("step 1 error: 提交 podcast 地址失败")
            sys.exit(1)  # 失败退出
        logging.info(f"step 1 success: 已提交 podcast 地址，Task ID: {task_id}")

        # 请求2：查询podcast音频列表
        task_status_data = None
        logging.info("step 2: 准备解析音频列表")
        time.sleep(2)
        with tqdm(range(30), desc="等待解析音频列表") as progress:
            for _ in progress:
                task_status_data = request_2(task_id)
                if task_status_data is None:
                    logging.info("step 2: 解析音频列表未就绪，稍后重试")
                    time.sleep(2)
                    continue
                status = task_status_data.get('status')
                if status == 0:
                    progress.n = progress.total
                    progress.set_description(f"解析音频列表已就绪")
                    progress.close()
                    break
                elif status > 0:
                    error_type = task_status_data.get('type', 'unknown')
                    logging.error(f"step 2: 解析音频列表失败，status: {status}, type: {error_type}")
                    logging.warning(f"请先确认 {podcast_url} 可以正常访问（可在 链接速读->播客链接转写 中进行测试）")
                    progress.set_description(f"解析音频列表超时")
                    progress.close()
                    sys.exit(1)
                time.sleep(2)

        if task_status_data is None or task_status_data.get('status') != 0:
            logging.error("step 2 error: 解析音频列表超时或失败")
            sys.exit(1)
        logging.info("step 2 success: 解析音频列表已就绪")

        # 请求3：提交音频解析任务
        urls_to_process = task_status_data.get('urls', [])
        count = len(urls_to_process)
        if count == 0:
            logging.error(f"step 3 error: 提交音频解析任务失败，未解析到音频。")
            sys.exit(1)

        logging.info(f"step 3: 准备提交 {count} 个音频解析任务")

        for url_item in tqdm(urls_to_process, desc="提交音频解析任务", unit="个"):
            file_id = url_item.get('fileId')
            file_size = url_item.get('size')
            show_name = url_item.get('showName', 'unknown')  # Default name
            time.sleep(2)
            record_id = request_3(file_id, file_size, show_name)
            if record_id is None:
                logging.warning(f"step 3: {show_name} 提交完成，但获取 Record ID 失败，请到网页查看进度")
            else:
                logging.info(f"step 3 success: 提交完成 {show_name} Record ID: {record_id}")
        logging.info(f"step 3 success: 提交音频解析任务完成")

        # 请求4：查询音频解析状态
        logging.info(f"step 4: 查询音频解析状态")
        time.sleep(2)
        all_task_done = False
        with tqdm(range(100), desc=f"检测音频解析状态") as progress:
            for _ in progress:
                record_data = request_4(page_size=count)
                if record_data is None or not record_data.get('batchRecord'):
                    logging.info(f"step 4: 获取音频解析状态失败，稍后重新检测")
                    time.sleep(20)
                    continue
                batch_record = record_data.get('batchRecord')
                all_count = len(batch_record)
                done_count = 0
                for record in batch_record:
                    record_task = record.get('recordList')[0]
                    record_status = record_task.get('recordStatus')
                    if record_status == 40:
                        msg = f" {record_task.get('recordTitle')}, code: {record_status}, " \
                              f"errorCode: {record_task.get('oriErrorCode')}, " \
                              f"msg: {record_task.get('oriErrorMsg')}"
                        logging.error(f"step 4 error: 音频解析任务失败，请到网页查看详情: {msg}")
                        progress.set_description(f"音频解析任务失败")
                        progress.close()
                        sys.exit(1)
                    elif record_status == 30:
                        done_count += 1
                    else:
                        logging.debug(
                            f"step 4: 音频解析任务未完成 {record_task.get('recordTitle')}, code: {record_status}")
                progress.set_description(f"检测音频解析状态 {done_count + 1} / {all_count}")
                if done_count == all_count:
                    all_task_done = True
                    progress.set_description(f"音频解析任务完成 {done_count} / {all_count}")
                    progress.n = progress.total
                    progress.close()
                    break
                time.sleep(20)

            if not all_task_done:
                logging.warning(f"step 4: 音频解析任务超时未完成")
            else:
                logging.info(f"step 4 success: 音频解析任务完成")
        return count
    except Exception as e:
        logging.error(f"提交音频解析任务出错: {e}")
        sys.exit(1)


def check_date(episodes_dir: str, json_path: str = 'yt_list_info.json'):
    if not os.path.exists(json_path):
        logging.debug(f"未找到 JSON 文件：{json_path}，跳过日期检查")
        return

    # 加载 JSON 数据
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            yt_info_list = json.load(f)
        except json.JSONDecodeError:
            logging.debug(f"JSON 文件格式不正确：{json_path}")
            return

    # 构建 ID 到 liveDate 的映射
    id_to_date = {item["id"]: item["liveDate"] for item in yt_info_list if "id" in item and "liveDate" in item}

    # 遍历 episodes_dir 中的文件
    for filename in tqdm(os.listdir(episodes_dir), desc="文件名日期检测", unit="个"):
        match = re.match(r'^(\d{4}-\d{2}-\d{2})_([a-zA-Z0-9_-]{11})', filename)
        if not match:
            continue  # 跳过不符合命名规则的文件

        file_date_str, video_id = match.groups()
        expected_date = id_to_date.get(video_id)

        if not expected_date:
            logging.info(f"找不到 ID {video_id} 的直播日期，跳过检测：{filename}")
            continue

        if file_date_str != expected_date:
            # 构建新文件名
            new_filename = filename.replace(file_date_str, expected_date, 1)
            old_path = os.path.join(episodes_dir, filename)
            new_path = os.path.join(episodes_dir, new_filename)

            # 重命名文件
            os.rename(old_path, new_path)
            logging.info(f"文件日期与开播日期不一致，已重命名：{filename} -> {new_filename}")


if __name__ == '__main__':
    check_date(episodes_dir)
    process_podcast(podcast_url)
