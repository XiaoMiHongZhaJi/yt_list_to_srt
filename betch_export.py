import os
import sys
import time
import logging
import requests
import urllib.parse
import urllib.request
from tqdm import tqdm
from config import headers, exportDetails, wait_mind_map_summary, wait_mind_map_summary_minutes, log_level, log_format, \
    log_datefmt, result_dir


# 设置兼容 tqdm 的 logging
class TqdmLoggingHandler(logging.Handler):
    def emit(self, record):
        tqdm.write(self.format(record))


# 设置日志
logging.basicConfig(level=log_level, handlers=[TqdmLoggingHandler()], format=log_format, datefmt=log_datefmt)


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
            logging.warning(f"Request 0 failed with message: {response_json_0['message']}")
            return None
    else:
        logging.warning(f"Request 0 failed with status code {response.status_code}: {response.text}")
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
            logging.warning(f"Request 1 failed with message: {response_json_1['message']}")
            return None
    else:
        logging.warning(f"Request 1 failed with status code {response.status_code}: {response.text}")
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
        logging.warning(f"Request 2 failed with status code {response.status_code}: {response.text}")
        return None


def get_record_list(page_no=1, page_size=1, show_name=None):
    url = "https://qianwen.biz.aliyun.com/assistant/api/record/list?c=tongyi-web"
    payload = {
        "status": [10, 20, 30, 33, 40, 41, 43],
        "beginTime": "",
        "endTime": "",
        "showName": show_name,
        "dirIdStr": "0",
        "lang": "",
        "orderType": "0",
        "orderDesc": True,
        "pageNo": page_no,
        "pageSize": page_size,
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        response_get_list = response.json()
        logging.debug(f"received response_get_list: {response_get_list}")
        if response_get_list.get("errorCode"):
            logging.warning(f'get_record_list failed: {response_get_list.get("errorCode")} {response_get_list.get("errorMsg")}')
            return []
        data = response_get_list.get("data")
        if data is None or data.get("batchRecord") is None:
            logging.warning(f'get_record_list empty')
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
        logging.warning(f"Request get_record_list failed with status code {response.status_code}: {response.text}")
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
            # 使用tqdm包装等待循环
            with tqdm(range(wait_mind_map_summary_minutes), desc="检测思维导图生成状态") as progress:
                for _ in progress:
                    response0 = request_0(record_id)
                    if response0 is not None and response0.get('labCardsMap') is not None and response0['labCardsMap'].get('labInfo') is not None:
                        lab_info = response0['labCardsMap']['labInfo']
                        for lab_item in lab_info:
                            if lab_item.get('key') == 'mindMapSummary' and lab_item.get('contents') is not None:
                                mind_map_summary_done = True
                                break
                    else:
                        logging.error("step 0: 未找到功能列表，稍后重试")
                    if mind_map_summary_done:
                        progress.n = progress.total
                        progress.set_description(f"思维导图已生成")
                        progress.close()
                        break
                    time.sleep(60)

            if mind_map_summary_done:
                logging.info("step 0 success: 思维导图已生成")
            else:
                logging.error("step 0 error: 思维导图仍未生成，跳过导出")

        # 第一步请求
        logging.info("step 1: 查询 Task ID")
        time.sleep(2)
        response1 = None
        # 使用tqdm包装重试循环
        with tqdm(range(30), desc="查询 Task ID") as progress:
            for i in progress:
                response1 = request_1(record_id)
                if response1 is not None and response1.get('exportTaskId') is not None:
                    progress.n = progress.total
                    progress.set_description(f"查询 Task ID 已就绪")
                    progress.close()
                    break
                time.sleep(2)

        if response1 is None or response1.get('exportTaskId') is None:
            logging.error("step 1 error: 查询 Task ID 失败")
            sys.exit(1)
        logging.info("step 1 success: 查询 Task ID 已就绪: " + response1['exportTaskId'])

        export_task_id = response1['exportTaskId']

        # 第二步请求
        logging.info("step 2: 查询任务状态")
        time.sleep(2)
        response2 = None
        # 使用tqdm包装重试循环
        progress = tqdm(range(30), desc="查询任务状态是否已就绪")
        for _ in progress:
            response2 = request_2(export_task_id)
            if response2 is not None and response2.get('exportStatus') == 1:
                progress.n = progress.total
                progress.set_description(f"任务状态已就绪")
                progress.close()
                break
            time.sleep(2)

        if response2 is None or response2.get('exportStatus') == 0:
            logging.error("step 2 error: 任务状态未就绪")
            sys.exit(1)
        logging.info("step 2 success: 任务状态已就绪")

        export_urls = response2['exportUrls']
        # 第三步请求
        logging.info("step 3: 准备导出")
        if export_urls is not None and len(export_urls) > 0:
            # 使用tqdm包装下载文件的循环
            for url_data in tqdm(export_urls, desc=f"导出文件 {record_title}", unit="个"):
                time.sleep(1)
                logging.debug(f"Export url_data: {url_data}")
                doc_type = str(url_data['docType'])
                if url_data['success']:
                    download_file(url_data['url'], result_dir + record_title)
                    logging.info(f"step 3 success: 导出成功 doc_type: {doc_type}")
                else:
                    logging.error(f"step 3 error: 导出失败 record_id: {record_id} doc_type: {doc_type}")

            logging.info(f"step 3 success: {record_title} 导出完成")
        else:
            logging.error("导出失败，record_id: " + record_id)

    except Exception as e:
        logging.error(f"导出失败: {e} record_id: {record_id}")


def download_file(url, file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path)  # 创建文件夹
    # 使用 `requests` 库下载文件
    response = requests.get(url, stream=True)
    response.raise_for_status()
    file_name = url.split("UTF-8%27%27")[-1]
    file_name = urllib.parse.unquote(file_name)
    file_name = urllib.parse.unquote(file_name)
    # 直接将文件内容写入磁盘，使用 URL 中的文件名
    with open(f'{file_path}/{file_name}', "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            f.write(chunk)


def export_from_text():
    try:
        with open('record_info.txt', 'r', encoding='utf8') as f_count:
            lines_to_process = [line for line in f_count if line.strip() and not line.startswith("#") and "\t" in line]
        total_lines = len(lines_to_process)
    except FileNotFoundError:
        logging.error("record_info.txt 未找到！")
        return

    if total_lines == 0:
        logging.warning("record_info.txt中没有有效记录可供导出。")
        return

    with open('record_info.txt', 'r', encoding='utf8') as f:
        for line in tqdm(f, total=total_lines, desc="从record_info.txt导出", unit="条"):
            line = line.strip()
            if not line or line.startswith("#") or "\t" not in line:
                continue
            split_parts = line.split("\t")
            if len(split_parts) < 2:
                logging.warning(f"跳过格式不正确的行: {line}")
                continue
            record_id = split_parts[0]
            file_path_title = split_parts[1]

            export_from_record_id(file_path_title, record_id)
            time.sleep(2)  # 保持原有的延时


def get_list_to_file():
    page_no = 1
    page_size = 30

    # 初始获取，确定是否需要写入文件头
    logging.info(f"获取任务列表，页码: {page_no}, 每页大小: {page_size}")
    record_list = get_record_list(page_no, page_size)
    if not record_list:  # 检查列表是否为空或者None
        logging.error("获取任务列表为空，请检查cookie等信息或网络。")
        return

    with open('record_info.txt', 'w', encoding='utf8') as f:
        f.write('#record_id\t标题\t关键字\t内容摘要\n')

    # 使用一个不确定总数的tqdm进度条来显示处理的页数
    with tqdm(desc="获取任务列表并写入记录", unit="页") as pbar_pages:
        while record_list:  # 只要record_list不为空就继续
            pbar_pages.set_postfix_str(f"当前页: {page_no}, 获取到: {len(record_list)}条")
            logging.info(f"获得{len(record_list)}条数据，准备写入文件 (来自页码 {page_no})")
            with open('record_info.txt', 'a', encoding='utf8') as f:
                # 为当前页的记录写入添加一个内部进度条
                for record_info in tqdm(record_list, desc=f"写入第{page_no}页记录", unit="条"):
                    f.write(f"{record_info['genRecordId']}\t{record_info['recordTitle']}\t")
                    if record_info.get('recordTags'):  # 检查是否存在
                        f.write(','.join(record_info['recordTags']))
                    f.write(f"\t{record_info.get('recordContent', '')}\n")  # 确保内容存在

            time.sleep(1.5)
            page_no += 1
            pbar_pages.update(1)  # 更新页数进度条
            logging.info(f"准备获取下一页: {page_no}")
            record_list = get_record_list(page_no, page_size)
            if record_list is None:
                logging.info(f"获取第 {page_no} 页记录为空，停止获取。")
                break

    logging.info("get_list_to_file 完成")


# 从转写列表获取最新一条并导出
def get_latest_and_export(page_size=1, show_name=None):
    page_no = 1
    all_task_done = False
    record_list = []
    logging.info(f"检测转写任务状态状态")
    progress = tqdm(range(30), desc="检测转写任务状态")
    for _ in progress:  # 最多重试30次，30分钟
        record_list = get_record_list(page_no, page_size, show_name)
        if len(record_list) == 0:
            logging.error(f"未获取到任务列表，请确认 cookies{'' if show_name is None else ' / 关键字'} 是否有效")
            progress.set_description(f"查询转写任务状态失败")
            progress.close()
            sys.exit(1)
        all_count = len(record_list)
        done_count = 0
        for record_info in record_list:
            record_title = record_info['recordTitle']
            record_status = record_info['recordStatus']
            record_id = record_info['genRecordId']
            if record_status == 40:
                logging.error(f"{record_id} 转写失败，请到网页查看详情。{record_title} 状态: {record_status}")
                progress.set_description(f"转写失败")
                progress.close()
                sys.exit(1)
            elif record_status == 30:
                done_count += 1
            else:
                logging.debug(f"{record_id} 转写暂未完成 {record_title} 状态: {record_status}")
        progress.set_description(f"检测转写任务状态 {done_count + 1} / {all_count}")
        if done_count == all_count:
            all_task_done = True
            progress.n = progress.total
            progress.set_description(f"转写任务已完成")
            progress.close()
            break
        time.sleep(60)

    if not all_task_done:
        logging.error(f"转写任务超时未完成，请到网页查看详情")
        sys.exit(1)
    logging.info(f"已转写完成，准备导出")
    time.sleep(2)
    record_count = len(record_list)
    if record_count == 1:
        record_info = record_list[0]
        record_title = record_info['recordTitle']
        record_id = record_info['genRecordId']
        export_from_record_id(record_title, record_id)
    else:
        progress = tqdm(record_list, desc="导出转写任务", unit="个")
        done_count = 0
        for record_info in progress:
            record_title = record_info['recordTitle']
            record_id = record_info['genRecordId']
            export_from_record_id(record_title, record_id)
            done_count += 1
            progress.set_description(f"导出转写任务 {done_count} / {record_count}")
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
            # 功能5: 从指定名称导出数据（模糊查询，匹配第一个）
            logging.info(f"从指定名称导出数据：{first_arg}")
            get_latest_and_export(1, first_arg)
