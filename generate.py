"""Windows English quiz video maker. Run: python generate.py"""
import asyncio
import json
import math
import os
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
STAMP = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
WORK = ROOT / 'work' / STAMP
OUTPUT = ROOT / 'videos'
FPS, SR, COUNTDOWN = 24, 48000, 10
FF = imageio_ffmpeg.get_ffmpeg_exe()
INK, GRAY, BLUE, GREEN = '#182433', '#637286', '#255ED7', '#14745A'
FONTS = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'


def font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ('arialbd.ttf' if bold else 'arial.ttf')), size)


def lines(draw, text, face, width):
    result, line = [], ''
    for word in text.split():
        candidate = (line + ' ' + word).strip()
        if draw.textlength(candidate, font=face) > width:
            if not line:
                raise ValueError('A word is too wide for this layout.')
            result.append(line)
            line = word
        else:
            line = candidate
    if line:
        result.append(line)
    return result


def paragraph(draw, text, x, y, face, width, leading):
    for line in lines(draw, text, face, width):
        draw.text((x, y), line, font=face, fill=INK)
        y += leading
    return y


def canvas(number, answer=False):
    im = Image.new('RGB', (1080, 1920), 'white')
    d = ImageDraw.Draw(im)
    color = GREEN if answer else BLUE
    d.text((64, 58), f'QUESTION {number:02d}', font=font(42, True), fill=INK)
    d.text((805, 69), 'ANSWER' if answer else 'PRACTICE', font=font(25, True), fill=GRAY)
    d.line((64, 131, 1016, 131), fill=color, width=4)
    return im, d


def question_page(item, number, seconds=None):
    im, d = canvas(number)
    for size in range(43, 35, -1):
        face, leading = font(size), round(size * 1.3)
        end = 176 + len(lines(d, item['question'], face, 952)) * leading + 40
        end += sum(len(lines(d, item['options'][k], face, 866)) * leading + 42 for k in 'ABCD')
        if end <= 1750:
            break
    else:
        raise ValueError(f'Question {number} is too long for a readable single page. No text was omitted.')
    y = paragraph(d, item['question'], 64, 176, face, 952, leading) + 32
    for letter in 'ABCD':
        d.line((64, y, 1016, y), fill='#DCE3ED', width=2)
        y += 20
        d.rounded_rectangle((64, y + 2, 115, y + 53), radius=8, fill='#F0F3F8')
        d.text((79, y + 9), letter, font=font(31, True), fill=INK)
        y = paragraph(d, item['options'][letter], 145, y, face, 871, leading) + 22
    if y >= 1770:
        raise ValueError(f'Question {number} exceeds the page boundary.')
    d.rounded_rectangle((64, 1795, 1016, 1884), radius=14, fill='#EDF3FF')
    label = 'LISTEN TO THE QUESTION' if seconds is None else 'CHOOSE YOUR ANSWER'
    d.text((89, 1825), label, font=font(27, True), fill=BLUE)
    if seconds is not None:
        d.text((912, 1816), f'{seconds:02d}', font=font(44, True), fill=BLUE)
    p = WORK / f'q{number:02d}-{seconds if seconds is not None else "read"}.png'
    im.save(p)
    return p


