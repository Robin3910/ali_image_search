from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading
import logging
import json
from alibabacloud_imagesearch20201214.client import Client
from alibabacloud_imagesearch20201214.models import AddImageAdvanceRequest
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions
import base64
import time
import math
import requests
from urllib.parse import urlparse
import os
from io import BytesIO

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 阿里云配置
ACCESS_KEY_ID = ""  # 请替换为您的AccessKey ID
ACCESS_KEY_SECRET = ""  # 请替换为您的AccessKey Secret
INSTANCE_NAME = ""  # 请替换为您的实例名称

# 限流配置
RATE_LIMIT = 200 * 1024  # 200KB/s
BUCKET_SIZE = 1024 * 1024  # 1MB 桶大小

# 创建临时目录用于存储下载的图片
TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

def download_image(url, custom_sku, index):
    """
    下载图片并返回BytesIO对象
    """
    try:
        # 下载图片
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 创建BytesIO对象
        image_data = BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                image_data.write(chunk)
        
        # 将指针移到开始位置
        image_data.seek(0)
        return image_data
    except Exception as e:
        logger.error(f"Error downloading image {url}: {str(e)}")
        return None

class RateLimiter:
    def __init__(self, rate_limit, bucket_size):
        self.rate_limit = rate_limit  # 每秒令牌数
        self.bucket_size = bucket_size  # 桶大小
        self.tokens = bucket_size  # 当前令牌数
        self.last_update = time.time()
        self.lock = threading.Lock()

    def acquire(self, size):
        """
        获取指定大小的令牌
        :param size: 需要的字节数
        :return: 需要等待的时间（秒）
        """
        with self.lock:
            now = time.time()
            # 计算从上次更新到现在应该增加的令牌数
            time_passed = now - self.last_update
            new_tokens = time_passed * self.rate_limit
            self.tokens = min(self.bucket_size, self.tokens + new_tokens)
            self.last_update = now

            if self.tokens >= size:
                self.tokens -= size
                return 0
            else:
                # 计算需要等待的时间
                wait_time = (size - self.tokens) / self.rate_limit
                self.tokens = 0
                return wait_time

# 创建限流器
rate_limiter = RateLimiter(RATE_LIMIT, BUCKET_SIZE)

# 创建线程池和任务队列
task_queue = Queue(maxsize=10000)  # 设置队列最大容量为10000
thread_pool = ThreadPoolExecutor(max_workers=5)  # 可以根据需要调整线程数

def create_client():
    """
    创建阿里云客户端
    """
    config = Config(
        access_key_id=ACCESS_KEY_ID,
        access_key_secret=ACCESS_KEY_SECRET
    )
    config.endpoint = 'imagesearch.cn-shenzhen.aliyuncs.com'
    config.region_id = 'cn-shenzhen'
    config.type = 'access_key'
    return Client(config)

def process_upload_task(task_data):
    """
    处理图片上传任务的具体实现
    """
    try:
        client = create_client()
        
        # 从请求数据中提取信息
        orders = task_data.get('orders', {}).get('orders', [])
        
        for order in orders:
            custom_sku = order.get('skus', {}).get('customSku')
            if not custom_sku:
                logger.error("Missing customSku in order")
                continue
                
            custom_images = order.get('customImages', [])
            if not custom_images:
                logger.error(f"No custom images found for SKU: {custom_sku}")
                continue
            
            # 下载并上传每个图片
            for index, image_url in enumerate(custom_images):
                start_time = time.time()  # 开始计时
                
                # 下载图片
                image_data = download_image(image_url, custom_sku, index)
                if not image_data:
                    continue
                
                # 计算图片大小（字节）
                image_size = image_data.getbuffer().nbytes
                
                # 获取限流令牌
                wait_time = rate_limiter.acquire(image_size)
                if wait_time > 0:
                    logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds for image {custom_sku}_{index}")
                    time.sleep(wait_time)

                try:
                    # 创建上传请求
                    request = AddImageAdvanceRequest()
                    request.instance_name = INSTANCE_NAME
                    request.product_id = f"{custom_sku}"
                    request.pic_name = f"{custom_sku}_image_{index}"
                    request.pic_content_object = image_data
                    request.crop = True  # 启用主体识别

                    # 发送请求
                    runtime = RuntimeOptions()
                    response = client.add_image_advance(request, runtime)

                    # 计算处理时间
                    end_time = time.time()
                    processing_time = end_time - start_time
                    print(response)
                    logger.info(f"Successfully uploaded image {custom_sku}_{index}: {response.to_map()}")
                    logger.info(f"处理耗时: {processing_time:.2f}秒, 图片大小: {image_size/1024:.2f}KB, 当前队列任务数: {task_queue.qsize()}, 本批次订单数: {len(orders)}")
                    
                finally:
                    # 确保关闭BytesIO对象
                    image_data.close()
                
    except Exception as e:
        logger.error(f"Error processing upload task: {str(e)}")

