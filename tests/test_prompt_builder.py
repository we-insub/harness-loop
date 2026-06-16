import unittest
from datetime import date

from app.config import VISIT_END, VISIT_START
from app.prompt_builder import extract_image_tags, make_prompt_inputs


class PromptBuilderTest(unittest.TestCase):
    def test_extract_image_tags_in_order(self):
        text = "앞 [image_1.jpg] 중간 [image_2.png] 끝"
        self.assertEqual(extract_image_tags(text), ["[image_1.jpg]", "[image_2.png]"])

    def test_visit_date_is_generated_in_allowed_range(self):
        inputs = make_prompt_inputs("제목", "가격: 9,800원", run_index=1)
        self.assertLessEqual(VISIT_START, inputs.visit_date)
        self.assertLessEqual(inputs.visit_date, VISIT_END)

    def test_source_visit_date_is_preserved(self):
        inputs = make_prompt_inputs("제목", "2026.06.01 방문 기준\n가격: 9,800원")
        self.assertEqual(inputs.visit_date, date(2026, 6, 1))


if __name__ == "__main__":
    unittest.main()
