# MinerU2.5（1.2B多模态模型，支持turing gpu)，指标超越dots.ocr、monkey-ocr
# 1、安装
# conda create -n mineru python=3.12
# conda activate mineru
# uv pip install mineru[all]
#
# 2、使用ui(注意要用transformer不要用pipe。)
# https://opendatalab.github.io/MinerU/usage/quick_usage/#quick-usage-via-command-line
# 如使用含vllm的ui（启动后，会下载模型，由于开VPN会造成启动测试失败，因此必须关VPN）：
# export MINERU_MODEL_SOURCE=modelscope
# mineru-gradio --server-name 0.0.0.0 --server-port 7860
# mineru-gradio --server-name 0.0.0.0 --server-port 7860 --enable-vllm-engine true
# 然后浏览器：http://powerai.cc:7860
#
# 3、使用cli(解析当前目录下所有文件如pdf)(--backend [pipeline|vlm-transformers|vlm-vllm-engine|vlm-http-client])
# export MINERU_MODEL_SOURCE=modelscope
# mineru -p ./ -o ./ --backend vlm-transformers
#
# 4、目前vllm-10.2下，2080ti用vllm-engine时engine会报错。

