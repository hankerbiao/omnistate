"""资源锁管理器

提供基于 MongoDB 的分布式锁机制，用于保护 DUT 资源在并发测试时的互斥访问。
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import ASCENDING, IndexModel
from app.shared.core.logger import log as logger


class ResourceLockDoc(Document):
    """资源锁文档模型"""
    resource_id: str = Field(..., description="资源标识（如 DUT asset_id）")
    lock_type: str = Field(..., description="锁类型（如 'dut_test'）")
    owner: str = Field(..., description="锁持有者标识（如任务ID或会话ID）")
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="锁过期时间")

    class Settings:
        name = "resource_locks"
        indexes = [
            IndexModel([("resource_id", ASCENDING), ("lock_type", ASCENDING)], unique=True),
            IndexModel("expires_at"),
            IndexModel("owner"),
        ]


class ResourceLockManager:
    """资源锁管理器

    提供分布式锁的获取、释放和状态查询功能。
    """

    def __init__(self, default_ttl_seconds: int = 300):
        """初始化资源锁管理器

        Args:
            default_ttl_seconds: 默认锁超时时间（秒）
        """
        self.default_ttl_seconds = default_ttl_seconds
        logger.info(f"ResourceLockManager initialized with TTL={default_ttl_seconds}s")

    async def acquire_lock(
        self,
        resource_id: str,
        lock_type: str,
        owner: str,
        ttl_seconds: Optional[int] = None,
        wait_timeout: float = 0,
        retry_interval: float = 0.5
    ) -> bool:
        """获取资源锁

        Args:
            resource_id: 资源标识（如 DUT asset_id）
            lock_type: 锁类型（如 'dut_test'）
            owner: 锁持有者标识（如任务ID或会话ID）
            ttl_seconds: 锁超时时间（秒），默认使用管理器默认值
            wait_timeout: 等待获取锁的超时时间（秒），0 表示不等待
            retry_interval: 重试间隔（秒）

        Returns:
            是否成功获取锁
        """
        ttl = ttl_seconds or self.default_ttl_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        start_time = datetime.now(timezone.utc)

        while True:
            try:
                lock = ResourceLockDoc(
                    resource_id=resource_id,
                    lock_type=lock_type,
                    owner=owner,
                    expires_at=expires_at
                )
                await lock.insert()
                logger.info(f"Lock acquired: resource={resource_id}, type={lock_type}, owner={owner}, ttl={ttl}s")
                return True

            except Exception as e:
                if "duplicate key" in str(e).lower():
                    logger.debug(f"Resource already locked: resource={resource_id}, type={lock_type}")
                    
                    if wait_timeout <= 0:
                        return False

                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                    if elapsed >= wait_timeout:
                        logger.warning(f"Failed to acquire lock after {wait_timeout}s: resource={resource_id}")
                        return False

                    await asyncio.sleep(retry_interval)
                else:
                    logger.exception(f"Unexpected error acquiring lock: {str(e)}")
                    return False

    async def release_lock(
        self,
        resource_id: str,
        lock_type: str,
        owner: str
    ) -> bool:
        """释放资源锁

        Args:
            resource_id: 资源标识
            lock_type: 锁类型
            owner: 锁持有者标识

        Returns:
            是否成功释放锁
        """
        try:
            lock = await ResourceLockDoc.find_one(
                ResourceLockDoc.resource_id == resource_id,
                ResourceLockDoc.lock_type == lock_type,
                ResourceLockDoc.owner == owner
            )
            
            if lock:
                await lock.delete()
                logger.info(f"Lock released: resource={resource_id}, type={lock_type}, owner={owner}")
                return True
            else:
                logger.warning(f"Lock not found for release: resource={resource_id}, type={lock_type}, owner={owner}")
                return False

        except Exception as e:
            logger.exception(f"Error releasing lock: {str(e)}")
            return False

    async def is_locked(
        self,
        resource_id: str,
        lock_type: str
    ) -> bool:
        """检查资源是否被锁定

        Args:
            resource_id: 资源标识
            lock_type: 锁类型

        Returns:
            资源是否被锁定
        """
        try:
            lock = await ResourceLockDoc.find_one(
                ResourceLockDoc.resource_id == resource_id,
                ResourceLockDoc.lock_type == lock_type,
                ResourceLockDoc.expires_at > datetime.now(timezone.utc)
            )
            return lock is not None
        except Exception as e:
            logger.exception(f"Error checking lock status: {str(e)}")
            return False

    async def get_lock_info(
        self,
        resource_id: str,
        lock_type: str
    ) -> Optional[dict]:
        """获取锁信息

        Args:
            resource_id: 资源标识
            lock_type: 锁类型

        Returns:
            锁信息字典，如果未锁定则返回 None
        """
        try:
            lock = await ResourceLockDoc.find_one(
                ResourceLockDoc.resource_id == resource_id,
                ResourceLockDoc.lock_type == lock_type,
                ResourceLockDoc.expires_at > datetime.now(timezone.utc)
            )
            
            if lock:
                return {
                    "resource_id": lock.resource_id,
                    "lock_type": lock.lock_type,
                    "owner": lock.owner,
                    "acquired_at": lock.acquired_at.isoformat(),
                    "expires_at": lock.expires_at.isoformat(),
                    "ttl_seconds": (lock.expires_at - datetime.now(timezone.utc)).total_seconds()
                }
            return None

        except Exception as e:
            logger.exception(f"Error getting lock info: {str(e)}")
            return None

    async def cleanup_expired_locks(self) -> int:
        """清理过期的锁

        Returns:
            清理的锁数量
        """
        try:
            result = await ResourceLockDoc.find(
                ResourceLockDoc.expires_at <= datetime.now(timezone.utc)
            ).delete()
            
            count = result.deleted_count
            if count > 0:
                logger.info(f"Cleaned up {count} expired locks")
            return count

        except Exception as e:
            logger.exception(f"Error cleaning up expired locks: {str(e)}")
            return 0

    async def force_release_lock(
        self,
        resource_id: str,
        lock_type: str
    ) -> bool:
        """强制释放锁（忽略 owner）

        Args:
            resource_id: 资源标识
            lock_type: 锁类型

        Returns:
            是否成功释放锁
        """
        try:
            result = await ResourceLockDoc.find(
                ResourceLockDoc.resource_id == resource_id,
                ResourceLockDoc.lock_type == lock_type
            ).delete()
            
            count = result.deleted_count
            if count > 0:
                logger.warning(f"Force released lock: resource={resource_id}, type={lock_type}")
            return count > 0

        except Exception as e:
            logger.exception(f"Error force releasing lock: {str(e)}")
            return False


class ResourceLockContext:
    """资源锁上下文管理器

    使用 async with 语法自动管理锁的获取和释放。
    """

    def __init__(
        self,
        manager: ResourceLockManager,
        resource_id: str,
        lock_type: str,
        owner: str,
        ttl_seconds: Optional[int] = None,
        wait_timeout: float = 0
    ):
        """初始化锁上下文管理器

        Args:
            manager: 资源锁管理器
            resource_id: 资源标识
            lock_type: 锁类型
            owner: 锁持有者标识
            ttl_seconds: 锁超时时间
            wait_timeout: 等待获取锁的超时时间
        """
        self.manager = manager
        self.resource_id = resource_id
        self.lock_type = lock_type
        self.owner = owner
        self.ttl_seconds = ttl_seconds
        self.wait_timeout = wait_timeout
        self._locked = False

    async def __aenter__(self):
        """进入上下文，获取锁"""
        acquired = await self.manager.acquire_lock(
            resource_id=self.resource_id,
            lock_type=self.lock_type,
            owner=self.owner,
            ttl_seconds=self.ttl_seconds,
            wait_timeout=self.wait_timeout
        )
        
        if not acquired:
            raise RuntimeError(f"Failed to acquire lock for resource={self.resource_id}")
        
        self._locked = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，释放锁"""
        if self._locked:
            await self.manager.release_lock(
                resource_id=self.resource_id,
                lock_type=self.lock_type,
                owner=self.owner
            )
            self._locked = False
        return False

    async def release(self):
        """手动释放锁"""
        if self._locked:
            await self.manager.release_lock(
                resource_id=self.resource_id,
                lock_type=self.lock_type,
                owner=self.owner
            )
            self._locked = False


# 全局资源锁管理器实例
_lock_manager: Optional[ResourceLockManager] = None


def get_lock_manager() -> ResourceLockManager:
    """获取全局资源锁管理器实例

    Returns:
        资源锁管理器实例
    """
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = ResourceLockManager()
    return _lock_manager
