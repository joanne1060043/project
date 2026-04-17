from ultralytics import YOLO

# 載入訓練好的模型
model = YOLO('best.pt')

# 設定圖片路徑，這裡假設您有一張圖片 'image.jpg'
results = model(
    'b.jpg',
    conf=0.55,   # 信心閥值 (0~1)
    iou=0.5     # IoU 閥值 (0~1)
)
result = results[0]
# 顯示結果
result.show()  # 顯示圖片上的預測結果

# 若需要保存預測結果，可以使用：
result.save()  # 將結果保存到指定文件夾