import json
from .forms import UserUpdateForm, ProfileUpdateForm

import random
from io import BytesIO
import PyPDF2
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .forms import InputForm
from .models import MCQ

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import User,MCQ,MCQHistory

from django.conf import settings



import json
from django.shortcuts import render
from PyPDF2 import PdfReader
from groq import Groq
from django.conf import settings
import os


# Load Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


import re

from django.shortcuts import render


from django.shortcuts import render
from django.conf import settings
from groq import Groq
import re

# def generate_mcq(request):
#     mcq_list = []
#     if request.method == "POST":
#         text = request.POST.get("context", "")
#         client = Groq(api_key=settings.GROQ_API_KEY)

#         try:
#             chat_completion = client.chat.completions.create(
#                 model = "llama-3.3-70b-versatile"
# ,  # active model
#                 messages=[
#                     {"role": "system", "content": "You are an MCQ generator."},
#                     {"role": "user", "content": f"Generate 3 MCQs from this text: {text}\nInclude the correct answer in a line starting with 'Answer:' after options."}
#                 ]
#             )

#             raw = chat_completion.choices[0].message.content
#             # print(raw)  # for debugging

#             # Flexible parser
#             questions = re.split(r"Question \d+:|Q\d+:", raw)
#             for q in questions:
#                 q = q.strip()
#                 if not q:
#                     continue
#                 lines = q.split("\n")
#                 question_text = lines[0].strip()
#                 options = []
#                 answer = ""
#                 for line in lines[1:]:
#                     line = line.strip()
#                     if line.lower().startswith("answer:"):
#                         answer = line.split(":", 1)[1].strip()
#                     elif line:
#                         options.append(line)
#                 if question_text:
#                     mcq_list.append({
#                         "question": question_text,
#                         "options": options,
#                         "correct_answer": answer if answer else (options[-1] if options else "")
#                     })

#         except Exception as e:
#             mcq_list = [{"question": f"Error: {str(e)}", "options": [], "correct_answer": ""}]

#     return render(request, "result.html", {"mcq_list": mcq_list})


client = Groq(api_key=settings.GROQ_API_KEY)  # global client for helper

def generate_mcq(request):
    mcq_list = []
    input_text = ""

    if request.method == "POST":
        input_text = request.POST.get("context", "").strip()

        try:
            # Prompt AI to return JSON format
            prompt = (
                f"Generate 3 MCQs from this text:\n{input_text}\n\n"
                f"Return output ONLY in this JSON format:\n"
                f"[{{\"question\": \"\", \"options\": [], \"answer\": \"\"}}]\n"
                f"Options must include at least 3 choices (A, B, C). Correct answer must match one of the options."
            )

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )

            raw = response.choices[0].message.content.strip()

            # Parse JSON safely
            try:
                mcq_list = json.loads(raw)
            except json.JSONDecodeError:
                raw_fixed = raw.replace("'", '"')
                mcq_list = json.loads(raw_fixed)

            # Standardize options and correct answer
            for mcq in mcq_list:
                options_raw = mcq.get('options', [])
                if isinstance(options_raw, str):
                    options = [opt.strip() for opt in options_raw.splitlines() if opt.strip()]
                else:
                    options = [opt.strip() for opt in options_raw if opt.strip()]

                answer = mcq.get('answer', '').strip()
                if answer and answer not in options:
                    options.append(answer)

                mcq['options'] = options
                mcq['correct_answer'] = answer if answer else (options[-1] if options else "")

            MCQHistory.objects.create(
                user_id=request.session.get("user_id"),  # ← THIS IS THE FIX
                input_text=input_text,
                mcq_data=json.dumps(mcq_list)           # ensure it’s saved as JSON text
            )

            print("Saving MCQ History:", input_text, mcq_list)


        except Exception as e:
            mcq_list = [{"question": f"Error: {str(e)}", "options": [], "correct_answer": ""}]

    history = MCQHistory.objects.filter(user=request.user).order_by('-created_at') if request.user.is_authenticated else []

    return render(request, "result.html", {"mcq_list": mcq_list, "input_text": input_text, "history": history})


