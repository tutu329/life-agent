# 小红书的dots.ocr(实测表格中数据文本精度高于MinerU2.5)
# https://github.com/rednote-hilab/dots.ocr
# ---------------------RuntimeError: FlashAttention only supports Ampere GPUs or newer.---------------------

# 1、安装
# conda create -n dots_ocr python=3.12
# conda activate dots_ocr
# git clone https://github.com/rednote-hilab/dots.ocr.git
# cd dots.ocr
# pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128
# pip install -e .
# python tools/download_model.py --type modelscope
# 2、使用
# 1）普通：python demo/demo_hf.py
# 2）vllm：
# # You need to register model to vllm at first
# python3 tools/download_model.py
# export hf_model_path=./weights/DotsOCR  # Path to your downloaded model weights, Please use a directory name without periods (e.g., `DotsOCR` instead of `dots.ocr`) for the model save path. This is a temporary workaround pending our integration with Transformers.
# export PYTHONPATH=$(dirname "$hf_model_path"):$PYTHONPATH
# sed -i '/^from vllm\.entrypoints\.cli\.main import main$/a\
# from DotsOCR import modeling_dots_ocr_vllm' `which vllm`  # If you downloaded model weights by yourself, please replace `DotsOCR` by your model saved directory name, and remember to use a directory name without periods (e.g., `DotsOCR` instead of `dots.ocr`)
#
# # launch vllm server
# CUDA_VISIBLE_DEVICES=0 vllm serve ${hf_model_path} --tensor-parallel-size 1 --gpu-memory-utilization 0.95  --chat-template-content-format string --served-model-name model --trust-remote-code
#
# # If you get a ModuleNotFoundError: No module named 'DotsOCR', please check the note above on the saved model directory name.
#
# # vllm api demo
# python3 ./demo/demo_vllm.py --prompt_mode prompt_layout_all_en