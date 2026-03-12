import os
import datetime
from typing import Optional
from minio import Minio
from minio.error import S3Error


class MinioLogManager:
    """
    MinIO日志管理SDK
    用于将测试日志文件按照指定路径规则上传到MinIO对象存储
    """

    def __init__(self, endpoint: str = None, access_key: str = None,
                 secret_key: str = None, bucket_name: str = None, secure: bool = False):
        """
        初始化MinIO客户端

        Args:
            endpoint: MinIO服务器地址 (格式: host:port)
            access_key: MinIO访问密钥
            secret_key: MinIO秘密密钥
            bucket_name: 存储桶名称
            secure: 是否使用HTTPS (内网部署通常为False)
        """
        # 默认配置
        self.endpoint = endpoint or "10.17.154.252:9003"
        self.access_key = access_key or "admin"
        self.secret_key = secret_key or "12345678"
        self.bucket_name = bucket_name or "auto-test-logs"
        self.secure = secure

        # 初始化MinIO客户端
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        # 确保Bucket存在
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> bool:
        """
        检查并创建Bucket（如果不存在）

        Returns:
            bool: Bucket存在或创建成功返回True
        """
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Bucket '{self.bucket_name}' 已创建")
            return True
        except S3Error as e:
            print(f"Bucket检查/创建失败: {e}")
            return False

    def upload_test_log(self, project: str, machine_ip: str, test_plan_id: str,
                       local_file_path: str, custom_date: str = None,
                       chunk_size: int = None) -> Optional[str]:
        """
        上传日志文件（支持普通上传和分块上传）

        路径格式：项目名/测试机器/日期/执行批次号/文件名

        Args:
            project: 项目名称
            machine_ip: 测试机器IP地址或机器名
            test_plan_id: 测试计划ID
            local_file_path: 本地文件路径
            custom_date: 自定义日期 (格式: YYYY-MM-DD, 默认为当前日期)
            chunk_size: 分块大小（字节），None表示使用普通上传，非None表示使用分块上传

        Returns:
            str: 成功时返回下载链接，失败时返回None

        Raises:
            FileNotFoundError: 当本地文件不存在时
        """
        # 1. 验证本地文件
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"本地文件 {local_file_path} 不存在")

        # 2. 构建云端路径
        if custom_date:
            date_str = custom_date
        else:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        file_name = os.path.basename(local_file_path)
        object_name = f"{project}/{machine_ip}/{date_str}/{test_plan_id}/{file_name}"

        # 3. 执行上传
        try:
            file_size = os.path.getsize(local_file_path)

            if chunk_size is None:
                # 普通上传（小文件）
                self.client.fput_object(
                    self.bucket_name,
                    object_name,
                    local_file_path
                )
                print(f"成功上传: {object_name}")
            else:
                # 分块上传（大文件）
                with open(local_file_path, 'rb') as file_data:
                    self.client.put_object(
                        self.bucket_name,
                        object_name,
                        file_data,
                        length=file_size,
                        part_size=chunk_size
                    )
                print(f"分块上传成功: {object_name} (大小: {file_size} bytes)")

            # 4. 生成下载链接 (默认7天有效期)
            download_url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
            )
            return download_url

        except S3Error as e:
            print(f"MinIO 上传失败: {e}")
            return None

    def upload_multiple_logs(self, project: str, machine_ip: str, test_plan_id: str,
                           local_file_paths: list, custom_date: str = None) -> dict:
        """
        批量上传多个日志文件

        Args:
            project: 项目名称
            machine_ip: 测试机器IP地址或机器名
            test_plan_id: 测试计划ID
            local_file_paths: 本地文件路径列表
            custom_date: 自定义日期

        Returns:
            dict: 上传结果字典 {文件路径: 下载链接或错误信息}
        """
        results = {}

        for file_path in local_file_paths:
            if os.path.exists(file_path):
                url = self.upload_test_log(project, machine_ip, test_plan_id,
                                         file_path, custom_date)
                results[file_path] = url if url else "上传失败"
            else:
                results[file_path] = "文件不存在"

        return results

    def upload_log_auto(self, project: str, machine_ip: str, test_plan_id: str,
                       local_file_path: str, custom_date: str = None,
                       large_file_threshold: int = 100 * 1024 * 1024,
                       chunk_size: int = 5 * 1024 * 1024) -> Optional[str]:
        """
        智能上传日志文件（自动选择上传方式）

        根据文件大小自动选择使用普通上传或分块上传
        - 小文件（< threshold）：使用普通上传
        - 大文件（>= threshold）：使用分块上传

        Args:
            project: 项目名称
            machine_ip: 测试机器IP地址或机器名
            test_plan_id: 测试计划ID
            local_file_path: 本地文件路径
            custom_date: 自定义日期 (格式: YYYY-MM-DD, 默认为当前日期)
            large_file_threshold: 大文件阈值（字节），默认100MB
            chunk_size: 分块大小（字节），默认5MB

        Returns:
            str: 成功时返回下载链接，失败时返回None

        Raises:
            FileNotFoundError: 当本地文件不存在时
        """
        # 1. 验证本地文件
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"本地文件 {local_file_path} 不存在")

        # 2. 获取文件大小
        file_size = os.path.getsize(local_file_path)
        file_size_mb = file_size / (1024 * 1024)

        print(f"文件大小: {file_size_mb:.2f} MB")

        # 3. 根据文件大小选择上传方式
        if file_size >= large_file_threshold:
            print(f"检测到大文件，使用分块上传方式...")
            return self.upload_test_log(
                project, machine_ip, test_plan_id,
                local_file_path, custom_date, chunk_size
            )
        else:
            print(f"检测到小文件，使用普通上传方式...")
            return self.upload_test_log(
                project, machine_ip, test_plan_id,
                local_file_path, custom_date
            )

    def list_log_files(self, project: str = None, machine_ip: str = None,
                      date_str: str = None, test_plan_id: str = None) -> list:
        """
        列出指定路径下的文件

        Args:
            project: 项目名称过滤
            machine_ip: 机器IP过滤
            date_str: 日期过滤 (YYYY-MM-DD)
            test_plan_id: 测试计划ID过滤

        Returns:
            list: 文件信息列表
        """
        prefix_parts = []
        if project:
            prefix_parts.append(project)
        if machine_ip:
            prefix_parts.append(machine_ip)
        if date_str:
            prefix_parts.append(date_str)
        if test_plan_id:
            prefix_parts.append(test_plan_id)

        prefix = "/".join(prefix_parts)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )

            file_list = []
            for obj in objects:
                file_info = {
                    "file_name": obj.object_name.split('/')[-1],
                    "full_path": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified
                }
                file_list.append(file_info)

            return file_list

        except S3Error as e:
            print(f"列出文件失败: {e}")
            return []

    def delete_log_file(self, project: str, machine_ip: str, test_plan_id: str,
                       file_name: str, date_str: str = None) -> bool:
        """
        删除指定日志文件

        Args:
            project: 项目名称
            machine_ip: 测试机器IP
            test_plan_id: 测试计划ID
            file_name: 文件名
            date_str: 日期 (YYYY-MM-DD, 默认为当前日期)

        Returns:
            bool: 删除成功返回True
        """
        if not date_str:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        object_name = f"{project}/{machine_ip}/{date_str}/{test_plan_id}/{file_name}"

        try:
            self.client.remove_object(self.bucket_name, object_name)
            print(f"成功删除: {object_name}")
            return True

        except S3Error as e:
            print(f"删除文件失败: {e}")
            return False

    def get_presigned_url(self, project: str, machine_ip: str, test_plan_id: str,
                         file_name: str, date_str: str = None,
                         expires_seconds: int = 604800) -> Optional[str]:
        """
        生成文件的预签名下载链接

        Args:
            project: 项目名称
            machine_ip: 测试机器IP
            test_plan_id: 测试计划ID
            file_name: 文件名
            date_str: 日期 (YYYY-MM-DD, 默认为当前日期)
            expires_seconds: 链接有效期 (默认7天)

        Returns:
            str: 预签名URL，失败时返回None
        """
        if not date_str:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        object_name = f"{project}/{machine_ip}/{date_str}/{test_plan_id}/{file_name}"

        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=datetime.timedelta(seconds=expires_seconds)
            )
            return url

        except S3Error as e:
            print(f"生成下载链接失败: {e}")
            return None

