from pathlib import Path
from preprocess.chunking import chunk_by_corporate_structure

# 统一使用Path类    解析为项目所在的绝对路径（项目随意移植不会出现路径问题）
current_dir = Path(__file__).resolve().parent.parent
input_dir = current_dir / "graphrag" / "input"
output_dir = current_dir / "preprocess" / "chunking_output"

# 创建输出目录  如果父目录不存在自动创建  如果父目录已存在不报错
output_dir.mkdir(parents=True, exist_ok=True)

# 遍历输入目录
for file_path in input_dir.iterdir():
    if file_path.suffix != ".txt":  # 只处理 .txt 文件
        continue

    # 读取文件（自动关闭）
    text = file_path.read_text(encoding="utf-8")

    # 分块
    chunks = chunk_by_corporate_structure(text, doc_id=file_path.stem)  # 使用 stem 去掉扩展名

    # 写入输出
    for i, chunk in enumerate(chunks):
        out_name = f"{file_path.stem}_chunk{i}.txt"  # 使用 stem 更简洁
        out_path = output_dir / out_name
        out_path.write_text(chunk["content"], encoding="utf-8")

print(f"分块完成，输出至 {output_dir}")