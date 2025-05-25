import sys
import time
import requests
import logging
import json
from config import podcast_url, log_level, log_format, log_datefmt, headers

# 设置日志
logging.basicConfig(level=log_level, format=log_format, datefmt=log_datefmt)


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
        if data['success']:
            return data['data']['taskId']
        else:
            logging.error("Request 1 failed: " + data.get('message', json.dumps(data)))
            return None
    else:
        logging.error(f"Request 1 failed with status code {response.status_code}: {response.text}")
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
        return data['data']
    else:
        logging.error(f"Request 2 failed with status code {response.status_code}: {response.text}")
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
        if data.get('success', False):
            return data['data']['recordIdList'][0]
        else:
            logging.error("Request 3 failed: " + data.get('errorMsg', json.dumps(data)))
            return None
    else:
        logging.error(f"Request 3 failed with status code {response.status_code}: {response.text}")
        return None


# 请求4：查询音频解析任务状态
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
        return data['data']
    else:
        logging.error(f"Request 4 failed with status code {response.status_code}: {response.text}")
        return None


# 执行流程：顺序调用请求
def process_podcast(podcast_url):
    try:
        # 请求1：提交podcast地址
        logging.info(f"step 1: 准备提交podcast地址: {podcast_url}")
        time.sleep(2)
        task_id = request_1(podcast_url)
        if task_id is not None:
            logging.info(f"step 1 success: 已提交podcast地址 Task ID: {task_id}")
        else:
            logging.error("step 1 error: 提交podcast地址失败")
            sys.exit(1) # 失败退出

        # 请求2：查询podcast音频列表
        task_status = None
        logging.info("step 2: 解析音频列表")
        time.sleep(2)
        for _ in range(10):  # 最多重试10次
            task_status = request_2(task_id)
            status = task_status['status']
            if status == 0:  # 如果状态为0，任务已就绪
                logging.info("step 2 success: 解析音频列表已就绪")
                break
            elif status < 0:
                logging.info("step 2: 解析音频列表未就绪，稍后重试")
                time.sleep(5)  # 等待5秒后重试
            else:
                logging.error(f"step 2: 解析音频列表失败，status: {status}, type: {task_status['type']}")
                logging.warning(f"请先确认 {podcast_url} 可以正常访问（可在 链接速读->播客链接转写 中进行测试）")
                sys.exit(1) # 失败退出

        if task_status['status'] != 0:
            logging.error("step 2 error: 解析音频列表超时")
            sys.exit(1) # 失败退出

        # 请求3：提交音频解析任务
        urls = task_status['urls']
        count = len(urls)
        if count == 0:
            logging.error(f"step 3 error: 提交失败，请到网页查看详情")
            sys.exit(1) # 失败退出
        elif count == 1:
            # 单个任务
            file_id = urls[0]['fileId']
            file_size = urls[0]['size']
            show_name = urls[0]['showName']
            logging.info("step 3: 提交音频解析任务")
            time.sleep(2)
            record_id = request_3(file_id, file_size, show_name)
            if record_id is None:
                logging.warning(f"step 3 error: 提交音频解析任务完成，但获取 Record ID 失败，请到网页查看进度")
            else:
                logging.info(f"step 3 success: 提交音频解析任务完成 Record ID: {record_id}")

            # 请求4：查询音频解析任务状态
            record_done = False
            logging.info("step 4: 查询音频解析任务状态")
            time.sleep(2)
            for _ in range(60):
                record_status = request_4()
                if record_status is not None and record_status['batchRecord'][0]['recordList'] is not None:
                    record_task = record_status['batchRecord'][0]['recordList'][0]
                    if record_task['recordStatus'] == 40:  # 解析失败
                        msg = f"title: {record_task['recordTitle']}, code: {record_task['recordStatus']}, {record_task['oriErrorCode']}, msg: {record_task['oriErrorMsg']}"
                        logging.error(f"step 4 error: 音频解析任务失败: {msg}")
                        break
                    elif record_task['recordStatus'] == 30:
                        logging.info("step 4 success: 音频解析任务完成")
                        record_done = True
                        break
                    else:
                        logging.info("step 4: 音频解析任务未完成，稍后重新检测")
                        time.sleep(30)
                else:
                    logging.info("step 4: 音频解析任务未完成，稍后重新检测")
                    time.sleep(30)
            if not record_done:
                logging.error("step 4: 音频解析任务未完成")
            return record_id
        else:
            # 多个任务
            logging.info(f"step 3: 提交音频解析任务，共 {count} 个")
            time.sleep(2)
            record_id_list = []
            for url in urls:
                file_id = url['fileId']
                file_size = url['size']
                show_name = url['showName']
                record_id = request_3(file_id, file_size, show_name)
                if record_id is None:
                    logging.warning(f"step 3: 提交单个音频解析任务完成，但获取 Record ID 失败，请到网页查看进度")
                    break
                logging.info(f"step 3: 提交单个音频解析任务完成 Record ID: {record_id}")
                record_id_list.append(record_id)
            count = len(record_id_list)
            if count > 0:
                # 请求4：查询音频解析任务状态
                logging.info("step 4: 查询音频解析任务状态")
                time.sleep(2)
                for record_id in record_id_list:
                    for _ in range(60):
                        record_status = request_4(count)
                        if record_status is not None and record_status['batchRecord'][0]['recordList'] is not None:
                            record_task = record_status['batchRecord'][0]['recordList'][0]
                            if record_task['recordStatus'] == 40:  # 解析失败
                                msg = f"title: {record_task['recordTitle']}, code: {record_task['recordStatus']}, {record_task['oriErrorCode']}, msg: {record_task['oriErrorMsg']}"
                                logging.error(f"step 4 error: 解析单个音频任务失败，请到网页查看详情: {msg}")
                                break
                            elif record_task['recordStatus'] == 30:
                                logging.info(f"step 4 success: 解析单个音频任务完成: {record_id}")
                                break
                            else:
                                logging.info(f"step 4: 解析单个音频任务未完成，稍后重新检测: {record_id}")
                                time.sleep(30)
                        else:
                            logging.info("step 4: 解析单个音频任务未完成，稍后重新检测")
                            time.sleep(30)
                    time.sleep(2)
                logging.info(f"step 4 success: 解析音频任务任务完成")
            return count

    except Exception as e:
        logging.error(f"提交音频解析任务出错: {e}")
        sys.exit(1) # 失败退出


if __name__ == '__main__':
    process_podcast(podcast_url)
