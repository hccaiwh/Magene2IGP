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

# 优先使用 i.igpsport.com（国内/国际均可访问，my.igpsport.com 在海外CI Connection refused）
# 两个域名的登录响应格式不同，login() 会自动兼容：
#   - my.igpsport.com → Set-Cookie 方式（redirect + loginTicket）
#   - i.igpsport.com  → JSON 方式（{"Code":200,"Data":...}）
IGP_HOST = "i.igpsport.com"
LOGIN_URL = f"https://{IGP_HOST}/Auth/Login"
ACTIVITY_URL = f"https://{IGP_HOST}/Activity/ActivityList"
UPLOAD_URL = f"https://{IGP_HOST}/Activity/UploadFit"


class IGPSPORT:
    """IGPSPORT平台API封装类（兼容 my / i 两个域名）"""

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
        登录IGPSPORT平台，自动兼容两种响应格式：
        - Cookie 方式（my.igpsport.com）：检查 Set-Cookie 中的 loginTicket
        - JSON 方式（i.igpsport.com）：解析 {"Code":200,"Data":...}
        """
        payload = {
            "username": self.username,
            "password": self.password,
        }

        try:
            resp = self.session.post(LOGIN_URL, data=payload, timeout=15)
            # 不调用 raise_for_status()，因为登录失败也返回 200 + JSON错误体
            logger.debug(f"登录响应状态码: {resp.status_code}")
            logger.debug(f"登录响应 Content-Type: {resp.headers.get('Content-Type','')}")
            logger.debug(f"登录响应体: {resp.text[:300]}")

            content_type = resp.headers.get("Content-Type", "")

            # ===== 情况1：JSON 响应（i.igpsport.com 风格）=====
            if "application/json" in content_type:
                try:
                    data = resp.json()
                except ValueError:
                    logger.error(f"❌ 登录响应不是合法JSON: {resp.text[:200]}")
                    return False

                code = data.get("Code") or data.get("code")
                if code == 200:
                    # 成功：从 Data 字段提取 token
                    token_data = data.get("Data") or data.get("data")
                    if isinstance(token_data, str) and token_data:
                        self.login_token = token_data
                    elif isinstance(token_data, dict):
                        self.login_token = (
                            token_data.get("token")
                            or token_data.get("access_token")
                            or token_data.get("loginToken")
                        )
                    else:
                        logger.error(f"❌ 无法从响应 Data 中提取 token: {token_data}")
                        return False

                    self.session.headers.update({
                        "Authorization": f"Bearer {self.login_token}"
                    })
                    logger.info("✅ IGPSPORT 登录成功（JSON模式）")
                    return True
                else:
                    msg = data.get("Message") or data.get("message", "未知错误")
                    logger.error(f"❌ IGPSPORT 登录失败: {msg} (Code: {code})")
                    return False

            # ===== 情况2：Cookie 响应（my.igpsport.com 风格）=====
            else:
                # 拼接所有 Set-Cookie 头（requests 可能返回逗号分隔或列表）
                if hasattr(resp.headers, "getlist"):
                    all_cookies = ", ".join(resp.headers.getlist("Set-Cookie"))
                else:
                    all_cookies = resp.headers.get("Set-Cookie", "")

                logger.debug(f"Set-Cookie 内容: {all_cookies[:300]}")

                if "loginTicket" not in all_cookies:
                    logger.error("❌ IGPSPORT 登录失败：未获取到 loginTicket（账号/密码可能有误）")
                    logger.debug(f"完整响应头: {dict(resp.headers)}")
                    return False

                match = re.search(r"loginToken=(.*?);", all_cookies)
                if not match or not match.group(1):
                    logger.error("❌ IGPSPORT 登录失败：未解析到 loginToken")
                    return False

                self.login_token = match.group(1)
                self.session.headers.update({
                    "Authorization": f"Bearer {self.login_token}"
                })
                logger.info("✅ IGPSPORT 登录成功（Cookie模式）")
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
