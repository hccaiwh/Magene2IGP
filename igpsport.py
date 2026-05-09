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

# GitHub Actions 可正常访问 my.igpsport.com（参考 IGPSPORT2Xingzhe 项目验证）
# i.igpsport.com 也可用，但登录返回 JSON 格式，认证方式不同
IGP_HOST = "my.igpsport.com"
LOGIN_URL = f"https://{IGP_HOST}/Auth/Login"
ACTIVITY_URL = f"https://{IGP_HOST}/Activity/ActivityList"
UPLOAD_URL = f"https://{IGP_HOST}/Activity/UploadFit"


class IGPSPORT:
    """IGPSPORT平台API封装类"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.login_token: Optional[str] = None

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
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
            "Accept-Encoding": "gzip, deflate",
        })

    def login(self) -> bool:
        """
        登录IGPSPORT平台
        - 接口：POST https://my.igpsport.com/Auth/Login
        - 密码明文 Form POST
        - 从 Set-Cookie 提取 loginTicket（登录成功标志）和 loginToken（后续认证用）
        - 参考：https://github.com/kvnZero/IGPSPORT2Xingzhe
        """
        payload = {
            "username": self.username,
            "password": self.password,
        }

        try:
            resp = self.session.post(LOGIN_URL, data=payload, timeout=15)
            resp.raise_for_status()

            # 拼接所有 Set-Cookie（可能有多个）
            if hasattr(resp.headers, "getlist"):
                all_cookies = ", ".join(resp.headers.getlist("Set-Cookie"))
            else:
                all_cookies = resp.headers.get("Set-Cookie", "")

            # 检查 loginTicket（登录成功标志）
            if "loginTicket" not in all_cookies:
                logger.error(f"❌ IGPSPORT 登录失败：未获取到 loginTicket（账号/密码可能有误）")
                logger.debug(f"响应内容: {resp.text[:300]}")
                return False

            # 提取 loginToken
            match = re.search(r"loginToken=(.*?);", all_cookies)
            if not match or not match.group(1):
                logger.error("❌ IGPSPORT 登录失败：未解析到 loginToken")
                return False

            self.login_token = match.group(1)
            self.session.headers.update({
                "Authorization": f"Bearer {self.login_token}"
            })

            logger.info("✅ IGPSPORT 登录成功")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ IGPSPORT 登录请求失败: {e}")
            return False

    def get_activity_list(self) -> list:
        """获取活动列表"""
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
        """上传FIT文件到IGPSPORT"""
        if not self.login_token:
            logger.warning("未登录，无法上传文件")
            return False

        try:
            filename = fit_path.split("/")[-1].split("\\")[-1]
            with open(fit_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                resp = self.session.post(UPLOAD_URL, files=files, timeout=60)

            logger.debug(f"上传响应: {resp.status_code} - {resp.text[:200]}")

            if resp.status_code == 200:
                logger.info(f"✅ 上传FIT文件到IGPSPORT成功: {filename}")
                return True
            else:
                logger.error(f"❌ 上传FIT文件失败，状态码: {resp.status_code}，响应: {resp.text[:200]}")
                return False

        except FileNotFoundError:
            logger.error(f"❌ 文件不存在: {fit_path}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 上传FIT文件失败: {e}")
            return False
        except IOError as e:
            logger.error(f"❌ 读取文件失败: {e}")
            return False
