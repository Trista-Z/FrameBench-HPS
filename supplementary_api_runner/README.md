# FrameBench 补实验 API 执行说明

你需要负责 **调用 3 个模型的 API 并把原始结果返回给作者**。

## 你需要准备

- Python 3.11 或以上版本
- 以下 3 个模型可用的 API Key：
  - GPT-4o mini
  - Claude Sonnet 4.6
  - Gemini 2.5 Pro

请不要修改模型、prompt、样本、split、rewrite 或任何实验参数。

## 第一次运行

解压文件夹后，在终端进入该目录：

```bash
cd supplementary_api_runner
```

检查依赖（本项目仅使用 Python 标准库，无需安装第三方包）：

```bash
python3 -m pip install -r requirements.txt
```

然后直接运行：

```bash
python3 launch.py
```

Windows 如果 `python3` 不可用，可以使用：

```bash
py -3 launch.py
```

程序会依次要求输入 3 个 API Key。输入时不会显示在屏幕上，Key 只保存在当前进程中，不会写入文件。

之后无需手动操作，脚本会自动完成全部 API 实验。

## 运行规模

正式实验共约 **9,984 次模型调用**：

- Dev：768 次
- Test：9,216 次

运行时间和费用取决于各 API 的速度、限流和价格。

## 跑完以后

正常完成后，文件夹根目录会生成：

```text
RETURN_TO_AUTHOR_RESULTS.zip
```

请把这个 ZIP **原样发回给作者**。

## 如果中途断网或程序退出

确认程序已经停止后，直接重新运行：

```bash
python3 launch.py
```

然后重新输入 API Key 即可。已经成功保存的结果会继续保留，不需要从头重跑。

## 如果程序在 Dev 阶段主动停止

如果某个模型返回的无效结果比例超过预设阈值，程序会主动停止，并生成：

```text
RETURN_TO_AUTHOR/
```

此时请 **不要改模型、prompt 或代码，也不要自行重跑不同设置**。把这个文件夹以及终端最后的报错信息发回给作者即可。

## 文件说明

你不需要逐个运行这些脚本，只运行 `launch.py` 即可。

- `launch.py`：一键入口
- `api_only.py`：控制整个实验流程
- `prepare.py`：生成需要调用的实验任务
- `run.py`：实际发送 API 请求并保存结果
- `collect_results.py`：跑完后整理并打包原始结果
- `common.py`：公共工具函数

如果没有报错，最终只需要把 `RETURN_TO_AUTHOR_RESULTS.zip` 发回作者。