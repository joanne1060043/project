from roboflow import Roboflow

# 初始化 Roboflow
rf = Roboflow(api_key="yqpOaFUOdnjm4NLwRSyp")
project = rf.workspace("-suqln").project(" ")

# 下載數據集到本地
# 它會自動幫您建立一個資料夾並放好 images 和 labels
dataset = project.version(1).download("yolov11")