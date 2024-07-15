console.log('llm_client.js invoked...');

// console.log(axios);
// // const createParser = window.EventSourceParser.createParser;
// // const { createParser } = eventsourceParser;
// const parser = createParser({
//   feed(event) {
//     // 处理解析后的事件
//     console.log(event);
//   }
// });


window.dash_clientside = Object.assign({}, window.dash_clientside, {
    llm_client: {
        ask_llm: function(n_clicks, llm_input) {
            console.log(llm_input);

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
                // "prompt": prompt,
                // "temperature": 0.7,
                // "max_tokens": 256,
                // "stream": true // 启用流式输出
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

                  // console.log('chunk is: ', chunk)

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
                console.error("响应体为空");
              }
            }
            // 示例调用
            streamOutputFromOpenAI(llm_input);
        }
    }
});