def generate_ai_mcqs(text, n=5):
    prompt = (
        f"Generate {n} high-quality MCQs from the following content.\n"
        f"Return JSON ONLY in this exact format:\n"
        f"[{{\"question\": \"\", \"options\": [], \"answer\": \"\"}}]\n\n"
        f"CONTENT:\n{text}\n"
    )

    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content.strip()

    try:
        mcqs = json.loads(content)
    except:
        content = content.replace("'", '"')
        mcqs = json.loads(content)

    return mcqs







def login_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email does not exist.")
            return redirect("login")

        if check_password(password, user.password):
            request.session["user_id"] = user.id
            return redirect("/")    
        else:
            messages.error(request, "Incorrect password.")
            return redirect("login")

    return render(request, "login1.html")


def register_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        hashed_pass = make_password(password)
        User.objects.create(email=email, password=hashed_pass)

        messages.success(request, "Account created successfully.")
        return redirect("login")

    return render(request, "reg.html")

def logout(request):
    request.session.flush()
    return redirect("login")






# def generate_basic_mcqs(text):
#     import random
#     sentences = [s.strip() for s in text.split(".") if s.strip()][:5]

#     mcqs = []
#     for s in sentences:
#         q = f"What does the text say about: '{s[:20]}...'?"
#         correct = s
#         distractors = [
#             "An unrelated idea.",
#             "A partially incorrect detail.",
#             "An opposite meaning."
#         ]

#         options = [correct] + distractors
#         random.shuffle(options)

#         mcqs.append({
#             "question": q,
#             "options": options,
#             "answer": correct,
#         })

#     return mcqs




def result(request):
    if request.user.is_authenticated:
        latest_batch = MCQ.objects.latest('created_at')
        mcq_list = latest_batch.get_mcqs()
    else:
        mcq_list = json.loads(request.session.get('mcqs', '[]'))
    return render(request, 'result.html', {"mcq_list": mcq_list})


def download_pdf(request):
    mcq_list = json.loads(request.session.get('mcqs', '[]'))
    if not mcq_list:
        return render(request, "quesGens/error.html", {"error": "No MCQs found to download as PDF."})

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y_position = height - 50

    for mcq in mcq_list:
        p.drawString(100, y_position, f"Question: {mcq['question']}")
        y_position -= 20
        for option in mcq['options']:
            p.drawString(120, y_position, f"- {option}")
            y_position -= 15
        y_position -= 30

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="mcqs.pdf")


# # ---------- Utility Functions ----------
# def extract_keywords_based_on_option(option, context, num_keywords):
#     if option == 'spacy':
#         from apps.keywordExtraction import get_keywords
#         from apps.summarization import summarizer, summary_model, summary_tokenizer
#         summary_text = summarizer(context, summary_model, summary_tokenizer)
#         return get_keywords(context, summary_text, num_keywords)
#     elif option == 'rake':
#         from apps.rakeKeyword import get_keywords_rake
#         return get_keywords_rake(context, num_keywords)
#     elif option == 'distilbert':
#         from apps.distilBERTKeyword import extract_keywords
#         return extract_keywords(context, num_keywords=num_keywords)
#     return []


# def generate_questions_and_distractors(option_1, option_3, context, keywords):
#     questions_dict, distractors_dict = {}, {}

#     if option_1 == "general":
#         from apps.questionGeneration import get_question, question_model, question_tokenizer
#     elif option_1 == "t5-llm":
#         from apps.question_gen_science import get_question_science, question_model, question_tokenizer

#     if option_3 == "t5-llm":
#         from apps.t5distractors import dis_model, dis_tokenizer, get_distractors_t5
#     elif option_3 == "llama":
#         from apps.llama_distractors import generate_distractors_llama
#     elif option_3 == "s2v":
#         from apps.s2vdistractors import generate_distractors, s2v

