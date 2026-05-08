"""
迈金(Onelap/Magene)平台 API 封装
提供登录、获取活动列表、下载FIT文件等功能
"""
import requests
import logging
from typing import Optional, List, Dict, Any
from utils import safe_sleep

logger = logging.getLogger(__name__)

BASE_API = "https://otm.onelap.cn"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"

class OnelapMagene:
    """迈金平台API封装类"""
    
    def __init__(self, username: str, password: str):
        """
        初始化迈金API客户端
        
        Args:
            username: 用户名/手机号
            password: 密码
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        
        # 添加重试机制，自动处理临时网络错误和5xx错误
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=2, # 最多重试2次
            backoff_factor=1, # 重试间隔：1s、2s
            status_forcelist=[429, 500, 502, 503, 504] # 这些状态码自动重试
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({"User-Agent": UA})
        self.token: Optional[str] = None
    
    def login(self) -> bool:
        """
        登录迈金平台
        
        Returns:
            登录是否成功
        """
        url = f"{BASE_API}/v1/auth/login"
        payload = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
            "client_id": "onelap_app"
        }
        
        try:
            resp = self.session.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            self.token = data.get("access_token")
            if not self.token:
                logger.error("登录失败：未获取到token")
                return False
            
            logger.info("✅ 迈金登录成功")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"迈金登录失败: {e}")
            return False
        except (KeyError, ValueError) as e:
            logger.error(f"解析登录响应失败: {e}")
            return False
    
    def get_activity_list(self, page: int = 1, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取活动列表
        
        Args:
            page: 页码
            limit: 每页数量
        
        Returns:
            活动列表
        """
        if not self.token:
            logger.warning("未登录，无法获取活动列表")
            return []
        url = f"{BASE_API}/v1/activities"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"page": page, "limit": limit}
        
        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            activities = data.get("data", {}).get("list", [])
            logger.info(f"ℹ️ 获取到 {len(activities)} 个活动")
            return activities
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取活动列表失败: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"解析活动列表失败: {e}")
            return []
    
    def download_fit(self, activity_id: str, save_dir: str) -> Optional[str]:
        """
        下载FIT文件
        
        Args:
            activity_id: 活动ID
            save_dir: 保存目录
        
        Returns:
            保存路径，失败返回None
        """
        if not self.token:
            logger.warning("未登录，无法下载文件")
            return None
        url = f"{BASE_API}/v1/activities/{activity_id}/download_fit"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            resp = self.session.get(url, headers=headers, stream=True, timeout=30)
            resp.raise_for_status()
            
            save_path = f"{save_dir}/{activity_id}.fit"
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"✅ 下载FIT文件成功: {activity_id}.fit")
            return save_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"下载FIT文件失败 {activity_id}: {e}")
            return None
        except IOError as e:
            logger.error(f"保存FIT文件失败 {activity_id}: {e}")
            return None
