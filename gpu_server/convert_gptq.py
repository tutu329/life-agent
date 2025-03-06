# Copyright 2025 ModelCloud
# Contact: qubitium@modelcloud.ai, x.com/qubitium
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
from gptqmodel import GPTQModel, QuantizeConfig
from transformers import AutoTokenizer

original_model_path = '/home/tutu/models/QwQ-32B'
pretrained_model_id = original_model_path
quantized_model_id = original_model_path + "-gptq"


def main():
    print('开始量化...')
    print('读取tokenizer...')

    tokenizer = AutoTokenizer.from_pretrained(pretrained_model_id, use_fast=True)
    examples = [
        tokenizer(
            "gptqmodel is an easy-to-use model quantization library with user-friendly apis, based on GPTQ algorithm."
        )
    ]

    quantize_config = QuantizeConfig(
        bits=4,  # quantize model to 4-bit
        group_size=128,  # it is recommended to set the value to 128
    )

    print('读取模型...')

    model = GPTQModel.load(
        pretrained_model_id,
        quantize_config=quantize_config,
    )

    print('正在量化...')

    model.quantize(examples)

    print('存储量化...')

    model.save(quantized_model_id)

    tokenizer.save_pretrained(quantized_model_id)

    print('量化完成.')

if __name__ == "__main__":
    main()