#     for keyword in keywords:
#         if option_1 == "general":
#             question = get_question(context, keyword, question_model, question_tokenizer)
#         elif option_1 == "t5-llm":
#             question = get_question_science(context, keyword, question_model, question_tokenizer)
#         else:
#             question = f"What is {keyword}?"

#         if option_3 == "t5-llm":
#             distractors = get_distractors_t5(question=question, answer=keyword, context=context, model=dis_model, tokenizer=dis_tokenizer)
#         elif option_3 == "llama":
#             distractors = generate_distractors_llama(context, question, keyword)
#         elif option_3 == "s2v":
#             distractors = generate_distractors(keyword, s2v)
#         else:
#             distractors = []

#         questions_dict[keyword] = question
#         distractors_dict[keyword] = distractors

#     return questions_dict, distractors_dict


# def create_mcq_list(keywords, questions_dict, distractors_dict):
#     mcq_list = []
#     for keyword in keywords:
#         question = questions_dict[keyword]
#         correct_answer = keyword
#         distractors = distractors_dict[keyword]
#         options = [correct_answer] + distractors
#         random.shuffle(options)
#         mcq_list.append({"question": question, "options": options, "correct_answer": correct_answer})
#     return mcq_list


# ---------- User Auth Views ----------
@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            return JsonResponse({'success': False, 'message': 'Passwords do not match'})
        if User.objects.filter(username=email).exists():
            return JsonResponse({'success': False, 'message': 'Email already in use'})
        user = User.objects.create_user(username=email, email=email, password=password)
        login(request, user)
        return JsonResponse({'success': True, 'message': 'Registration successful'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return JsonResponse({'success': True, 'message': 'Login successful'})
        return JsonResponse({'success': False, 'message': 'Invalid credentials'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def logout_view(request):
    logout(request)
    return redirect('generate_mcq')


def test(request):
    latest_batch = MCQ.objects.latest('created_at')
    mcq_list = latest_batch.get_mcqs()
    if request.method == 'POST':
        score = sum(1 for i, mcq in enumerate(mcq_list) if request.POST.get(f'option_{i}') == mcq["correct_answer"])
        return render(request, 'quesGens/test_results.html', {'score': score, 'total': len(mcq_list)})
    return render(request, 'quesGens/test.html', {'mc_list': mcq_list})


def history(request):
    history_data = []

    user_id = request.session.get('user_id', None)

    if user_id:
        mcq_entries = MCQHistory.objects.filter(user_id=user_id).order_by('-created_at')
        for entry in mcq_entries:
            history_data.append({
                "id": entry.id,
                "input_text": entry.input_text,
                "mcqs": entry.get_mcqs(),
                "created_at": entry.created_at,
            })
    else:
        mcqs = request.session.get('mcqs', [])
        input_text = request.session.get('input_text', '')
        if mcqs:
            history_data.append({
                "id": None,
                "input_text": input_text,
                "mcqs": mcqs,
                "created_at": None
            })
    print("=== HISTORY VIEW EXECUTED ===")
    print("history_data =", history_data)
    

    return render(request, "history.html", {"history_data": history_data})


def delete_history(request, entry_id):
    user_id = request.session.get("user_id")

    if user_id:
        mcq_entry = get_object_or_404(MCQHistory, id=entry_id, user_id=user_id)
        mcq_entry.delete()
    else:
        request.session.pop('mcqs', None)

    return redirect('history')


def about(request):
    return render(request, 'about.html')


def quiz(request):
    return render(request, 'quiz.html')

def is_logged_in(request):
    return JsonResponse({'logged_in': request.user.is_authenticated})

def landing(request):
    return render(request, "index.html")

def profile(request):
    return render(request, 'profile.html')

def test_results(request):
    return render(request, "quesGens/test_results.html")
