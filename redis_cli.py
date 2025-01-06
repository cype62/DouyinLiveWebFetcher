import redis
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RedisClient:
    def __init__(self, host='10.10.6.31', port=30379, db=12, password='interlib'):
        """
        初始化 Redis 连接
        :param host: Redis 服务器地址
        :param port: Redis 服务器端口
        :param db: Redis 数据库编号
        :param password: Redis 密码
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.connection_pool = redis.ConnectionPool(host=host, port=port, db=db, password=password)
        self.client = redis.Redis(connection_pool=self.connection_pool)

    def get(self, key):
        """
        获取指定 key 的值
        :param key: Redis key
        :return: key 对应的值，如果 key 不存在则返回 None
        """
        try:
            value = self.client.get(key)
            if value is not None:
                return value.decode('utf-8')
            return None
        except redis.exceptions.RedisError as e:
            logging.error(f"获取 Redis key {key} 时出错: {e}")
            return None

    def set(self, key, value, ex=None):
        """
        设置指定 key 的值
        :param key: Redis key
        :param value: 要设置的值
        :param ex: 过期时间（秒），可选
        :return: 是否设置成功
        """
        try:
            self.client.set(key, value, ex=ex)
            logging.info(f"已设置 Redis key: {key}")
            return True
        except redis.exceptions.RedisError as e:
            logging.error(f"设置 Redis key {key} 时出错: {e}")
            return False

    def delete(self, key):
        """
        删除指定 key
        :param key: Redis key
        :return: 是否删除成功
        """
        try:
            self.client.delete(key)
            logging.info(f"已删除 Redis key: {key}")
            return True
        except redis.exceptions.RedisError as e:
            logging.error(f"删除 Redis key {key} 时出错: {e}")
            return False

    def exists(self, key):
        """
        检查指定 key 是否存在
        :param key: Redis key
        :return: 是否存在
        """
        try:
            return self.client.exists(key)
        except redis.exceptions.RedisError as e:
            logging.error(f"检查 Redis key {key} 是否存在时出错: {e}")
            return False

    def close(self):
        """
        关闭 Redis 连接
        """
        try:
            self.client.close()
            logging.info("Redis 连接已关闭")
        except redis.exceptions.RedisError as e:
            logging.error(f"关闭 Redis 连接时出错: {e}")