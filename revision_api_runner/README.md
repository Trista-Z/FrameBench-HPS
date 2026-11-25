# FrameBench-HPS revision API runner

仅用于 API 执行；无需统计分析、不包含历史模型回答或人工编码映射。Python 3.10+，仅使用标准库，无需 pip install。请不要自行调整 prompt、模型或重复次数。API key 运行时无回显输入，或预先配置环境变量；不要写进代码或提交 Git。

## 1. 无费用检查

```bash
python3 launch.py e2_all --dry-run
python3 launch.py e3_all --dry-run
python3 launch.py e1 --dry-run
```

## 2. 开始 E2 和 E3（同期对照版）

```bash
python3 launch.py e2_all --dev-only
python3 launch.py e2_all
python3 launch.py e3_all --dev-only
python3 launch.py e3_all
```

按提示提供 OPENAI_API_KEY、ANTHROPIC_API_KEY、GEMINI_API_KEY 和 E2 所需 QWEN_API_KEY、QWEN_BASE_URL（OpenAI-compatible /v1 endpoint）。检查 models.json 的模型 ID、API URL 与推理参数；默认 Qwen 地址是占位符。GPT-5 不传 temperature（API 兼容性），不代表已验证 temperature=0。模型不可用或参数报错时联系作者，不能自行替换。dev 无效率任一模型超过 10% 会停止，先将结果交给作者。正式运行会复用已保存 dev 数据。

## 3. E1（须由作者提供已审核文件）

两位研究人员确认 40 个 scenario-specific outcomes 及所有 prompt variants 后，将两份已填写的 H1 `E1_outcome_review.csv` 私下保存为 `review/coder1.csv` 和 `review/coder2.csv`。

```bash
python3 launch.py e1 --review review/coder1.csv review/coder2.csv --dev-only
python3 launch.py e1 --review review/coder1.csv review/coder2.csv
```

程序核对两份 CSV 的独立 reviewer IDs、完整场景、target、context 和 accept 决策。不得伪造批准。若任一 target 需修改，先由作者重新生成审核材料并重新审核。审核 CSV 不提交 Git。

| 实验 | Dev calls | Test calls |
| --- | ---: | ---: |
| E1 | 768 | 9,216 |
| E2_all | 448 | 5,376 |
| E3_all | 576 | 6,912 |
| Total | 1,792 | 21,504 |

最低预算备选：经作者同意用 `e2` (256 dev/3,072 test) 和 `e3_minimal` (288 dev/3,456 test) 替换 all 版本。同一 cohort 不得同时运行两套。调用量不含 retries 和后续独立 judge；judge 与人工验证由作者另行安排。

## 4. 结果返回

每次运行结束会自动生成/更新 `REVISION_RESULTS.zip`，包含同一 cohort 的原始记录、manifests、实际模型配置及状态。私下把 ZIP 原样发回作者，不上传公开仓库。即使中断，也可运行 `python3 launch.py --export-only` 导出已保存记录。正常断点续跑用相同命令；模型配置或输入发生变化请先联系作者，不能混用 cohort。若崩溃留下 RUNNING.lock，确认进程已经退出后才可删除对应锁。

`--mock` 可在不调用 API 的情况下测试完整执行流程，输出 MOCK_RESULTS.zip，不能当作实验数据。`--retry-errors` 仅在作者批准时重试 transport errors。所有密钥仅在本地环境，ZIP 不包含密钥或人工映射。
