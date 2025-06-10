# ali_image_search

基于阿里云图像搜索服务的图片上传和管理系统。

## 项目简介

本项目是一个基于阿里云图像搜索服务的图片上传和管理系统，主要用于处理和管理商品图片。系统提供了高效的图片上传接口，支持批量处理，并实现了请求限流和并发控制。

## 主要功能

- 支持批量图片上传
- 自动图片主体识别
- 请求限流控制
- 并发任务处理
- 健康检查接口
- 完整的日志记录

## 技术栈

- Python 3.x
- Flask
- 阿里云图像搜索服务
- 线程池
- 令牌桶限流算法

## 安装说明

1. 克隆项目到本地：
```bash
git clone [项目地址]
cd ali_image_search
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置阿里云参数：
在 `ali_image_search_server.py` 中配置以下参数：
- ACCESS_KEY_ID
- ACCESS_KEY_SECRET
- INSTANCE_NAME

## 使用方法

1. 启动服务器：
```bash
python ali_image_search_server.py
```

2. API 接口说明：

### 上传图片
- 接口：`/upload`
- 方法：POST
- 请求体格式：
```json
{
    "shopId": "店铺ID",
    "shopName": "店铺名称",
    "orders": {
        "orders": [
            {
                "orderId": "订单ID",
                "title": "商品标题",
                "price": 价格,
                "quantity": 数量,
                "skus": {
                    "customSku": "自定义SKU",
                    "skuId": "SKU ID"
                },
                "customImages": [
                    "图片URL1",
                    "图片URL2"
                ]
            }
        ]
    }
}
```

### 健康检查
- 接口：`/health`
- 方法：GET
- 返回：服务器状态信息

## 注意事项

1. 请确保已正确配置阿里云访问密钥
2. 系统默认限流为 200KB/s
3. 建议在生产环境中使用 HTTPS
4. 请妥善保管阿里云访问密钥

## 许可证

[添加许可证信息]

## 联系方式

[添加联系方式]
