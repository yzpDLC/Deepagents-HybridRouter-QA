from config.settings import prompts_conf
from utils.path_tool import get_abs_path
from utils.logger_handler import logger


def load_prompt(prompts_name):
    try:
        prompt_path = get_abs_path(prompts_conf[prompts_name])
    except KeyError as e:
        logger.error(f"请检查配置文件，缺少{prompts_name}字段")
        raise e

    try:
        return open(prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"请检查配置文件，指定的{prompts_name}字段路径错误：{prompt_path}")
        raise e
