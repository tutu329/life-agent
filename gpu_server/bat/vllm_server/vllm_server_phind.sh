export CUDA_VISIBLE_DEVICES=0,1,3,2
python -m vllm.entrypoints.openai.api_server --model=/home/tutu/models/Phind-CodeLlama-34B-v2-GPTQ --tensor-parallel-size=4 --trust-remote-code --dtype=float16 --chat-template=/home/tutu/models/template_alpaca.jinja --host=0.0.0.0 --port=8002
