import asyncio
import copy
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import AsyncMock, patch

import generate as g


class QuizVideoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'work'
        self.work.mkdir()
        self.patch = patch.multiple(g, ROOT=self.root, WORK=self.work, OUTPUT=self.root / 'videos')
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.item = {
            'number': 44,
            'question': 'Which option meets the requirement?',
            'options': {letter: f'Choose service {letter}.' for letter in 'ABCDE'},
            'answer': 'B',
            'explanation': [{'title': 'Why it works', 'text': 'The selected service meets the requirement.'}],
        }

    def test_correct_options_are_read_once_before_explanation(self):
        for answer in ('B', 'BE'):
            with self.subTest(answer=answer):
                self.item['answer'] = answer
                speech = ' '.join(p['speech'] for p in g.answer_pages(self.item, 1))
                expected = ('The correct answer is B. Choose service B.' if answer == 'B' else
                            'The correct answers are B and E. Option B. Choose service B. Option E. Choose service E.')
                self.assertEqual(speech, expected + ' Explanation. The selected service meets the requirement.')

    def test_long_question_shows_all_five_options_during_countdown(self):
        self.item['question'] = 'The company needs a reliable service for its daily processing workload. ' * 20
        self.item['options'] = {
            letter: f'Choice {letter}. ' + 'Configure the service to process incoming data automatically. ' * 3
            for letter in 'ABCDE'
        }
        with patch.object(g, 'paragraph', wraps=g.paragraph) as draw:
            g.question_page(self.item, 1)
            self.assertEqual([c.args[1] for c in draw.call_args_list], [self.item['question']])
        with patch.object(g, 'paragraph', wraps=g.paragraph) as draw:
            g.question_page(self.item, 1, 10)
            self.assertEqual([c.args[1] for c in draw.call_args_list], list(self.item['options'].values()))

    def test_continuation_preserves_explanation_and_original_header(self):
        text = ' '.join(f'Step {i} explains how the selected service meets the requirement.' for i in range(50))
        self.item['explanation'][0]['text'] = text
        with patch.object(g, 'canvas', wraps=g.canvas) as canvas:
            pages = g.answer_pages(self.item, 1, 'Example Exam')
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(c.args == (44, 'Example Exam', True) for c in canvas.call_args_list))
        speech = ' '.join(p['speech'] for p in pages)
        self.assertEqual(speech.split('Explanation. ', 1)[1], text)
        self.assertEqual(speech.count('Choose service B.'), 1)

    def test_timeline_has_ten_seconds_of_silence_before_answers(self):
        self.item['answer'] = 'eb'
        (self.root / 'questions.json').write_text(json.dumps({'questions': [self.item]}), encoding='utf-8')
        self.work.rmdir()  # main creates its own work directory.
        with patch.object(g, 'voice', new_callable=AsyncMock) as voice, \
                patch.object(g, 'audio', return_value=(b'\x01\x00' * g.SR, g.FPS)), \
                patch.object(g, 'encode', side_effect=lambda job: self.work / f'clip-{job[0]}.mp4'), \
                patch.object(g, 'ffmpeg'):
            asyncio.run(g.main())
        report = json.loads((self.work / 'report.json').read_text())
        timeline = report['questions'][0]
        self.assertEqual(timeline['question'], 44)
        self.assertEqual(timeline['answer_start'] - timeline['countdown_start'], 10)
        self.assertEqual(voice.await_args_list[0].args[0], self.item['question'])
        self.assertTrue(voice.await_args_list[1].args[0].startswith('The correct answers are B and E.'))
        with wave.open(str(self.work / 'narration.wav'), 'rb') as audio:
            audio.setpos(g.SR)
            self.assertEqual(audio.readframes(10 * g.SR), bytes(10 * g.SR * 2))

    def test_invalid_answers_fail_before_online_speech(self):
        for index, answer in enumerate(('BB', 'F', '')):
            with self.subTest(answer=answer):
                item = copy.deepcopy(self.item)
                item['answer'] = answer
                (self.root / 'questions.json').write_text(json.dumps({'questions': [item]}), encoding='utf-8')
                with patch.object(g, 'WORK', self.root / f'invalid-{index}'), \
                        patch.object(g, 'voice', new_callable=AsyncMock) as voice:
                    with self.assertRaisesRegex(ValueError, 'distinct letters'):
                        asyncio.run(g.main())
                    voice.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
