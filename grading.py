# 사용자가 입력한 답이 정답과 맞는지 채점하는 함수
def grade_answer(user_answer: str, correct_answer: str) -> bool:
    user = user_answer.strip().lower()
    if not user:
        return False
    answers = [answer.strip().lower() for answer in correct_answer.split("/")]
    return user in answers
