# YOLOv12 Project

## 一、環境安裝方式 (Environment Setup)

### 1. 依賴項 (Dependencies)

| 依賴項          | 版本        |
| --------------- | ----------- |
| ultralytics     | latest      |
| numpy           | latest      |
| tforch          | cuda v12.6  |
| torchvision     | cuda v12.6  |


### 2. 進入 Python 沙盒 (Activate Virtual Environment)

> 使用此指令進入虛擬 Python 環境

Windows
```bash
.venv\Scripts\activate
```

Linux
```sh
source .venv\bin\activate
```

### 3. 使用以下指令安裝所需依賴 (已使用沙盒套件 `.venv`，若已經存在可跳過此步驟)  
```bash
pip install -r req.txt
````

## 二、訓練 (Training)

> 使用 YOLOv12m 訓練模型。

### 訓練中斷與恢復 (Interrupt and Resume Training)

* **中斷訓練**：按 `ctrl+c`
* **恢復訓練**：

```bash
python train.py --resume --data=data.yaml --epochs=100 --device=0
```

### 訓練過程中的損失與指標 (Loss and Metrics During Training)

* **train/box_loss**: 訓練過程中的框架損失（衡量預測框與真實框之間的差距）
* **train/cls_loss**: 訓練過程中的分類損失（衡量每個物體分類的準確性）
* **train/dfl_loss**: 訓練過程中的 DFL 損失（針對不同的預測特徵進行的損失度量）
* **metrics/precision(B)**: 模型的精度（越高表示預測準確率越好）
* **metrics/recall(B)**: 模型的召回率（衡量模型檢測到的所有正確預測的比例）
* **metrics/mAP50(B)**: 模型在 AP50（IoU 大於 50%）下的平均精度（越高表示總體精度更好）
* **metrics/mAP50-95(B)**: 模型在 AP50-95（IoU 範圍從 50% 到 95%）下的平均精度（更嚴格的檢測指標）
* **val/box_loss**: 驗證過程中的框架損失
* **val/cls_loss**: 驗證過程中的分類損失
* **val/dfl_loss**: 驗證過程中的 DFL 損失
* **lr/pg0**: 訓練過程中的學習率（第一個參數組）
* **lr/pg1**: 訓練過程中的學習率（第二個參數組）
* **lr/pg2**: 訓練過程中的學習率（第三個參數組）

## 三、專案架構 (Project Structure)

以下是專案的目錄結構，提供各個檔案及資料夾的簡介：

```
PROJECT/
│
├── .pycache/                # 編譯後的 Python 文件
├── .venv/                   # Python 虛擬環境
├── .vscode/                 # Visual Studio Code 設定
│   ├── launch.json
│   └── settings.json
│
├── assets/                  # 資料夾儲存資源檔案 (如模型檔案、圖片等)
│   ├── clip/
│   └── id.json
│
├── dataset/                 # 訓練與測試資料
│   ├── test/
│   ├── train/
│   └── valid/
│
├── config/                  # 配置檔案
│   └── data.yaml
│
├── runs/                    # 訓練過程中生成的結果
│   └── detect/
│       └── drone_project/
│           ├── v11_experiment/
│           └── v12_experiment/
│
├── src/                     # 主要程式碼
│   ├── dataset/             # 資料處理模組
│   │   └── take_pictures.py
│   ├── preprocessing/       # 資料前處理
│   │   ├── rename.py
│   │   ├── test_rotate.py
│   │   └── yolo_dataset_split.py
│   ├── test/                # 測試模組
│   │   └── cv.py
│   └── train/               # 訓練模組
│       └── yolo12n_640dpi.py
│
└── tutorial/                # 教學資料
└── .gitignore               # Git 忽略檔案
└── README.md                # 這個檔案
```

### 目錄結構簡介：

1. **assets/**: 儲存模型文件、資源等，包含 `clip/` 與 `id.json`。
2. **dataset/**: 包含測試、訓練與驗證資料夾。
3. **config/**: 配置資料夾，包含資料集配置文件 `data.yaml`。
4. **runs/**: 儲存訓練結果與模型檔案。
5. **src/**: 主程式碼資料夾，包含資料處理、前處理與訓練的 Python 模組。
6. **tutorial/**: 學習與指導文件。
7. **.gitignore**: 用於 Git 避免跟蹤不必要的文件。
8. **README.md**: 本檔案，提供專案說明與設置指南。

---

這樣的結構幫助你清晰地組織專案文件，並保持良好的模組化與可維護性。
