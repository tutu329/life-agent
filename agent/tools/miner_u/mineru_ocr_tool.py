# MinerU2.5（1.2B多模态模型，支持turing gpu)，指标超越dots.ocr、monkey-ocr
# 1、安装
# conda create -n mineru python=3.12
# conda activate mineru
# uv pip install mineru[all]
#
# 2、使用ui(目前能启动，但ui解析pdf开始后，但用vllm-engine时engine会报错)
# https://opendatalab.github.io/MinerU/usage/quick_usage/#quick-usage-via-command-line
# 如使用含vllm的ui（启动后，会下载模型，由于开VPN会造成启动测试失败，因此必须关VPN）：
# export MINERU_MODEL_SOURCE=modelscope
# mineru-gradio --server-name 0.0.0.0 --server-port 7860
# mineru-gradio --server-name 0.0.0.0 --server-port 7860 --enable-vllm-engine true
# 然后浏览器：http://powerai.cc:7860
#
# 3、使用cli(解析当前目录下所有文件如pdf)
# export MINERU_MODEL_SOURCE=modelscope
# mineru -p ./ -o ./

