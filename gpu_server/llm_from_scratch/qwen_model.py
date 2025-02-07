print(f'导入torch...'.center(80, '='))

from transformers import AutoTokenizer
from pprint import pprint
import torch
import os
import json

from safetensors import safe_open
import matplotlib.pyplot as plt
from tabulate import tabulate

def get_device_and_print_gpu_info():
    # 打印gpu信息
    table_data = []
    headers = [
        "Device", "Name", "VRAM (Used/Total)", "Compute"
    ]

    has_gpu = True if torch.cuda.is_available() else False

    if not has_gpu:
        table_data = [["CUDA 不可用", "N/A", "N/A", "N/A"]]
        print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="left"))
        return table_data

    gpu_count = torch.cuda.device_count()

    for i in range(gpu_count):
        name = torch.cuda.get_device_name(i)
        free_mem, total_mem = torch.cuda.mem_get_info(i)
        prop = torch.cuda.get_device_properties(i)

        used_mem_gb = (total_mem - free_mem) / 1024 ** 3
        total_mem_gb = total_mem / 1024 ** 3
        compute_cap = f"{prop.major}.{prop.minor}"

        row = [
            f"GPU {i}",
            name,
            f"{used_mem_gb:.2f}/{total_mem_gb:.2f} GB",
            compute_cap,
        ]
        table_data.append(row)

    print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="left"))

    # 返回device("cpu" or "cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# 读取model
def load_model(device, model_path, show_model_paras=False):
    model = {}

    # 获取目录下所有safetensors文件数量
    def count_safetensors_files(directory=model_path):
        files = os.listdir(directory)
        # 统计以.safetensors结尾的文件数量
        safetensors_count = len([f for f in files if f.endswith('.safetensors')])
        return safetensors_count

    safetensors_num = count_safetensors_files()

    # 读取model，并打印model中的keys
    print(f'获取model({model_path})...'.center(80, '='))
    for i in range(1, safetensors_num + 1):
        if safetensors_num==1:
            file_name = "model.safetensors"
        else:
            file_name = f"model-0000{i}-of-0000{safetensors_num}.safetensors"
        with safe_open(os.path.join(model_path, file_name), framework="pt", device="cpu") as f:
            if show_model_paras:
                print(f'* keys in "{file_name}":')
                pprint(f.keys())

            for k in f.keys():
                model[k] = f.get_tensor(k).to(device)

    return model


# 打印config信息
def print_config(config):
    # 计算最长键的长度
    key_width = max(len(key) for key in config.keys())
    # 计算最长值的长度（将值转换为字符串）
    val_width = max(len(str(val)) for val in config.values())
    # 打印格式化的结果
    for key, value in config.items():
        print(f'\t {key:<{key_width}}: {str(value)!r:>{val_width}}')


def load_config(model_path, file_name='config.json'):
    with open(os.path.join(model_path, file_name), "r") as f:
        config = json.load(f)
        print_config(config)
        return config


