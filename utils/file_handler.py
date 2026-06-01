import os
import hashlib
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from utils.logger_handler import logger


def get_file_md5_hex(filepath: str):
    if not os.path.exists(filepath):
        logger.error(f"File {filepath} does not exist.")
        return
    if not os.path.isfile(filepath):
        logger.error(f"{filepath} is not a file.")
        return

    md5 = hashlib.md5()

    chunk_size = 4096

    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                md5.update(chunk)

            return md5.hexdigest()

    except Exception as e:
        logger.error(f"Error occurred while calculating MD5: {e}")
        return None

def listdir_with_allowed_type(path: str, allowed_types: tuple[str]):
    files=[]
    if not os.path.isdir(path):
        logger.error(f"{path} is not a directory.")
        return allowed_types

    for f in os.listdir(path):
        if f.endswith(allowed_types):
            files.append(os.path.join(path, f))

    return tuple(files)


def pdf_loader(filepath: str, password=None) -> list[Document]:
    return PyPDFLoader(filepath, password).load()

def txt_loader(filepath: str) -> list[Document]:
    return TextLoader(filepath,encoding="utf-8").load()