def worker():
    """
    工作线程，从队列中获取任务并处理
    """
    while True:
        task = task_queue.get()
        if task is None:
            break
        process_upload_task(task)
        task_queue.task_done()

# 启动工作线程
for _ in range(5):  # 启动5个工作线程
    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()

# # # 请求内容：
# {
#     "shopId": "4896500733967",
#     "shopName": "temu-LECOQT",
#     "orders": {
#         "orders": [
#             {
#                 "barcode_image_url": "https://yulian-temu-images.oss-cn-heyuan.aliyuncs.com/product_barcode/2025-06-10/WB2506103799038_product_barcode_1749552953135.pdf",
#                 "creationTime": "2025-06-10 14:50:39",
#                 "deliveryDeadline": "06-15 14:50:38",
#                 "orderId": "WB2506103799038",
#                 "price": 13.5,
#                 "product_img_url": "https://img.cdnfe.com/product/fancy/c9431349-4456-481a-8051-1cd0351c72f9.jpg",
#                 "quantity": 1,
#                 "shippingDeadline": "06-12 14:50:38",
#                 "shippingInfo": {
#                     "actualWarehouse": "-",
#                     "receivingTime": "-",
#                     "shippingNumber": "-",
#                     "shippingTime": "-"
#                 },
#                 "skc": "36021100740",
#                 "skus": {
#                     "customSku": "72508801565699",
#                     "property": "10pcs",
#                     "skuId": "44196921296"
#                 },
#                 "status": "待发货",
#                 "title": "定制个性化名片 - 10/30/50/1000/2000张，双面防水纸，光面设计，Angeline Smith设计模板，适用于社交与办公风格 - 可自定义图片或信息，个性化营销工具 | 现代名片设计 | 定制图形名片，个性化商务名片",
#                 "effective_image_url": "https://yulian-temu-images.oss-cn-heyuan.aliyuncs.com/temu/images/temu/images/WB2506103799038_72508801565699_1749552983346.png",
#                 "customImages": [
#                     "https://yulian-temu-images.oss-cn-heyuan.aliyuncs.com/temu/images/2025/06/10/WB2506103799038_72508801565699_1749552986020_1.png",
#                     "https://yulian-temu-images.oss-cn-heyuan.aliyuncs.com/temu/images/2025/06/10/WB2506103799038_72508801565699_1749552986483_2.png"
#                 ],
#                 "customTexts": [
#                     "",
#                     ""
#                 ]
#             }
#         ]
#     }
# }
@app.route('/upload', methods=['POST'])
def upload_image():
    """
    接收上传请求的接口
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # 验证必要字段
        if 'orders' not in data or 'orders' not in data['orders']:
            return jsonify({"error": "Invalid data format"}), 400

        # 将任务添加到队列
        task_queue.put(data)
        
        # 记录当前队列状态
        logger.info(f"新任务已加入队列，当前队列任务数: {task_queue.qsize()}，本批次订单数: {len(data['orders']['orders'])}")
        
        # 立即返回成功响应
        return jsonify({
            "status": "success",
            "message": "Upload task queued successfully",
            "queue_size": task_queue.qsize()
        }), 202

    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    """
    return jsonify({"status": "healthy"}), 200

@app.route('/queue/status', methods=['GET'])
def queue_status():
    """
    获取队列状态接口
    """
    return jsonify({
        "queue_size": task_queue.qsize(),
        "max_size": task_queue.maxsize
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8088, debug=False)
