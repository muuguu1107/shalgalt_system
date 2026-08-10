from flask import Flask, render_template, request, redirect, url_for, session
import os
import re
import random
import pandas as pd
from datetime import datetime


app = Flask(__name__)

# Session ашиглана
app.secret_key = "shalgalt-system-2026"


# =========================================================
# ТОХИРГОО
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

QUESTION_COUNT = 10

EXAM_MINUTES = 10

PASS_SCORE = 8


# =========================================================
# ШАЛГАЛТЫН ФАЙЛУУД
# =========================================================

EXAM_FILES = {

    "ААД": os.path.join(
        BASE_DIR,
        "ААД",
        "questions.txt"
    ),

    "Нарядын систем": os.path.join(
        BASE_DIR,
        "Нарядын систем",
        "questions.txt"
    )

}


# =========================================================
# EXCEL ФАЙЛ
# =========================================================

RESULT_FILE = os.path.join(
    BASE_DIR,
    "results.xlsx"
)


# =========================================================
# TXT ФАЙЛ УНШИХ
# =========================================================

def read_file(filename):

    if not os.path.exists(filename):

        print("Файл олдсонгүй:")
        print(filename)

        return ""


    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1251"
    ]


    for encoding in encodings:

        try:

            with open(
                filename,
                "r",
                encoding=encoding
            ) as f:

                return f.read()

        except UnicodeDecodeError:

            pass


    return ""


# =========================================================
# ТЕКСТ ЦЭВЭРЛЭХ
# =========================================================

def clean_text(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# АСУУЛТ УНШИХ
# =========================================================

def read_questions(filename):

    text = read_file(filename)


    if not text:

        return []


    # Windows мөр
    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )


    lines = text.split("\n")


    # =====================================================
    # ЭХЛЭЛИЙН SPACE-УУДЫГ АРИЛГАНА
    # =====================================================

    lines = [
        line.strip()
        for line in lines
    ]


    # =====================================================
    # АСУУЛТЫН БЛОК ҮҮСГЭХ
    #
    # 1. ...
    # 2. ...
    # 3. ...
    #
    # =====================================================

    blocks = []

    current = []


    for line in lines:

        if not line:

            continue


        # Зөвхөн:
        # 1. Асуулт
        # 2. Асуулт
        # гэх мэт үндсэн асуултыг танина

        match = re.match(
            r"^(\d+)\.\s+(.+)",
            line
        )


        if match:

            # Өмнөх блок
            if current:

                blocks.append(
                    current
                )


            current = [line]

        else:

            if current:

                current.append(line)


    # Сүүлийн блок
    if current:

        blocks.append(
            current
        )


    questions = []


    # =====================================================
    # БЛОК БҮР
    # =====================================================

    for block in blocks:

        if len(block) < 3:

            continue


        first_line = block[0]


        # =================================================
        # АСУУЛТЫН ТЕКСТ
        # =================================================

        question_match = re.match(
            r"^\d+\.\s+(.+)",
            first_line
        )


        if not question_match:

            continue


        question_text = (
            question_match
            .group(1)
            .strip()
        )


        # =================================================
        # ЗӨВ ХАРИУЛТ
        # =================================================

        correct = None

        correct_position = -1


        for i, line in enumerate(block):

            match = re.search(
                r"Зөв\s*хариулт\s*:\s*([A-D])",
                line,
                re.IGNORECASE
            )


            if match:

                correct = (
                    match
                    .group(1)
                    .upper()
                )

                correct_position = i

                break


        # Зөв хариулт олдохгүй бол
        if not correct:

            continue


        # =================================================
        # A B C D СОНГОЛТ
        # =================================================

        answer_lines = block[
            1:correct_position
        ]


        options = {}

        current_letter = None


        for line in answer_lines:

            option_match = re.match(
                r"^([A-D])[\.\):]\s*(.*)",
                line,
                re.IGNORECASE
            )


            if option_match:

                letter = (
                    option_match
                    .group(1)
                    .upper()
                )


                value = (
                    option_match
                    .group(2)
                    .strip()
                )


                options[letter] = value

                current_letter = letter


            else:

                # Сонголтын текст олон мөртэй байвал
                if current_letter:

                    options[current_letter] += (
                        " " + line
                    )


        # =================================================
        # 3-ААС ДООШ СОНГОЛТ БОЛ БУРУУ
        # =================================================

        if len(options) < 3:

            continue


        # =================================================
        # ЗӨВ ХАРИУЛТ СОНГОЛТД БАЙГАА ЭСЭХ
        # =================================================

        if correct not in options:

            continue


        # =================================================
        # АСУУЛТ ҮҮСГЭХ
        # =================================================

        question = {

            "question":
                clean_text(
                    question_text
                ),

            "A":
                clean_text(
                    options.get(
                        "A",
                        ""
                    )
                ),

            "B":
                clean_text(
                    options.get(
                        "B",
                        ""
                    )
                ),

            "C":
                clean_text(
                    options.get(
                        "C",
                        ""
                    )
                ),

            "D":
                clean_text(
                    options.get(
                        "D",
                        ""
                    )
                ),

            "correct":
                correct

        }


        questions.append(
            question
        )


    # =====================================================
    # ID ӨГӨХ
    # =====================================================

    for i, question in enumerate(
        questions,
        start=1
    ):

        question["id"] = i


    print()
    print("=" * 60)
    print("Файл:", filename)
    print("Нийт зөв уншсан асуулт:", len(questions))
    print("=" * 60)


    return questions


