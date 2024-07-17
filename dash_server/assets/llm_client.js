// 经过测试，Bash下的js是浏览器运行的js，和node.js有较大差别，/assets下存放js文件或直接用external_scripts=['https://cdn.jsdelivr.net/npm/axios@1.2.0/dist/axios.min.js']这样的方式
// 能用一些外部js库，但是行为和node.js不一样，如response.data.on这样的数据监听报错等。
// 因此，最后考虑用自带的fetch实现client侧的stream输出和set_props刷新

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    llm_client: {
        ask_llm: async function(n_clicks, llm_input) {
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
                    content: prompt
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

              var all_content = "";
              // 处理流式响应
              if (response.body) {
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");

                console.log('------------------while() entered. ------------------');
                while (true) {
                  const { done, value } = await reader.read();
                  // console.log('done:', done);
                  if (done) {
                    console.log('reader.read() done:', done);
                    break;
                  }

                  const raw_lines = decoder.decode(value);

                  // fetch方式调用后，采用reader方式读取，是返回一行一行的字符串，要从字符串中解析出text
                  const lines = raw_lines.split("\n");
                  for (const line of lines) {
                    if (line.startsWith("data: ")) {
                      const data = JSON.parse(line.substring(6));
                      if (data.choices[0].finish_reason=='stop') {
                        // stream结束，退出
                        break
                      }
                      if (data.choices && data.choices[0]) {
                          const chunk = data.choices[0].delta.content;
                          if (chunk) {
                              console.log(chunk); // 打印流式输出的文本
                              all_content += chunk;

                              // --------------------------刷新html--------------------------
                              dash_clientside.set_props(
                                "output",
                                {
                                    'children': all_content,
                                    'style': {"color": "#ffffff"},
                                },
                              )
                              console.log(chunk); // 打印流式输出的文本
                              // -----------------------------------------------------------

                          }
                      }
                    }
                  }
                  // console.log('all_content1:', all_content);

                }
                console.log('------------------while() exited. ------------------');

              } else {
                console.error("streamOutputFromOpenAI() response为空.");
              }
              return all_content;
            }
            // 示例调用
            let result = await streamOutputFromOpenAI(llm_input);

            var dict = {
                'chat_result': result,
            };

            dash_clientside.set_props(
              "local-mem",
              {
                  'data': dict,
              },
            )
            // 注意，js下无法和python一样返回多个参数，必须返回多个output的list(但仍然有问题，返回多个output会导致prevent_initial_call=True无效！)
            console.log('dict:', dict);
            console.log('result:', result);
            return result;
            // return [result+'_show', result+'_mem', result];
        }
    }
});