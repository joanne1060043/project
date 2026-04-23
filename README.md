# Project
### 一、環境安裝方式 Download
#### 1. 依賴項
|       依賴項      |      版本      |
|   ---             |    ---        |
|ultralytics        |latest         |
|torch              |cuda v12.6     |
|torchvision        |cuda v12.6     |

> 下載方式可以用下列指令 (已使用沙盒套件 .venv，可跳過此步驟)
```bat
pip install -r req.txt
```

#### 2. 進入 python 沙盒
> 使用此指令進入虛擬 python 環境
```bat
.venv\Scripts\activate
```

### 二、訓練
> 我們使用 YOLO v12.

中斷訓練：ctrl+c
恢復訓練：`python train.py --resume --data=data.yaml --epochs=100 --device=0`

train/box_loss: 訓練過程中的框架損失（通常是回歸損失，衡量預測框與真實框之間的差距）。
train/cls_loss: 訓練過程中的分類損失（衡量每個物體分類的準確性）。
train/dfl_loss: 訓練過程中的 DFL 損失（在某些模型中是針對不同的預測特徵進行的損失度量，可能是分佈式回歸的損失）。
metrics/precision(B): 訓練過程中模型的精度（衡量模型預測的正確性，越高表示預測準確率越好）。
metrics/recall(B): 訓練過程中模型的召回率（衡量模型檢測到的所有正確預測的比例）。
metrics/mAP50(B): 訓練過程中模型在 AP50（IoU 大於 50%）下的平均精度（mAP，越高表示模型的總體精度更好）。
metrics/mAP50-95(B): 訓練過程中模型在 AP50-95（IoU 範圍從 50% 到 95%）下的平均精度，這是衡量檢測器精度的更嚴格指標。
val/box_loss: 驗證過程中的框架損失（衡量預測框與真實框之間的差距）。
val/cls_loss: 驗證過程中的分類損失。
val/dfl_loss: 驗證過程中的 DFL 損失。
lr/pg0: 訓練過程中的學習率（第一個參數組），通常用於優化器的第一階段。
lr/pg1: 訓練過程中的學習率（第二個參數組），通常用於優化器的第二階段。
lr/pg2: 訓練過程中的學習率（第三個參數組），通常用於優化器的第三階段。