# =========================================================
# НҮҮР
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# =========================================================
# ШАЛГАЛТ СОНГОХ
# =========================================================

@app.route(
    "/select_exam",
    methods=["POST"]
)
def select_exam():

    exam_type = request.form.get(
        "exam_type"
    )


    if exam_type not in EXAM_FILES:

        return redirect(
            url_for("index")
        )


    questions = read_questions(
        EXAM_FILES[exam_type]
    )


    # 10-аас дээш байх
    if len(questions) < QUESTION_COUNT:

        return render_template(
            "error.html",
            message=(
                f"{exam_type} шалгалтад "
                f"{len(questions)} асуулт танигдсан байна. "
                f"Хамгийн багадаа 10 асуулт "
                f"шаардлагатай."
            )
        )


    session["exam_type"] = exam_type


    return redirect(
        url_for("info")
    )


# =========================================================
# МЭДЭЭЛЭЛ ОРУУЛАХ
# =========================================================

@app.route("/info")
def info():

    exam_type = session.get(
        "exam_type"
    )


    if not exam_type:

        return redirect(
            url_for("index")
        )


    questions = read_questions(
        EXAM_FILES[exam_type]
    )


    return render_template(
        "info.html",

        exam_type=exam_type,

        total_questions=len(
            questions
        ),

        question_count=QUESTION_COUNT,

        exam_minutes=EXAM_MINUTES

    )


# =========================================================
# ШАЛГАЛТ ЭХЛҮҮЛЭХ
# =========================================================

@app.route(
    "/start",
    methods=["POST"]
)
def start():

    name = request.form.get(
        "name",
        ""
    ).strip()


    position = request.form.get(
        "position",
        ""
    ).strip()


    exam_type = session.get(
        "exam_type"
    )


    if not exam_type:

        return redirect(
            url_for("index")
        )


    if not name or not position:

        return redirect(
            url_for("info")
        )


    # =====================================================
    # БҮХ АСУУЛТ
    # =====================================================

    all_questions = read_questions(
        EXAM_FILES[exam_type]
    )


    if len(all_questions) < QUESTION_COUNT:

        return "Асуулт хүрэлцэхгүй байна."


    # =====================================================
    # САНАМСАРГҮЙ 10
    # =====================================================

    questions = random.sample(
        all_questions,
        QUESTION_COUNT
    )


    # =====================================================
    # SESSION
    # =====================================================

    session["name"] = name

    session["position"] = position

    session["questions"] = questions

    session["started"] = True


    return render_template(
        "exam.html",

        exam_type=exam_type,

        name=name,

        position=position,

        questions=questions,

        exam_minutes=EXAM_MINUTES

    )


# =========================================================
# ШАЛГАЛТ ДУУСГАХ
# =========================================================

@app.route(
    "/submit",
    methods=["POST"]
)
def submit():

    if not session.get(
        "started"
    ):

        return redirect(
            url_for("index")
        )


    name = session.get(
        "name",
        ""
    )


    position = session.get(
        "position",
        ""
    )


    exam_type = session.get(
        "exam_type",
        ""
    )


    questions = session.get(
        "questions",
        []
    )


    # =====================================================
    # ОНОО
    # =====================================================

    score = 0


    for question in questions:

        question_id = str(
            question["id"]
        )


        answer = request.form.get(
            "q_" + question_id,
            ""
        ).upper()


        correct = question[
            "correct"
        ].upper()


        if answer == correct:

            score += 1


    total = len(
        questions
    )


    # =====================================================
    # ХУВЬ
    # =====================================================

    percentage = round(
        score / total * 100
    )


    # =====================================================
    # ТЭНЦСЭН
    # =====================================================

    if score >= PASS_SCORE:

        result = "ТЭНЦСЭН"

    else:

        result = "ТЭНЦЭЭГҮЙ"


    # =====================================================
    # EXCEL
    # =====================================================

    new_row = pd.DataFrame([{

        "Огноо":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

         "Шалгалтын төрөл":
        exam_type,

        "Овог нэр":
            name,

        "Албан тушаал":
            position,

        "Авсан оноо":
            score,

        "Нийт оноо":
            total

    }])


    if os.path.exists(
        RESULT_FILE
    ):

        try:

            old_data = pd.read_excel(
                RESULT_FILE
            )

            data = pd.concat(
                [
                    old_data,
                    new_row
                ],
                ignore_index=True
            )

        except Exception:

            data = new_row

    else:

        data = new_row


    # =====================================================
    # БАГАНА
    # =====================================================

    data = data[
        [
            "Огноо",
            "Шалгалтын төрөл",
            "Овог нэр",
            "Албан тушаал",
            "Авсан оноо",
            "Нийт оноо"
        ]
    ]


    data.to_excel(
        RESULT_FILE,
        index=False
    )


    # =====================================================
    # SESSION ЦЭВЭРЛЭХ
    # =====================================================

    session.clear()


    # =====================================================
    # ҮР ДҮН
    # =====================================================

    return render_template(
        "result.html",

        name=name,

        position=position,

        exam_type=exam_type,

        score=score,

        total=total,

        percentage=percentage,

        result=result,

        pass_score=PASS_SCORE

    )


# =========================================================
# ERROR PAGE
# =========================================================

@app.route("/error")
def error():

    return render_template(
        "error.html",
        message="Алдаа гарлаа."
    )


# =========================================================
# SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )