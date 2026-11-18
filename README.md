# QuizVideoMaker

将英文选择题制作成竖屏刷题视频的 Windows/Python 小工具。

## 视频流程

1. 显示完整题干和 A–D 或 A–E 选项，只朗读英文题干。长题先显示题干，读完后显示完整选项。
2. 显示全部选项，静默倒计时 10 秒。
3. 显示答案，先宣布正确答案字母，再完整朗读正确选项，最后朗读一段简短英文解析。多选题逐一朗读正确选项；内容较长时自动续页，每页读完后再翻页。
4. 多道题按 JSON 中的顺序合成为一个 MP4。

每页顶部显示原始题号和考试名称，默认考试名称为 AWS SAA-C03。

输出为 1080 × 1920、24 fps，英文合成配音，无背景音乐。工具不自动推理答案，解析需预先提供并核对。

## 开始使用

需要 Windows、Python 3.10+ 和网络连接。

1. 下载并解压仓库，或克隆到本机。
2. 编辑 `questions.json`，填写题干、选项、答案和解析。
3. 双击 `run.cmd`。首次运行会在项目内建立 `.venv` 并安装依赖。
4. 完成后在 `videos/` 中查看 MP4。

也可手动运行：

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe generate.py
```

中间图片、语音和时间信息保存在 `work/`。每次运行使用新的时间戳，不覆盖旧视频。

## 题目格式

`questions` 是题目数组；一个对象对应一道题，可以放入多道题。

```json
{
  "exam_title": "AWS SAA-C03",
  "questions": [
    {
      "number": 44,
      "question": "Full English question text.",
      "options": {
        "A": "First option.",
        "B": "Second option.",
        "C": "Third option.",
        "D": "Fourth option.",
        "E": "Fifth option."
      },
      "answer": "AB",
      "explanation": [
        {
          "title": "Why A and B work",
          "text": "One concise English paragraph explaining why the correct answers meet the requirements."
        }
      ]
    }
  ]
}
```

- 所有内容使用英文；JSON 文件保存为 UTF-8。
- `exam_title` 是考试名称；省略时使用 `AWS SAA-C03`。
- `number` 是原始题号，必须是正整数；省略时按列表顺序从 1 编号。
- `options` 支持 A–D 或 A–E；选项正文不必重复字母标签。
- `answer` 填单个字母（如 `C`）或连续的多个字母（如 `AB`、`BE`）；小写自动转大写，不能重复或引用不存在的选项。
- `explanation` 建议只放一条，包含简短的 `title` 和一段 `text`。用直白英文解释正确答案如何满足题意，以官方文档为依据，避免无关扩展。工具兼容旧的多段解析，但不会自动压缩或改写。
- 答题前只朗读题干；倒计时后朗读答案字母、正确选项全文和解析正文，不朗读解析小标题。

## 版式与使用边界

- 解析超出页面时自动续页，保持正常字号，不截断正文。
- 题干与选项优先同页，放不下时分为“题干页 → 完整选项及倒计时页”。题干或选项单独仍过长时明确报错，不删减文字。
- 多选答案一起显示；正确选项全文超出答案页容量时会明确报错。
- 工具会朗读 JSON 中提供的全部解析；不需要错误选项分析时，请不要将它写入解析。
- 技术缩写的合成发音可能需要人工听审。

## 配音、网络与费用

文字排版和视频编码在本机执行。英文旁白文本会发送到 Microsoft Edge 在线语音服务。

配音使用第三方 [edge-tts](https://github.com/rany2/edge-tts)，无需在本工具中填写 API Key。它依赖在线服务，可能受网络、服务变化或限流影响；本项目不承诺永久免费、无限量、持续可用或商业授权。

本工具没有使用付费视频生成模型。依赖为 [Pillow](https://python-pillow.org/)、[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) 和 edge-tts，各依赖适用其自身许可及相关服务条款。

示例题的解析依据 [Amazon Athena 官方说明](https://docs.aws.amazon.com/athena/latest/ug/what-is.html)，为简短转述。更多说明见 [使用说明](使用说明.txt)。

## 本地检查

安装依赖后运行：

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

检查单选、多选的答案朗读顺序、长题完整选项显示、解析续页，以及输入校验；这些检查不调用在线语音服务。
