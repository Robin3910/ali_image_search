# 阿里云配置
ALIYUN_CONFIG = {
    'ACCESS_KEY_ID': "",
    'ACCESS_KEY_SECRET': "",
    'INSTANCE_NAME': "",
    'ENDPOINT': 'imagesearch.cn-shenzhen.aliyuncs.com',
    'REGION_ID': 'cn-shenzhen',
    'USE_INTERNAL_ENDPOINT': False  # 是否使用内网访问
}

# 数据库配置
DB_CONFIG = {
    'host': '',
    'user': '',
    'password': '',
    'database': '',
    'charset': 'utf8mb4'
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# 图片删除配置
DELETE_CONFIG = {
    'DAYS_AGO': 3,  # 删除几天前的数据
    'REQUEST_DELAY': 0.1  # 请求延迟时间（秒）
} 