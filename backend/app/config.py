"""
应用配置 —— 所有环境相关配置集中管理
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# 数据库配置 (SQL Server, 使用 pyodbc)
# ============================================================
# 方式1: Windows 集成身份验证 (Trusted Connection)
#   "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=OJPlatform;Trusted_Connection=yes"
# 方式2: SQL Server 身份验证
#   "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=OJPlatform;UID=sa;PWD=your_password"

DATABASE_URL = os.getenv(
    "OJ_DATABASE_URL",
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=OJPlatform;Trusted_Connection=yes;TrustServerCertificate=yes"
)

# SQLAlchemy 需要 pyodbc 连接字符串前缀
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={DATABASE_URL}"

# ============================================================
# JWT 认证配置
# ============================================================
JWT_SECRET_KEY = os.getenv("OJ_JWT_SECRET", "change-me-to-a-random-secret-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24      # 24 小时
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 天

# ============================================================
# 文件存储路径
# ============================================================
DATA_DIR = Path(os.getenv("OJ_DATA_DIR", "D:/dev/data/QuickOJ"))
PROBLEMS_DATA_DIR = DATA_DIR / "problems"             # 已通过的测试数据: /data/problems/{problem_id}/
PROBLEMS_PENDING_DIR = DATA_DIR / "problems" / "pending"  # 待审核的测试数据: /data/problems/pending/{problem_id}/
IMAGES_DIR = DATA_DIR / "images" / "problems"         # /data/images/problems/{problem_id}/
AVATARS_DIR = DATA_DIR / "avatars"                    # /avatars/{user_id}.{ext}
TEMP_DIR = BASE_DIR / "temp"

# ============================================================
# 文件上传限制
# ============================================================
MAX_AVATAR_SIZE_MB = 5
ALLOWED_AVATAR_TYPES = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_IMAGE_TYPES = {"jpg", "jpeg", "png", "gif", "svg", "webp"}
ALLOWED_TEST_DATA_EXT = ".zip"

# ============================================================
# 评测配置
# ============================================================
JUDGE_POLL_INTERVAL_SECONDS = 2.0           # 评测调度器轮询间隔
JUDGE_SERVER_URL = os.getenv("JUDGE_SERVER_URL", "http://localhost:8001")  # 评测机服务地址
MAX_CODE_LENGTH = 65536             # 代码最大长度 (字符)

# ============================================================
# 分页默认值
# ============================================================
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
