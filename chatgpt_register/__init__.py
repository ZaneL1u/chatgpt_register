"""ChatGPT 批量自动注册工具"""

from chatgpt_register.config.model import RegisterConfig
from chatgpt_register.core.batch import run_batch

__version__ = "0.1.0"

__all__ = ["RegisterConfig", "run_batch", "__version__"]