def answer_pages(item, number):
    """Keep normal font sizes and continue long explanations on the next page."""
    letter = item['answer']
    result = []
    im, d = canvas(number, True)
    d.text((64, 190), f'Correct answer: {letter}', font=font(66, True), fill=GREEN)
    text, face = item['options'][letter], font(44)
    bottom = 348 + len(lines(d, text, face, 872)) * 61 + 30
    d.rounded_rectangle((64, 317, 1016, bottom), radius=18, fill='#EDF7F2')
    paragraph(d, text, 104, 348, face, 872, 61)
    y = bottom + 60
    spoken = [f'The correct answer is {letter}.']
    limit, next_start = 1765, 340

    def save_page():
        p = WORK / f'q{number:02d}-answer-{len(result) + 1:02d}.png'
        im.save(p)
        result.append({'image': p, 'speech': ' '.join(spoken)})

    def next_page():
        nonlocal im, d, y, spoken
        save_page()
        im, d = canvas(number, True)
        d.text((64, 190), 'Explanation (continued)', font=font(58, True), fill=GREEN)
        y, spoken = next_start, []

    for section in item['explanation']:
        remaining = section['text'].split()
        if not remaining:
            continue
        title = section['title']
        continued = False
        while remaining:
            heading = title + (' (continued)' if continued else '')
            heading_height = len(lines(d, heading, font(45, True), 952)) * 59 + 18
            body_height = len(lines(d, ' '.join(remaining), font(43), 952)) * 61
            required = heading_height + body_height
            # Keep a section together when it fits on a fresh page.
            if y + required > limit and y > next_start and required <= limit - next_start:
                next_page()
            available_lines = int((limit - y - heading_height) // 61)
            if available_lines < 1:
                if y <= next_start:
                    raise ValueError(f'Answer {number}: a section title is too long to leave room for its text.')
                next_page()
                continue
            wrapped = lines(d, ' '.join(remaining), font(43), 952)
            take = len(' '.join(wrapped[:available_lines]).split())
            if take < len(remaining):
                # Prefer a sentence boundary to avoid splitting the narration mid-sentence.
                boundaries = [i + 1 for i, word in enumerate(remaining[:take]) if word.rstrip('\"\')]').endswith(('.', '!', '?'))]
                if boundaries:
                    take = boundaries[-1]
            chunk = ' '.join(remaining[:take])
            y = paragraph(d, heading, 64, y, font(45, True), 952, 59) + 18
            y = paragraph(d, chunk, 64, y, font(43), 952, 61)
            spoken.append(chunk)
            remaining = remaining[take:]
            if remaining:
                next_page()
                continued = True
            else:
                y += 48
    save_page()
    return result


def ffmpeg(args):
    p = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y'] + list(map(str, args)), capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode('utf-8', errors='replace'))


async def voice(text, name):
    spoken = text.replace('S3', 'S three').replace('500 GB', 'five hundred gigabytes')
    await edge_tts.Communicate(spoken, 'en-US-AriaNeural', rate='+0%', connect_timeout=10, receive_timeout=60).save(str(WORK / f'{name}.mp3'))


def audio(name, ending=False):
    target = WORK / f'{name}.wav'
    ffmpeg(['-i', WORK / f'{name}.mp3', '-ac', '1', '-ar', SR, target])
    with wave.open(str(target), 'rb') as w:
        pcm = w.readframes(w.getnframes())
    pcm = bytes(int(.2 * SR) * 2) + pcm + bytes(int((.7 if ending else .25) * SR) * 2)
    frames = math.ceil(len(pcm) / 2 / SR * FPS)
    pcm += bytes(frames * (SR // FPS) * 2 - len(pcm))
    return pcm, frames


def encode(job):
    index, picture, frames = job
    path = WORK / f'clip-{index:03d}.mp4'
    ffmpeg(['-loop', '1', '-framerate', FPS, '-i', picture, '-frames:v', frames, '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-crf', '21', '-threads', '2', '-pix_fmt', 'yuv420p', path])
    print(f'Encoded segment {index + 1}', flush=True)
    return path


async def main():
    questions = json.loads((ROOT / 'questions.json').read_text('utf-8-sig'))['questions']
    if not isinstance(questions, list) or not questions:
        raise ValueError('questions must be a nonempty list.')
    WORK.mkdir(parents=True)
    OUTPUT.mkdir(exist_ok=True)
    pages = []
    # Check every page before making any online speech requests.
    for number, item in enumerate(questions, 1):
        if set(item['options']) != set('ABCD') or item['answer'] not in 'ABCD' or len(item['answer']) != 1:
            raise ValueError(f'Question {number}: provide options A-D and one correct answer letter.')
        if not item['question'].strip() or not item['explanation'] or any(not item['options'][k].strip() for k in 'ABCD'):
            raise ValueError(f'Question {number}: question, options, and explanation must not be empty.')
        pictures = [question_page(item, number)]
        pictures += [question_page(item, number, n) for n in range(COUNTDOWN, 0, -1)]
        pages.append({'question': pictures, 'answer': answer_pages(item, number)})
    jobs, pcm_parts, timeline = [], [], []
    clock = 0
    for number, (item, pictures) in enumerate(zip(questions, pages), 1):
        print(f'Generating English speech for question {number}/{len(questions)}...', flush=True)
        await voice(item['question'], f'q{number}-read')
        qpcm, qframes = audio(f'q{number}-read')
        images = list(pictures['question'])
        durations = [qframes] + [FPS] * COUNTDOWN
        pcm_parts += [qpcm, bytes(COUNTDOWN * SR * 2)]
        answer_starts = []
        for page_index, page in enumerate(pictures['answer'], 1):
            name = f'q{number}-answer-{page_index}'
            await voice(page['speech'], name)
            apcm, aframes = audio(name, True)
            answer_starts.append(clock + sum(durations) / FPS)
            images.append(page['image'])
            durations.append(aframes)
            pcm_parts.append(apcm)
        timeline.append({'question': number, 'start': clock, 'countdown_start': clock + qframes / FPS, 'answer_start': clock + qframes / FPS + COUNTDOWN, 'answer_page_starts': answer_starts})
        clock += sum(durations) / FPS
        jobs += [(len(jobs) + i, picture, frames) for i, (picture, frames) in enumerate(zip(images, durations))]
    with ThreadPoolExecutor(max_workers=2) as pool:
        clips = list(pool.map(encode, jobs))
    with wave.open(str(WORK / 'narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        for pcm in pcm_parts:
            w.writeframes(pcm)
    (WORK / 'concat.txt').write_text('\n'.join("file '" + p.name + "'" for p in clips), encoding='utf-8')
    ffmpeg(['-f', 'concat', '-safe', '0', '-i', WORK / 'concat.txt', '-c', 'copy', WORK / 'silent.mp4'])
    final = OUTPUT / f'quiz_{STAMP}.mp4'
    ffmpeg(['-i', WORK / 'silent.mp4', '-i', WORK / 'narration.wav', '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-metadata:s:a:0', 'language=eng', '-movflags', '+faststart', final])
    (WORK / 'report.json').write_text(json.dumps({'duration_seconds': clock, 'questions': timeline, 'output': str(final)}, indent=2), encoding='utf-8')
    print(f'COMPLETE: {final}\nDuration: {clock:.1f} seconds', flush=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f'FAILED: {exc}', flush=True)
        raise SystemExit(1)
