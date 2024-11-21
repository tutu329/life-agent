# 将tensorboard.sh和trainer_log_to_tesorboard.py复制到日志文件trainer_log.jsonl所在目录，如/home/tutu/LLaMA-Factory/saves/Qwen2.5-1.5B/full/cpt_all_2024-11-11-09-41-24
# 运行tensorboard.sh即可
rm -rf tensorboard_runs
python trainer_log_to_tensorboard.py
tensorboard --logdir tensorboard_runs --port 7861