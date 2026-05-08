"""
迈金(Onelap/Magene)平台 API 封装
提供登录、获取活动列表、下载FIT文件等功能
"""
import requests
import logging
import hashlib
import os
from typing import Optional, List, Dict, Any
from utils import safe_sleep

logger = logging.getLogger(__name__)

# 参考：https://gitcode.com/u012153104/OnelapSyncIGPSport
LOGIN_URL = "https://www.onelap.cn/api/login"
ACTIVITY_URL = "http://u.onelap.cn/analysis/list"
DOWNLOAD_HOST = "http://u.onelap.cn"

class OnelapMagene:
    """迈金平台API封装类（适配新版接口）"""

    def __init__(self, username: str, password: str):
        """
        初始化迈金API客户端

        Args:
            username: 用户名/手机号
            password: 密码（明文，内部会做MD5加密）
        """
        self.username = username
        self.password = password
        self.session = requests.Session()

        # 添加重试机制
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.token_data: Optional[Dict[str, Any]] = None

    def login(self) -> bool:
        """
        登录迈金平台（新版接口）
        API文档参考：OnelapSyncIGPSport 项目
        """
        hashed_pwd = hashlib.md5(self.password.encode()).hexdigest()
        payload = {
            "account": self.username,
            "password": hashed_pwd
        }

        try:
            resp = self.session.post(LOGIN_URL, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 200:
                logger.error(f"登录失败: {data.get('error', '未知错误')}")
                return False

            self.token_data = data["data"][0]
            uid = self.token_data["userinfo"]["uid"]
            nickname = self.token_data["userinfo"]["nickname"]
            logger.info(f"✅ 迈金登录成功 | 用户: {nickname} (ID: {uid})")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"迈金登录失败: {e}")
            return False
        except (KeyError, ValueError) as e:
            logger.error(f"解析登录响应失败: {e}")
            return False

    def get_activity_list(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取活动列表（使用Cookie认证）

        Args:
            limit: 获取数量（按时间倒序取最新）
        """
        if not self.token_data:
            logger.warning("未登录，无法获取活动列表")
            return []

        uid = self.token_data["userinfo"]["uid"]
        token = self.token_data["token"]
        refresh_token = self.token_data["refresh_token"]

        headers = {
            "Cookie": f"ouid={uid}; XSRF-TOKEN={token}; OTOKEN={refresh_token}"
        }

        try:
            resp = self.session.get(ACTIVITY_URL, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            activities = data.get("data", [])
            # 按创建时间倒序，取最新的 limit 条
            activities_sorted = sorted(
                activities,
                key=lambda x: x.get("created_at", 0),
                reverse=True
            )
            result = activities_sorted[:limit]
            logger.info(f"ℹ️ 获取到 {len(result)} 个活动")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"获取活动列表失败: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"解析活动列表失败: {e}")
            return []

    def download_fit(self, activity: Dict[str, Any], save_dir: str) -> Optional[str]:
        """
        下载FIT文件

        Args:
            activity: 活动数据字典
            save_dir: 保存目录

        Returns:
            保存路径，失败返回None
        """
        if not self.token_data:
            logger.warning("未登录，无法下载文件")
            return None

        uid = self.token_data["userinfo"]["uid"]
        token = self.token_data["token"]
        refresh_token = self.token_data["refresh_token"]

        headers = {
            "Cookie": f"ouid={uid}; XSRF-TOKEN={token}; OTOKEN={refresh_token}"
        }

        # 获取下载链接和文件名
        if activity.get("fitUrl"):
            filename = f"{activity['fitUrl']}.fit"
            download_url = activity.get("durl", "")
        else:
            filename = f"{activity['fileKey']}"
            download_url = activity.get("durl", "")

        if not download_url:
            logger.error(f"活动 {filename} 无下载链接")
            return None

        # 补全相对路径
        if not download_url.startswith("http"):
            download_url = f"{DOWNLOAD_HOST}{download_url}"

        save_path = f"{save_dir}/{filename}"

        try:
            resp = self.session.get(download_url, headers=headers, stream=True, timeout=30)
            resp.raise_for_status()

            os.makedirs(save_dir, exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"✅ 下载成功: {filename}")
            return save_path

        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败 {filename}: {e}")
            return None
        except IOError as e:
            logger.error(f"保存文件失败 {filename}: {e}")
            return None
