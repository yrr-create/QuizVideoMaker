# QuizVideoMaker

将英文选择题制作成竖屏刷题视频的 Windows/Python 小工具。

## 视频流程

1. 完整题干和 A–D 选项同页显示，只朗读英文题干。
2. 留在题目页，静默倒计时 10 秒。
3. 显示正确答案和英文解析；解析较长时自动续页，每页读完后再翻页。
4. 多道题按 JSON 中的顺序合成为一个 MP4。

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
  "questions": [
    {
      "question": "Full English question text.",
      "options": {
        "A": "First option.",
        "B": "Second option.",
        "C": "Third option.",
        "D": "Fourth option."
      },
      "answer": "A",
      "explanation": [
        {
          "title": "Why A works",
          "text": "A concise English explanation of the correct answer."
        }
      ]
    }
  ]
}
```

- 所有内容使用英文；JSON 文件保存为 UTF-8。
- `answer` 填 A、B、C 或 D。
- `explanation` 可按内容分段，不强制段数；每段有 `title` 和 `text`。
- 只播报题干、答案字母和解析正文，不播报选项及解析小标题。

## 版式与使用边界

- 解析超出页面时自动续页，保持正常字号，不截断正文。
- 题目和选项仍采用同页布局，极长题目超出可读容量时会提示。
- 工具会朗读 JSON 中提供的全部解析；不需要错误选项分析时，请不要将它写入解析。
- 技术缩写的合成发音可能需要人工听审。

## 配音、网络与费用

文字排版和视频编码在本机执行。英文旁白文本会发送到 Microsoft Edge 在线语音服务。

配音使用第三方 [edge-tts](https://github.com/rany2/edge-tts)，无需在本工具中填写 API Key。它依赖在线服务，可能受网络、服务变化或限流影响；本项目不承诺永久免费、无限量、持续可用或商业授权。

本工具没有使用付费视频生成模型。依赖为 [Pillow](https://python-pillow.org/)、[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) 和 edge-tts，各依赖适用其自身许可及相关服务条款。

更多说明见 [使用说明](使用说明.txt)。
