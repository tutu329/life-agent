import json
from torch.utils.tensorboard import SummaryWriter

# 打开 JSONL 文件
log_file = "trainer_log.jsonl"

print(f"开始转换'{log_file}'为TensorBoard日志文件...")

# 创建 TensorBoard 日志写入器
writer = SummaryWriter("tensorboard_runs/trainer_log")

# 遍历 JSONL 文件中的每一行
with open(log_file, "r") as f:
    for line in f:
        log = json.loads(line)  # 解析 JSON 数据
        current_steps = log.get("current_steps")
        loss = log.get("loss")
        lr = log.get("lr")
        epoch = log.get("epoch")
        percentage = log.get("percentage")
        elapsed_time = log.get("elapsed_time")
        remaining_time = log.get("remaining_time")

        # 写入标量数据到 TensorBoard
        writer.add_scalar("Loss/train", loss, current_steps)
        writer.add_scalar("Learning_Rate", lr, current_steps)
        writer.add_scalar("Epoch", epoch, current_steps)
        writer.add_scalar("Percentage_Complete", percentage, current_steps)

        # 可以在 TensorBoard 的文本标签中记录耗时信息（可选）
        writer.add_text("Elapsed_Time", elapsed_time, current_steps)
        writer.add_text("Remaining_Time", remaining_time, current_steps)

# 关闭写入器
writer.close()

print(f"'{log_file}'已成功转换为TensorBoard日志文件'tensorboard_runs/trainer_log'")