class Qwen_Model:
    def __init__(self):
        self.device = None
        self.model = None
        self.tokenizer = None
        self.config = None

        self.show_tensor=None

    def init(self, model_path, show_model_paras=False, show_tensor=True):
        self.device = get_device_and_print_gpu_info()
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = load_model(self.device, model_path, show_model_paras=show_model_paras)
        self.config = load_config(model_path=model_path, file_name='config.json')

        self._init_config(self.config)

        self.show_tensor = show_tensor

    def print_tensor(self, title, tensor):
        if not self.show_tensor:
            return
        """
        按照如下规则构造表格：
          1. 表头第一列为 "Row\Col"，后面依次显示前几列的列号，
             如果 tensor 列数超过 col_limit，则倒数第二个单元格显示 "..."，
             最后一个单元格显示总列数。
          2. 对于数据行：每行第一列显示行号，
             后面依次显示前几列的数据（格式化为小数 3 位），
             如果 tensor 列数超过 col_limit，则该行倒数第二个单元格显示 "..."，
             倒数最后一个单元格留空。
          3. 如果 tensor 行数超过 row_limit，则在数据行下方插入一行全 "..."（省略行）。
          4. 最后一行为汇总行：第一列显示总行数，
             如果 tensor 列数超过 col_limit，则倒数第二个单元格显示 "..."，
             最后一个单元格显示总列数，其余单元格留空。
        """
        print(f'【{title}】'.center(80, '='))
        if tensor.ndim == 1:
            total_rows = tensor.shape[0]
            total_cols = 1
        elif tensor.ndim >= 3:
            print(tensor.shape)
            return
        else:
            total_rows, total_cols = tensor.shape

        if total_rows > total_cols:
            row_limit = 5
            col_limit = 4
        elif total_rows < total_cols:
            row_limit = 4
            col_limit = 5
        else:
            row_limit = 4
            col_limit = 4

        # 判断是否需要截断（即 tensor 的行或列数超过上限）
        truncated_rows = total_rows > row_limit
        truncated_cols = total_cols > col_limit

        # 若截断，则实际显示的数据行/列数为：上限减去 2（最后一行/列用于汇总，倒数第二行/列用于显示 "..."）
        disp_rows = (row_limit - 2) if truncated_rows else total_rows
        disp_cols = (col_limit - 2) if truncated_cols else total_cols

        # 构造表头：第一列为 "Row\Col"
        # header = [title]
        header = ['']
        # 显示前 disp_cols 列的列号
        for j in range(disp_cols):
            header.append(str(j + 1))
        if total_cols > 1:
            if truncated_cols:
                # 倒数第二列显示省略号，最后一列显示总列数
                header.append("...")
                header.append(str(total_cols))
            else:
                # 不截断时，最后一列仍显示总列数（作为附加信息）
                header.append(str(total_cols))

        table = []
        # 构造数据行：显示前 disp_rows 行数据
        for i in range(disp_rows):
            row = [str(i + 1)]  # 第一列显示行号
            # 显示前 disp_cols 个数据（格式化为浮点数，保留 3 位小数）
            for j in range(disp_cols):
                if total_cols == 1:
                    value = f"{tensor[i]:6.3f}"
                else:
                    value = f"{tensor[i, j]:6.3f}"
                row.append(f'"{value}"')
            if total_cols > 1:
                if truncated_cols:
                    row.append("...")  # 倒数第二列显示省略号
                    row.append("")  # 最后一列留空
                else:
                    row.append("")
            table.append(row)

        # 如果行数需要截断，则在数据行后增加一行全 "..."（省略行）
        if truncated_rows:
            ellipsis_row = ["..."] * len(header)
            table.append(ellipsis_row)

        # 最后一行为汇总行：
        # 第一列显示总行数，其余单元格为空，
        # 如果列数截断，则倒数第二个单元格显示 "..."，最后一个单元格显示总列数
        summary_row = [str(total_rows)]
        if total_cols > 1:
            if truncated_cols:
                summary_row.extend([""] * disp_cols)
                summary_row.append("...")
                summary_row.append("")
            else:
                summary_row.extend([""] * disp_cols)
                summary_row.append(str(total_cols))
        table.append(summary_row)

        print(tabulate(table, headers=header, tablefmt="grid"))

    def get_token_ids(self, tokens):
        token_ids = self.tokenizer.encode(tokens)
        print(f'{tokens!r}对应的token_ids为: "{token_ids!r}"')
        return token_ids

    def _init_config(self, config):
        self.dim = config["hidden_size"]
        self.n_layers = config["num_hidden_layers"]
        self.n_heads = config["num_attention_heads"]
        self.n_kv_heads = config["num_key_value_heads"]
        self.vocab_size = config["vocab_size"]
        self.ffn_dim_multiplier = config["intermediate_size"]
        self.norm_eps = config["rms_norm_eps"]
        self.rope_theta = torch.tensor(config["rope_theta"], device=self.device)

    def rms_norm(self, tensor, norm_weights):
        return (tensor * torch.rsqrt(tensor.pow(2).mean(-1, keepdim=True) + self.norm_eps)) * norm_weights

    def infer(self, prompt):
        # prompt->tokens
        tokens = self.tokenizer.encode(prompt)
        tokens = torch.tensor(tokens, device=self.device)
        print('输入的prompt'.center(80, '='))
        print(f'\t tokens: {tokens}')
        your_input_tokens = tokens.tolist()
        print(f'\t tokens list: {your_input_tokens}')
        prompt_split_as_tokens = [self.tokenizer.decode([token.item()]) for token in tokens]
        print(f'\t prompt_split_as_tokens: {prompt_split_as_tokens}')

        # 读取embedding_layer
        print(f'读取embedding_layer...'.center(80, '='))
        embedding_layer = torch.nn.Embedding(self.vocab_size, self.dim, device=self.device)
        embedding_layer.weight.data.copy_(self.model["model.embed_tokens.weight"])
        self.print_tensor('embedding_layer.weight', embedding_layer.weight)

        # 获取prompt的token_embeddings_unnormalized
        print(f'获取prompt的token_embeddings_unnormalized...'.center(80, '='))
        token_embeddings_unnormalized = embedding_layer(tokens).to(torch.bfloat16)
        # print(f'token_embeddings_unnormalized:"{token_embeddings_unnormalized}"')
        self.print_tensor('token_embeddings_unnormalized', token_embeddings_unnormalized)

        # 获取prompt的token_embeddings
        token_embeddings = self.rms_norm(token_embeddings_unnormalized, self.model["model.layers.0.input_layernorm.weight"])
        self.print_tensor('token_embeddings', token_embeddings)

        # self.print_tensor('layers.0.q.weight', self.model["model.layers.0.self_attn.q_proj.weight"])
        # self.print_tensor('layers.0.q.bias', self.model["model.layers.0.self_attn.q_proj.bias"])
        # self.print_tensor('layers.0.k.weight', self.model["model.layers.0.self_attn.k_proj.weight"])
        # self.print_tensor('layers.0.k.bias', self.model["model.layers.0.self_attn.k_proj.bias"])
        # self.print_tensor('layers.0.v.weight', self.model["model.layers.0.self_attn.v_proj.weight"])
        # self.print_tensor('layers.0.v.bias', self.model["model.layers.0.self_attn.v_proj.bias"])
        # self.print_tensor('layers.0.o.weight', self.model["model.layers.0.self_attn.o_proj.weight"])

        # 获取Q
        q_layer0 = self.model["model.layers.0.self_attn.q_proj.weight"]
        self.print_tensor('q_layer0', q_layer0)

        head_dim = q_layer0.shape[0] // self.n_heads
        q_layer0 = q_layer0.view(self.n_heads, 2, head_dim // 2, self.dim).permute(0, 2, 1, 3).reshape(self.n_heads, head_dim, self.dim)
        self.print_tensor('q_layer0.reshape(): ', q_layer0)
        q_layer0_bias = self.model["model.layers.0.self_attn.q_proj.bias"].reshape(self.n_heads, -1)
        self.print_tensor('q_layer0_bias: ', q_layer0_bias)

        # Q = x * w_Q_T + b_q
        q_layer0_head0 = q_layer0[0]
        q_layer0_bias_head0 = q_layer0_bias[0]
        q_per_token = torch.matmul(token_embeddings, q_layer0_head0.T) + q_layer0_bias_head0
        self.print_tensor('q_per_token: ', q_per_token)

        # RoPE(增加每一个token的顺序信息)
        q_per_token_split_into_pairs = q_per_token.float().view(q_per_token.shape[0], -1, 2)
        self.print_tensor('q_per_token_split_into_pairs: ', q_per_token_split_into_pairs)

        zero_to_one_split_into_64_parts = torch.tensor(range(64), device=self.device) / 64
        print('zero_to_one_split_into_64_parts'.center(80, '='))
        print(zero_to_one_split_into_64_parts)

        freqs = 1.0 / (self.rope_theta ** zero_to_one_split_into_64_parts)
        print('rope_theta'.center(80, '='))
        print(self.rope_theta)
        print('freqs=1/(rope_theta^zero_to_one_split_into_64_parts)'.center(80, '='))
        print(freqs)

        freqs_for_each_token = torch.outer(torch.arange(len(tokens), device=self.device), freqs)
        freqs_cis = torch.polar(torch.ones_like(freqs_for_each_token), freqs_for_each_token)

        q_per_token_as_complex_numbers = torch.view_as_complex(q_per_token_split_into_pairs)
        self.print_tensor('q_per_token_as_complex_numbers: ', q_per_token_as_complex_numbers)
        q_per_token_as_complex_numbers_rotated = q_per_token_as_complex_numbers * freqs_cis
        self.print_tensor('q_per_token_as_complex_numbers_rotated: ', q_per_token_as_complex_numbers_rotated)
        q_per_token_split_into_pairs_rotated = torch.view_as_real(q_per_token_as_complex_numbers_rotated)
        q_per_token_rotated = q_per_token_split_into_pairs_rotated.view(q_per_token.shape)
        self.print_tensor('q_per_token_rotated: ', q_per_token_rotated)

        # K的操作基本和Q一样
        # K = x * w_K_T + b_k
        k_layer0 = self.model["model.layers.0.self_attn.k_proj.weight"]
        k_layer0 = k_layer0.view(self.n_kv_heads, 2, k_layer0.shape[0] // self.n_kv_heads // 2, self.dim).permute(0, 2, 1, 3).reshape(self.n_kv_heads, k_layer0.shape[0] // self.n_kv_heads, self.dim)
        k_layer0_bias = self.model["model.layers.0.self_attn.k_proj.bias"].reshape(self.n_heads, -1)
        k_layer0_head0 = k_layer0[0]
        k_layer0_bias_head0 = k_layer0_bias[0]
        k_per_token = torch.matmul(token_embeddings, k_layer0_head0.T) + k_layer0_bias_head0
        k_per_token_split_into_pairs = k_per_token.float().view(k_per_token.shape[0], -1, 2)
        k_per_token_as_complex_numbers = torch.view_as_complex(k_per_token_split_into_pairs)
        k_per_token_split_into_pairs_rotated = torch.view_as_real(k_per_token_as_complex_numbers * freqs_cis)
        k_per_token_rotated = k_per_token_split_into_pairs_rotated.view(k_per_token.shape)
        self.print_tensor('k_per_token_rotated: ', k_per_token_rotated)

        # Q * K_T
        qk_per_token = torch.matmul(q_per_token_rotated, k_per_token_rotated.T) / (head_dim) ** 0.5
        self.print_tensor('qk_per_token: ', qk_per_token)

        def display_qk_heatmap(qk_per_token):
            _, ax = plt.subplots()
            im = ax.imshow(qk_per_token.to(float).detach().cpu(), cmap='viridis')
            ax.set_xticks(range(len(prompt_split_as_tokens)))
            ax.set_yticks(range(len(prompt_split_as_tokens)))
            ax.set_xticklabels(prompt_split_as_tokens)
            ax.set_yticklabels(prompt_split_as_tokens)
            ax.figure.colorbar(im, ax=ax)

        # 做上三角mask
        mask = torch.full((len(tokens), len(tokens)), float("-inf"), device=self.device)
        mask = torch.triu(mask, diagonal=1)
        qk_per_token_after_masking = qk_per_token + mask
        qk_per_token_after_masking_after_softmax = torch.nn.functional.softmax(qk_per_token_after_masking, dim=1).to(torch.bfloat16)
        self.print_tensor('qk_per_token_after_masking_after_softmax: ', qk_per_token_after_masking_after_softmax)

        # V = x * w_V_T + b_V
        v_layer0 = self.model["model.layers.0.self_attn.v_proj.weight"]
        v_layer0 = v_layer0.view(self.n_kv_heads, v_layer0.shape[0] // self.n_kv_heads, self.dim)
        v_layer0_bias = self.model["model.layers.0.self_attn.v_proj.bias"].reshape(self.n_heads, -1)
        v_layer0_head0 = v_layer0[0]
        v_layer0_bias_head0 = v_layer0_bias[0]
        v_per_token = torch.matmul(token_embeddings, v_layer0_head0.T) + v_layer0_bias_head0

        # QKV = softmax(mask(Q * K_T)) * V
        qkv_attention = torch.matmul(qk_per_token_after_masking_after_softmax, v_per_token)

        qkv_attention_store = []
        GQA_num = 1
        for head in range(self.n_heads):
            q_layer0_head = q_layer0[head]
            k_layer0_head = k_layer0[head // GQA_num]
            v_layer0_head = v_layer0[head // GQA_num]
            q_per_token = torch.matmul(token_embeddings, q_layer0_head.T)
            k_per_token = torch.matmul(token_embeddings, k_layer0_head.T)
            v_per_token = torch.matmul(token_embeddings, v_layer0_head.T)

            q_per_token_split_into_pairs = q_per_token.float().view(q_per_token.shape[0], -1, 2)
            q_per_token_as_complex_numbers = torch.view_as_complex(q_per_token_split_into_pairs)
            q_per_token_split_into_pairs_rotated = torch.view_as_real(
                q_per_token_as_complex_numbers * freqs_cis[:len(tokens)])
            q_per_token_rotated = q_per_token_split_into_pairs_rotated.view(q_per_token.shape)

            k_per_token_split_into_pairs = k_per_token.float().view(k_per_token.shape[0], -1, 2)
            k_per_token_as_complex_numbers = torch.view_as_complex(k_per_token_split_into_pairs)
            k_per_token_split_into_pairs_rotated = torch.view_as_real(
                k_per_token_as_complex_numbers * freqs_cis[:len(tokens)])
            k_per_token_rotated = k_per_token_split_into_pairs_rotated.view(k_per_token.shape)

            qk_per_token = torch.matmul(q_per_token_rotated, k_per_token_rotated.T) / (128) ** 0.5
            mask = torch.full((len(tokens), len(tokens)), float("-inf"), device=self.device)
            mask = torch.triu(mask, diagonal=1)
            qk_per_token_after_masking = qk_per_token + mask
            qk_per_token_after_masking_after_softmax = torch.nn.functional.softmax(qk_per_token_after_masking,
                                                                                   dim=1).to(torch.bfloat16)
            qkv_attention = torch.matmul(qk_per_token_after_masking_after_softmax, v_per_token)
            qkv_attention_store.append(qkv_attention)

        stacked_qkv_attention = torch.cat(qkv_attention_store, dim=-1)
        w_layer0 = self.model["model.layers.0.self_attn.o_proj.weight"]
        embedding_delta = torch.matmul(stacked_qkv_attention, w_layer0.T)
        embedding_after_edit = token_embeddings_unnormalized + embedding_delta
        embedding_after_edit_normalized = self.rms_norm(embedding_after_edit,
                                                   self.model["model.layers.0.post_attention_layernorm.weight"])

        w1 = self.model["model.layers.0.mlp.gate_proj.weight"]
        w2 = self.model["model.layers.0.mlp.down_proj.weight"]
        w3 = self.model["model.layers.0.mlp.up_proj.weight"]
        output_after_feedforward = torch.matmul(
            torch.functional.F.silu(torch.matmul(embedding_after_edit_normalized, w1.T)) * torch.matmul(
                embedding_after_edit_normalized, w3.T), w2.T)
        layer_0_embedding = embedding_after_edit + output_after_feedforward

        k_cache, v_cache = [], []

        final_embedding = token_embeddings_unnormalized
        GQA_num = 1
        for layer in range(self.n_layers):
            k_cache.append([])
            v_cache.append([])
            qkv_attention_store = []
            layer_embedding_norm = self.rms_norm(final_embedding, self.model[f"model.layers.{layer}.input_layernorm.weight"])
            q_layer = self.model[f"model.layers.{layer}.self_attn.q_proj.weight"]
            q_layer = q_layer.view(self.n_heads, 2, q_layer.shape[0] // self.n_heads // 2, self.dim).permute(0, 2, 1,
                                                                                                             3).reshape(
                self.n_heads, q_layer.shape[0] // self.n_heads, self.dim)
            q_layer_bias = self.model[f"model.layers.{layer}.self_attn.q_proj.bias"].reshape(self.n_heads, -1)
            k_layer = self.model[f"model.layers.{layer}.self_attn.k_proj.weight"]
            k_layer = k_layer.view(self.n_kv_heads, 2, k_layer.shape[0] // self.n_kv_heads // 2, self.dim).permute(0, 2,
                                                                                                                   1,
                                                                                                                   3).reshape(
                self.n_kv_heads, k_layer.shape[0] // self.n_kv_heads, self.dim)
            k_layer_bias = self.model[f"model.layers.{layer}.self_attn.k_proj.bias"].reshape(self.n_heads, -1)
            v_layer = self.model[f"model.layers.{layer}.self_attn.v_proj.weight"]
            v_layer = v_layer.view(self.n_kv_heads, v_layer.shape[0] // self.n_kv_heads, self.dim)
            v_layer_bias = self.model[f"model.layers.{layer}.self_attn.v_proj.bias"].reshape(self.n_heads, -1)
            for head in range(self.n_heads):
                q_layer_head = q_layer[head]
                k_layer_head = k_layer[head // GQA_num]
                v_layer_head = v_layer[head // GQA_num]
                q_layer_bias_head = q_layer_bias[head]
                k_layer_bias_head = k_layer_bias[head // GQA_num]
                v_layer_bias_head = v_layer_bias[head // GQA_num]

                q_per_token = torch.matmul(layer_embedding_norm, q_layer_head.T) + q_layer_bias_head
                k_per_token = torch.matmul(layer_embedding_norm, k_layer_head.T) + k_layer_bias_head
                v_per_token = torch.matmul(layer_embedding_norm, v_layer_head.T) + v_layer_bias_head

                if head % GQA_num == 0:
                    v_cache[-1].append(v_per_token)
                q_per_token_split_into_pairs = q_per_token.float().view(q_per_token.shape[0], -1, 2)
                q_per_token_as_complex_numbers = torch.view_as_complex(q_per_token_split_into_pairs)
                q_per_token_split_into_pairs_rotated = torch.view_as_real(q_per_token_as_complex_numbers * freqs_cis)
                q_per_token_rotated = q_per_token_split_into_pairs_rotated.view(q_per_token.shape)

                k_per_token_split_into_pairs = k_per_token.float().view(k_per_token.shape[0], -1, 2)
                k_per_token_as_complex_numbers = torch.view_as_complex(k_per_token_split_into_pairs)
                k_per_token_split_into_pairs_rotated = torch.view_as_real(k_per_token_as_complex_numbers * freqs_cis)
                k_per_token_rotated = k_per_token_split_into_pairs_rotated.view(k_per_token.shape)

                if head % GQA_num == 0:
                    k_cache[-1].append(k_per_token_rotated)

                qk_per_token = torch.matmul(q_per_token_rotated, k_per_token_rotated.T) / (128) ** 0.5
                mask = torch.full((len(token_embeddings_unnormalized), len(token_embeddings_unnormalized)),
                                  float("-inf"), device=self.device)
                mask = torch.triu(mask, diagonal=1)
                qk_per_token_after_masking = qk_per_token + mask
                qk_per_token_after_masking_after_softmax = torch.nn.functional.softmax(qk_per_token_after_masking,
                                                                                       dim=1).to(torch.bfloat16)
                qkv_attention = torch.matmul(qk_per_token_after_masking_after_softmax, v_per_token)
                qkv_attention_store.append(qkv_attention)

            stacked_qkv_attention = torch.cat(qkv_attention_store, dim=-1)
            w_layer = self.model[f"model.layers.{layer}.self_attn.o_proj.weight"]
            embedding_delta = torch.matmul(stacked_qkv_attention, w_layer.T)
            embedding_after_edit = final_embedding + embedding_delta
            embedding_after_edit_normalized = self.rms_norm(embedding_after_edit, self.model[
                f"model.layers.{layer}.post_attention_layernorm.weight"])
            w1 = self.model[f"model.layers.{layer}.mlp.gate_proj.weight"]
            w2 = self.model[f"model.layers.{layer}.mlp.down_proj.weight"]
            w3 = self.model[f"model.layers.{layer}.mlp.up_proj.weight"]
            output_after_feedforward = torch.matmul(
                torch.functional.F.silu(torch.matmul(embedding_after_edit_normalized, w1.T)) * torch.matmul(
                    embedding_after_edit_normalized, w3.T), w2.T)
            final_embedding = embedding_after_edit + output_after_feedforward

        final_embedding = self.rms_norm(final_embedding, self.model["model.norm.weight"])
        logits = torch.matmul(final_embedding[-1], self.model["lm_head.weight"].T)
        next_token = torch.argmax(logits, dim=-1)

        print('======输入的prompt======')
        for i in range(len(prompt_split_as_tokens)):
            token_text = f'({your_input_tokens[i]})'
            print(f'{prompt_split_as_tokens[i]}\t{token_text:>10}')

        print('=======输出的内容=======')
        token_text = f'({next_token.item()})'
        print(f'{self.tokenizer.decode([next_token.item()])}\t{token_text:>10}', flush=True)

        max_new_len = 8
        seq_len = len(tokens)
        GQA_num = 1

        next_token = torch.tensor([next_token.item()], device=self.device)
        for _ in range(max_new_len - 1):
            if next_token[-1].item() == 151643:
                break
            next_token_embeddings_unnormalized = embedding_layer(next_token).to(torch.bfloat16)
            final_embedding = next_token_embeddings_unnormalized
            for layer in range(self.n_layers):
                qkv_attention_store = []
                layer_embedding_norm = self.rms_norm(final_embedding,
                                                self.model[f"model.layers.{layer}.input_layernorm.weight"])
                q_layer = self.model[f"model.layers.{layer}.self_attn.q_proj.weight"]
                q_layer = q_layer.view(self.n_heads, 2, q_layer.shape[0] // self.n_heads // 2, self.dim).permute(0, 2,
                                                                                                                 1,
                                                                                                                 3).reshape(
                    self.n_heads, q_layer.shape[0] // self.n_heads, self.dim)
                q_layer_bias = self.model[f"model.layers.{layer}.self_attn.q_proj.bias"].reshape(self.n_heads, -1)
                k_layer = self.model[f"model.layers.{layer}.self_attn.k_proj.weight"]
                k_layer = k_layer.view(self.n_kv_heads, 2, k_layer.shape[0] // self.n_kv_heads // 2, self.dim).permute(
                    0, 2, 1, 3).reshape(self.n_kv_heads, k_layer.shape[0] // self.n_kv_heads, self.dim)
                k_layer_bias = self.model[f"model.layers.{layer}.self_attn.k_proj.bias"].reshape(self.n_heads, -1)
                v_layer = self.model[f"model.layers.{layer}.self_attn.v_proj.weight"]
                v_layer = v_layer.view(self.n_kv_heads, v_layer.shape[0] // self.n_kv_heads, self.dim)
                v_layer_bias = self.model[f"model.layers.{layer}.self_attn.v_proj.bias"].reshape(self.n_heads, -1)

                for head in range(self.n_heads):
                    q_layer_head = q_layer[head]
                    k_layer_head = k_layer[head // GQA_num]
                    v_layer_head = v_layer[head // GQA_num]
                    q_layer_bias_head = q_layer_bias[head]
                    k_layer_bias_head = k_layer_bias[head // GQA_num]
                    v_layer_bias_head = v_layer_bias[head // GQA_num]

                    q_per_token = torch.matmul(layer_embedding_norm, q_layer_head.T) + q_layer_bias_head
                    q_per_token_split_into_pairs = q_per_token.float().view(q_per_token.shape[0], -1, 2)
                    q_per_token_as_complex_numbers = torch.view_as_complex(q_per_token_split_into_pairs)
                    freqs_for_next_token = torch.outer(torch.tensor([seq_len], device=self.device), freqs)
                    freqs_cis_next_token = torch.polar(torch.ones_like(freqs_for_next_token), freqs_for_next_token)
                    q_per_token_split_into_pairs_rotated = torch.view_as_real(
                        q_per_token_as_complex_numbers * freqs_cis_next_token)
                    q_per_token_rotated = q_per_token_split_into_pairs_rotated.view(q_per_token.shape)

                    if head % GQA_num == 0:
                        v_per_token = torch.matmul(layer_embedding_norm, v_layer_head.T) + v_layer_bias_head
                        v_cache[layer][head // GQA_num] = torch.cat([v_cache[layer][head // GQA_num], v_per_token],
                                                                    dim=0)
                        k_per_token = torch.matmul(layer_embedding_norm, k_layer_head.T) + k_layer_bias_head
                        k_per_token_split_into_pairs = k_per_token.float().view(k_per_token.shape[0], -1, 2)
                        k_per_token_as_complex_numbers = torch.view_as_complex(k_per_token_split_into_pairs)
                        k_per_token_split_into_pairs_rotated = torch.view_as_real(
                            k_per_token_as_complex_numbers * freqs_cis_next_token)
                        k_per_token_rotated = k_per_token_split_into_pairs_rotated.view(k_per_token.shape)
                        k_cache[layer][head // GQA_num] = torch.cat(
                            [k_cache[layer][head // GQA_num], k_per_token_rotated], dim=0)

                    qk_per_token = torch.matmul(q_per_token_rotated, k_cache[layer][head // GQA_num].T) / (128) ** 0.5
                    qk_per_token_after_masking = qk_per_token
                    qk_per_token_after_masking_after_softmax = torch.nn.functional.softmax(qk_per_token_after_masking,
                                                                                           dim=1).to(torch.bfloat16)
                    qkv_attention = torch.matmul(qk_per_token_after_masking_after_softmax,
                                                 v_cache[layer][head // GQA_num])
                    qkv_attention_store.append(qkv_attention)

                stacked_qkv_attention = torch.cat(qkv_attention_store, dim=-1)
                w_layer = self.model[f"model.layers.{layer}.self_attn.o_proj.weight"]
                embedding_delta = torch.matmul(stacked_qkv_attention, w_layer.T)
                embedding_after_edit = final_embedding + embedding_delta
                embedding_after_edit_normalized = self.rms_norm(embedding_after_edit, self.model[
                    f"model.layers.{layer}.post_attention_layernorm.weight"])
                w1 = self.model[f"model.layers.{layer}.mlp.gate_proj.weight"]
                w2 = self.model[f"model.layers.{layer}.mlp.down_proj.weight"]
                w3 = self.model[f"model.layers.{layer}.mlp.up_proj.weight"]
                output_after_feedforward = torch.matmul(
                    torch.functional.F.silu(torch.matmul(embedding_after_edit_normalized, w1.T)) * torch.matmul(
                        embedding_after_edit_normalized, w3.T), w2.T)
                final_embedding = embedding_after_edit + output_after_feedforward

            final_embedding = self.rms_norm(final_embedding, self.model["model.norm.weight"])
            logits = torch.matmul(final_embedding, self.model["lm_head.weight"].T)
            next_token = torch.argmax(logits, dim=-1)
            token_text = f'({next_token.item()})'
            print(f'{self.tokenizer.decode([next_token.item()])}\t{token_text:>10}', flush=True)
            seq_len += 1
        print('推理正常结束'.center(80, '='))


def main():
    model = Qwen_Model()
    # model.init(model_path=r"D:\models\Qwen2.5-14B-Instruct-GPTQ-Int4", show_model_paras=True)
    model.init(model_path="/home/tutu/models/Qwen1.5-4B-Chat", show_model_paras=False, show_tensor=True)

    model.infer(prompt='朱元璋定睛一看，发现')
    model.get_token_ids('q')
    model.get_token_ids('r')
    model.get_token_ids('s')
    # model.infer(prompt='北国风光，千里冰封，')


if __name__ == "__main__":
    main()
