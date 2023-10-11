d:
cd d:\Qwen
cmd /K "conda activate qwen && set CUDA_VISIBLE_DEVICES=0 && start python openai_api.py && cd d:\server\life-agent && python qwen_webui.py"

