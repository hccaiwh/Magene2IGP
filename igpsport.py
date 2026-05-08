"""
IGPSPORT平台 API 封装
提供登录、上传FIT文件等功能
参考：https://github.com/kvnZero/IGPSPORT2Xingzhe
"""
import requests
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 国内版 IGPSPORT 域名
# 国际版用 i.igpsport.com（本项目暂不支持）
IGP_HOST = "my.igpsport.com"
LOGIN_URL = f"https://{IGP_HOST}/Auth/Login"
ACTIVITY_URL = f"https://{IGP_HOST}/Activity/ActivityList"
UPLOAD_URL = "https://www.imxingzhe.com/api/v1/fit/upload/"  # 参考项目中的行者上传接口


class IGPSPORT:
    """IGPSPORT平台API封装类（适配新版接口）"""

    def __init__(self, username: str, password: str):
        """
        初始化IGPSPORT API客户端

        Args:
            username: 用户名/邮箱
            password: 密码（明文，登录时直接传递）
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.login_token: Optional[str] = None

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

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Encoding": "gzip, deflate",
        })

    def login(self) -> bool:
        """
        登录IGPSPORT平台（新版接口）
        参考：IGPSPORT2Xingzhe 项目
        """
        payload = {
            "username": self.username,
            "password": self.password,
        }

        try:
            resp = self.session.post(LOGIN_URL, data=payload, timeout=15)
            resp.raise_for_status()

            # 从 Set-Cookie 中提取 loginToken
            set_cookie = resp.headers.get("Set-Cookie", "")
            if "loginTicket" not in set_cookie:
                logger.error("❌ IGPSPORT 登录失败：未获取到 loginTicket")
                return False

            match = re.search(r"loginToken=(.*?);", set_cookie)
            if not match:
                logger.error("❌ IGPSPORT 登录失败：未解析到 loginToken")
                return False

            self.login_token = match.group(1)
            self.session.headers.update({
                "Authorization": f"Bearer {self.login_token}"
            })

            logger.info("✅ IGPSPORT 登录成功")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ IGPSPORT 登录失败: {e}")
            return False

    def get_activity_list(self) -> list:
        """
        获取活动列表

        Returns:
            活动列表（字典列表）
        """
        if not self.login_token:
            logger.warning("未登录，无法获取活动列表")
            return []

        try:
            resp = self.session.get(ACTIVITY_URL, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            activities = result.get("item", [])
            logger.info(f"ℹ️ 获取到 {len(activities)} 个IGPSPORT活动")
            return activities
        except requests.exceptions.RequestException as e:
            logger.error(f"获取IGPSPORT活动列表失败: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"解析IGPSPORT活动列表失败: {e}")
            return []

    def upload_fit_file(self, fit_path: str, activity_name: str = "") -> bool:
        """
        上传FIT文件到IGPSPORT（通过官方上传接口）

        Args:
            fit_path: FIT文件路径
            activity_name: 活动名称（可选）

        Returns:
            上传是否成功
        """
        if not self.login_token:
            logger.warning("未登录，无法上传文件")
            return False

        upload_url = f"https://{IGP_HOST}/Activity/UploadFit"
        # 备用接口（参考项目中的方式）
        # upload_url = "https://www.imxingzhe.com/api/v1/fit/upload/"

        try:
            with open(fit_path, "rb") as f:
                files = {"file": (fit_path.split("/")[-1], f, "application/octet-stream")}
                resp = self.session.post(upload_url, files=files, timeout=60)
                resp.raise_for_status()

            logger.info(f"✅ 上传FIT文件到IGPSPORT成功: {fit_path.split('/')[-1]}")
            return True

        except FileNotFoundError:
            logger.error(f"❌ 文件不存在: {fit_path}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 上传FIT文件失败: {e}")
            return False
        except IOError as e:
            logger.error(f"❌ 读取文件失败: {e}")
            return False
