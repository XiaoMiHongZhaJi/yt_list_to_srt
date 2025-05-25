import os
import sys
import time
import logging
import requests
import urllib.parse
import urllib.request
from config import headers, exportDetails, wait_mind_map_summary, wait_mind_map_summary_minutes, log_level, log_format, log_datefmt

# 设置日志
logging.basicConfig(level=log_level, format=log_format, datefmt=log_datefmt)


def request_0(record_id):
    url = "https://tw-efficiency.biz.aliyun.com/api/lab/getAllLabInfo?c=tongyi-web"
    payload = {
        "action": "getAllLabInfo",
        "transId": record_id,
        "content": [
            "labInfo",
            "labSummaryInfo"
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        response_json_0 = response.json()
        logging.debug(f"received response_json_0: {response_json_0}")
        if response_json_0['message'] == "success" and response_json_0['success']:
            return response_json_0['data']
        else:
            logging.error(f"Request 0 failed with message: {response_json_0['message']}")
            return None
    else:
        logging.error(f"Request 0 failed with status code {response.status_code}: {response.text}")
        return None


def request_1(record_id):
    url = "https://tw-efficiency.biz.aliyun.com/api/export/request?c=tongyi-web"
    payload = {
        "action": "exportTrans",
        "transIds": [record_id],
        "exportDetails": exportDetails
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        response_json_1 = response.json()
        logging.debug(f"received response_json_1: {response_json_1}")
        if response_json_1['message'] == "success" and response_json_1['success']:
            return response_json_1['data']
        else:
            logging.error(f"Request 1 failed with message: {response_json_1['message']}")
            return None
    else:
        logging.error(f"Request 1 failed with status code {response.status_code}: {response.text}")
        return None


def request_2(exportTaskId):
    url = "https://tw-efficiency.biz.aliyun.com/api/export/request?c=tongyi-web"
    payload = {
        "action": "getExportStatus",
        "exportTaskId": exportTaskId
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        response_json_2 = response.json()
        logging.debug(f"received response_json_2: {response_json_2}")
        return response_json_2['data']
    else:
        logging.error(f"Request 2 failed with status code {response.status_code}: {response.text}")
        return None


def get_record_list(page_no=1, page_size=1, record_id=None):
    url = "https://qianwen.biz.aliyun.com/assistant/api/record/list?c=tongyi-web"
    payload = {
        "status": [10, 20, 30, 33, 40, 41, 43],
        "beginTime": "",
        "endTime": "",
        "showName": "",
        "dirIdStr": "0",
        "lang": "",
        "orderType": "0",
        "orderDesc": True,
        "pageNo": page_no,
        "pageSize": page_size,
        "recordId": record_id,
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        response_get_list = response.json()
        logging.debug(f"received response_get_list: {response_get_list}")
        if response_get_list.get("errorCode"):
            logging.error(
                f'get_record_list failed: {response_get_list.get("errorCode")} {response_get_list.get("errorMsg")}')
            return []
        data = response_get_list.get("data")
        if data is None or data.get("batchRecord") is None:
            logging.info(f'get_record_list empty')
            return []
        batch_record_list = data.get("batchRecord")
        record_all_list = []
        for batch_record in batch_record_list:
            record_list = batch_record.get("recordList")
            for record_info in record_list:
                record_all_list.append({
                    "genRecordId": record_info.get("genRecordId"),
                    "recordTitle": record_info.get("recordTitle"),
                    "recordContent": record_info.get("recordContent"),
                    "recordTags": record_info.get("recordTags"),
                    "recordStatus": record_info.get("recordStatus"),
                })
        return record_all_list
    else:
        logging.error(f"Request get_record_list failed with status code {response.status_code}: {response.text}")
        return None


def export_from_record_id(record_title, record_id):
    try:
        logging.info(f"开始导出 {record_title} record_id: {record_id}")
        time.sleep(2)

        # 检测是否有思维导图
        if wait_mind_map_summary:
            mind_map_summary_done = False
            logging.info("step 0: 不跳过思维导图，检测是否有思维导图")
            time.sleep(2)
            for _ in range(wait_mind_map_summary_minutes):
                response0 = request_0(record_id)
                if response0 is not None and response0.get('labCardsMap') is not None and response0['labCardsMap'].get('labInfo') is not None:
                    labInfo = response0['labCardsMap']['labInfo']
                    if labInfo[6]['key'] == 'mindMapSummary':
                        if labInfo[6].get('contents') is not None:
                            mind_map_summary_done = True
                    else:
                        for labInfo1 in labInfo:
                            if labInfo1['key'] == 'mindMapSummary':
                                if labInfo1.get('contents') is not None:
                                    mind_map_summary_done = True
                else:
                    logging.info("step 0: 未找到功能列表")
                if mind_map_summary_done:
                    logging.info("step 0 success: 已有思维导图")
                    break
                else:
                    logging.warning(f"step 0: 思维导图未生成，1分钟后继续")
                    time.sleep(60)
            if not mind_map_summary_done:
                logging.error("step 0 error: 思维导图仍未生成，跳过检测")

        # 第一步请求
        logging.info("step 1: 查询Task ID")
        time.sleep(2)
        for _ in range(10):  # 最多重试10次
            response1 = request_1(record_id)
            if response1 is not None and response1['exportTaskId'] is not None:
                logging.info("step 1 success: 查询Task ID已就绪: " + response1['exportTaskId'])
                break
            else:
                logging.info("step 1: 查询Task ID未就绪，稍后重试")
                time.sleep(2)  # 等待2秒后重试

        if response1 is None or response1['exportTaskId'] is None:
            logging.error("step 1 error: 查询Task ID未就绪")
            return

        export_task_id = response1['exportTaskId']

        # 第二步请求
        logging.info("step 2: 查询任务状态")
        time.sleep(2)
        for _ in range(10):  # 最多重试10次
            response2 = request_2(export_task_id)
            if response2 is not None and response2['exportStatus'] == 1:
                logging.info("step 2 success: 任务状态已就绪")
                break
            else:
                logging.info("step 2: 任务状态未就绪，稍后重试")
                time.sleep(5)  # 等待5秒后重试

        if response2 is None or response2['exportStatus'] == 0:
            logging.error("step 2 error: 任务状态未就绪")
            return
        export_urls = response2['exportUrls']
        time.sleep(1)

        # 第三步请求
        logging.info("step 3: 准备导出")
        if export_urls is not None and len(export_urls) > 0:
            for url_data in export_urls:
                logging.debug(f"Export url_data: {url_data}")
                print(url_data)
                doc_type = str(url_data['docType'])
                if url_data['success']:
                    download_file(url_data['url'], record_title)
                    logging.info(f"step 3 success: 导出成功 doc_type: {doc_type}")
                    time.sleep(1)
                else:
                    logging.error(f"step 3 error: 导出失败 record_id: {record_id} doc_type: {doc_type}")

            logging.info("step 3 success: 全部导出完成")
        else:
            logging.error("导出失败: No export URLs found for record_id " + record_id)

    except Exception as e:
        logging.error(f"导出失败: {e} for record_id {record_id}")


def download_file(url, file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path)  # 创建文件夹
    # 使用 `requests` 库下载文件
    response = requests.get(url, stream=True)
    file_name = url.split("UTF-8%27%27")[-1]
    file_name = urllib.parse.unquote(file_name)
    file_name = urllib.parse.unquote(file_name)
    # 直接将文件内容写入磁盘，使用 URL 中的文件名
    with open(f'{file_path}/{file_name}', "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            f.write(chunk)


def export_from_text():
    with open('record_info.txt', 'r', encoding='utf8') as f:
        line = f.readline()
        while len(line) > 0:
            if line.find("\t") < 0 or line.startswith("#"):
                line = f.readline()
                continue
            split = line.split("\t")
            record_id = split[0]
            file_path = split[1]
            export_from_record_id(file_path, record_id)
            line = f.readline()
            time.sleep(2)


def get_list_to_file():
    page_no = 1
    page_size = 30
    record_list = get_record_list(page_no, page_size)
    if len(record_list) > 0:
        with open('record_info.txt', 'w', encoding='utf8') as f:
            f.write('#record_id\t标题\t关键字\t内容摘要\n')
    else:
        logging.error("get_record_list 为空，请检查cookie等信息")
        return

    while len(record_list) > 0:
        logging.info(f"获得{len(record_list)}条数据，准备写入文件")
        with open('record_info.txt', 'a', encoding='utf8') as f:
            for record_info in record_list:
                # 写入文件
                f.write(f"{record_info['genRecordId']}\t{record_info['recordTitle']}\t")
                if record_info['recordTags']:
                    f.write(','.join(record_info['recordTags']))
                f.write(f"\t{record_info['recordContent']}\n")
        time.sleep(1.5)
        page_no += 1
        record_list = get_record_list(page_no, page_size)

    logging.info("get_list_to_file 完成")


# 从转写列表获取最新一条并导出
def get_latest_and_export(page_size=1, record_id=None):
    page_no = 1
    for _ in range(30):  # 最多重试30次，30分钟
        record_all_done = True
        record_list = get_record_list(page_no, page_size, record_id)
        if len(record_list) == 0:
            logging.error(f"未获取到任务列表，请确认cookies是否有效")
            return
        else:
            logging.info(f"获取到 {len(record_list)} 条转写任务，检测转写任务状态")
        for record_info in record_list:
            record_title = record_info['recordTitle']
            record_status = record_info['recordStatus']
            record_id = record_info['genRecordId']
            if record_status == 40:
                logging.error(f"转写失败，请到网页查看详情。{record_title} 状态: {record_status}，id: {record_id}")
                record_all_done = False
                break
            elif record_status != 30:
                logging.info(f"转写暂未完成，一分钟后再次检测。{record_title} 状态: {record_status}，id: {record_id}")
                record_all_done = False
                time.sleep(60)
            else:
                logging.info(f"已转写完成。{record_title} 状态: {record_status}，id: {record_id}")
        if record_all_done:
            break
    if not record_all_done:
        logging.error(f"仍有转写任务未完成，请到网页查看详情")
        return
    for record_info in record_list:
        record_title = record_info['recordTitle']
        record_id = record_info['genRecordId']
        export_from_record_id(record_title, record_id)
    logging.info("get_latest_and_export 完成")


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        # 功能1: 获取最新的一条转写任务并导出数据
        logging.info("获取最新的 1 条转写任务并导出数据")
        get_latest_and_export(1)
    else:
        first_arg = args[0]
        if first_arg.isdigit():
            # 功能2: 获取最新的指定条转写任务并导出数据
            logging.info(f"获取最新的 {first_arg} 条转写任务并导出数据")
            get_latest_and_export(int(first_arg))
        elif first_arg == 'get_list_to_file':
            # 功能3: 获取所有已完成转写任务并保存到 record_info.txt
            logging.info("获取所有已完成的转写任务并保存到 record_info.txt")
            get_list_to_file()
        elif first_arg == 'export_from_text':
            # 功能4: 从 record_info.txt 中读取所有的 record_id_list 并导出数据
            logging.info("从 record_info.txt 中读取所有的 record_id_list 并导出数据")
            export_from_text()
        else:
            # 功能5: 根据指定 record_id 导出数据
            logging.info(f"从指定 record_id 导出数据：{first_arg}")
            get_latest_and_export(1, first_arg)
