import unittest

from app.validator import validate_output


class ValidatorTest(unittest.TestCase):
    def test_validator_accepts_valid_output(self):
        title = "도쿄 후지산 버스 투어 추천 하는 이유"
        source = """상품명: 도쿄 후지산 버스 투어
가격: 9,800원
[image_1.jpg]
[image_2.jpg]
"""
        output = """제목을입력해주세요1: 도쿄 후지산 버스 투어 추천 하는 이유

본문2:
안녕하세요.

2026.06.01 방문 기준
확인한 내용입니다.

[image_1.jpg]

[image_2.jpg]

ㄱ. 기본정보
ㄴ. 이용 흐름
ㄷ. 확인할 점

ㅂㅂㅂ기본정보
가격 정보를
먼저 봤습니다.

표 2 x 2 시작
(0,0) 항목
(0,1) 내용
(1,0) 가격
(1,1) 9,800원
표 2 x 2 끝

ㅂㅂㅂ이용 흐름
원문 기준으로
흐름을 봤습니다.

ㅂㅂㅂ확인할 점
숫자 정보는
그대로 남겼습니다.
"""
        report = validate_output(title, source, output)
        self.assertTrue(report.passed)


    def test_validator_rejects_changed_title_and_missing_table(self):
        title = "도쿄 후지산 버스 투어 추천 하는 이유"
        source = "가격: 9,800원\n[image_1.jpg]"
        output = """제목을입력해주세요1: 바뀐 제목

본문2:
2026.06.01 방문 기준
[image_1.jpg]

ㅂㅂㅂ기본정보
가격은 좋았습니다.

ㅂㅂㅂ이용 흐름
확인했습니다.

ㅂㅂㅂ마치며
마무리했습니다.
"""
        report = validate_output(title, source, output)
        failure_names = {item.name for item in report.failures}
        self.assertIn("title_exact", failure_names)
        self.assertIn("table_required_for_info", failure_names)


if __name__ == "__main__":
    unittest.main()
