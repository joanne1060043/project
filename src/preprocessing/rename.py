############################ 
# 重新命名並排序指定資料夾的圖片
# route: ./src/preprocessing/rename.py
# 

import os

folder_path = "assets/raw"  # 你的資料夾路徑

files = sorted(os.listdir(folder_path))  # 先排序

for i, filename in enumerate(files, start=1):
    # 取得副檔名
    ext = os.path.splitext(filename)[1]
    
    # 新檔名 (001.jpg 這種格式)
    new_name = f"{i:03d}{ext}"
    
    old_path = os.path.join(folder_path, filename)
    new_path = os.path.join(folder_path, new_name)
    
    os.rename(old_path, new_path)

print("重新命名完成！")