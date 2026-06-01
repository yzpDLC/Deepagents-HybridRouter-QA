"""
为整个项目提供统一的绝对路径
"""
import os

def get_project_root_path() -> str:
    """
    获取项目根目录的绝对路径
    """
    current_file_path = os.path.abspath(__file__)
    current_file_dir = os.path.dirname(current_file_path)
    project_root_path = os.path.dirname(current_file_dir)
    return project_root_path


def get_abs_path(relative_path: str) -> str:
    """
    获取绝对路径
    """
    project_root_path = get_project_root_path()

    return os.path.join(project_root_path, relative_path)


