"""
QuickOJ 后端启动入口
用法: python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "access": {
                    "format": '%(asctime)s %(levelname)s: %(message)s',
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "default": {"class": "logging.StreamHandler", "formatter": "default"},
                "access": {"class": "logging.StreamHandler", "formatter": "access"},
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO"},
                "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
            },
        },
    )
