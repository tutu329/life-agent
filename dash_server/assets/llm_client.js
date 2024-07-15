// 经过测试，Bash下的js是浏览器运行的js，和node.js有较大差别，/assets下存放js文件或直接用external_scripts=['https://cdn.jsdelivr.net/npm/axios@1.2.0/dist/axios.min.js']这样的方式
// 能用一些外部js库，但是行为和node.js不一样，如response.data.on这样的数据监听报错等。
// 因此，最后考虑用自带的fetch实现client侧的stream输出和set_props刷新

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    llm_client: {
        ask_llm: function(n_clicks, llm_input) {
            async function streamOutputFromOpenAI(prompt) {
              // 构建请求体
              const requestBody = {
                messages: [
                  {
                    role: 'system',
                    content: 'You are ChatGPT, a helpful assistant.'
                  },
                  {
                    role: 'user',
                    content: llm_input
                  }
                ],
                stream: true, // 启用流式输出
                "model": "qwen14", // 或者你选择的其他模型
                "temperature": 0.7,
                "max_tokens": 512,
              };

              // 使用 fetch 发送请求
              const response = await fetch("http://127.0.0.1:8001/v1/chat/completions", {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "Authorization": `Bearer empty` // 替换为你的 OpenAI API 密钥
                },
                body: JSON.stringify(requestBody)
              });

              // 处理流式响应
              if (response.body) {
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");

                var all_content = "";
                while (true) {
                  const { done, value } = await reader.read();
                  if (done) break;

                  const chunk = decoder.decode(value);

                  // fetch方式调用后，采用reader方式读取，是返回一行一行的字符串，要从字符串中解析出text
                  const lines = chunk.split("\n");
                  for (const line of lines) {
                    if (line.startsWith("data: ")) {
                      const data = JSON.parse(line.substring(6));
                      if (data.choices && data.choices[0]) {
                          if (data.choices[0].delta.content) {
                              console.log(data.choices[0].delta.content); // 打印流式输出的文本
                              all_content += data.choices[0].delta.content;
                              dash_clientside.set_props(
                                "output",
                                {
                                    'children': all_content,
                                    'style': {"color": "#ffffff"},
                                },
                              )
                          }
                      }
                    }
                  }
                }
              } else {
                console.error("streamOutputFromOpenAI() response为空.");
              }
            }
            // 示例调用
            streamOutputFromOpenAI(llm_input);
        }
    }
});