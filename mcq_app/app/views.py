import json
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
from .models import User




# def login_page(request):
#     if request.method == "POST":
#         email = request.POST.get("email")
#         password = request.POST.get("password")

#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             messages.error(request, "Invalid email or password")
#             return render(request, "login1.html")

#         # Manual password check (since you're storing plain text)
#         if user.password == password:
#             request.session['user_id'] = user.id
#             request.session['user_email'] = user.email
#             return redirect("generate_mcq")
#         else:
#             messages.error(request, "Invalid email or password")
#             return render(request, "login1.html")

#     return render(request, "login1.html")

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
            return redirect("generate_mcq")    
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





def generate_mcq(request):
    if request.method == "POST":
        form = InputForm(request.POST, request.FILES)
        if form.is_valid():
            context = clean_text(form.cleaned_data["context"]).strip()
            pdfile = form.cleaned_data["pdf_file"]
            num_keywords = int(form.cleaned_data["num_keywords"])
            option_1 = form.cleaned_data["option_1"]
            option_2 = form.cleaned_data["option_2"]
            option_3 = form.cleaned_data["option_3"]

            if not context and pdfile:
                reader = PyPDF2.PdfReader(pdfile, strict=False)
                context = "".join(page.extract_text() or "" for page in reader.pages)

            # Step 1: Token check
            if len(context) > 2500:
                from apps.questionGeneration import question_tokenizer
                tokenized_length = len(question_tokenizer.tokenize(context))
            else:
                tokenized_length = 0

            # Step 2: Chunking
            chunks = (
                keyword_centric_chunking(context, question_tokenizer)
                if tokenized_length > 500
                else [context]
            )

            # Step 3: Generate MCQs
            all_keywords, questions_dict, distractors_dict = [], {}, {}
            for chunk in chunks:
                keywords = extract_keywords_based_on_option(option_2, chunk, num_keywords)
                keywords = remove_duplicates(keywords)
                all_keywords.extend(keywords)

                q_dict, d_dict = generate_questions_and_distractors(option_1, option_3, chunk, keywords)
                questions_dict.update(q_dict)
                distractors_dict.update(d_dict)

            for keyword in all_keywords:
                distractors_dict[keyword] = remove_distractors_duplicate_with_correct_answer(
                    keyword, distractors_dict[keyword]
                )

            mcq_list = create_mcq_list(all_keywords, questions_dict, distractors_dict)

            if request.user.is_authenticated:
                MCQ.objects.create(user=request.user, mcqs=mcq_list)
            else:
                request.session['mcqs'] = json.dumps(mcq_list)

                

            return render(request, "result.html", {"context": context, "mcq_list": mcq_list})

    return render(request, "index.html", {"form": InputForm(), "user": request.user})


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


# ---------- Utility Functions ----------
def extract_keywords_based_on_option(option, context, num_keywords):
    if option == 'spacy':
        from apps.keywordExtraction import get_keywords
        from apps.summarization import summarizer, summary_model, summary_tokenizer
        summary_text = summarizer(context, summary_model, summary_tokenizer)
        return get_keywords(context, summary_text, num_keywords)
    elif option == 'rake':
        from apps.rakeKeyword import get_keywords_rake
        return get_keywords_rake(context, num_keywords)
    elif option == 'distilbert':
        from apps.distilBERTKeyword import extract_keywords
        return extract_keywords(context, num_keywords=num_keywords)
    return []


def generate_questions_and_distractors(option_1, option_3, context, keywords):
    questions_dict, distractors_dict = {}, {}

    if option_1 == "general":
        from apps.questionGeneration import get_question, question_model, question_tokenizer
    elif option_1 == "t5-llm":
        from apps.question_gen_science import get_question_science, question_model, question_tokenizer

    if option_3 == "t5-llm":
        from apps.t5distractors import dis_model, dis_tokenizer, get_distractors_t5
    elif option_3 == "llama":
        from apps.llama_distractors import generate_distractors_llama
    elif option_3 == "s2v":
        from apps.s2vdistractors import generate_distractors, s2v

    for keyword in keywords:
        if option_1 == "general":
            question = get_question(context, keyword, question_model, question_tokenizer)
        elif option_1 == "t5-llm":
            question = get_question_science(context, keyword, question_model, question_tokenizer)
        else:
            question = f"What is {keyword}?"

        if option_3 == "t5-llm":
            distractors = get_distractors_t5(question=question, answer=keyword, context=context, model=dis_model, tokenizer=dis_tokenizer)
        elif option_3 == "llama":
            distractors = generate_distractors_llama(context, question, keyword)
        elif option_3 == "s2v":
            distractors = generate_distractors(keyword, s2v)
        else:
            distractors = []

        questions_dict[keyword] = question
        distractors_dict[keyword] = distractors

    return questions_dict, distractors_dict


def create_mcq_list(keywords, questions_dict, distractors_dict):
    mcq_list = []
    for keyword in keywords:
        question = questions_dict[keyword]
        correct_answer = keyword
        distractors = distractors_dict[keyword]
        options = [correct_answer] + distractors
        random.shuffle(options)
        mcq_list.append({"question": question, "options": options, "correct_answer": correct_answer})
    return mcq_list


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
    if request.user.is_authenticated:
        mcq_entries = MCQ.objects.filter(user=request.user).order_by('-created_at')
        for entry in mcq_entries:
            history_data.append({
                "id": entry.id,
                "mcqs": entry.get_mcqs(),
                "created_at": entry.created_at,
            })
    else:
        mcqs = json.loads(request.session.get('mcqs', '[]'))
        if mcqs:
            history_data.append({"id": None, "mcqs": mcqs, "created_at": None})
    return render(request, "history.html", {"history_data": history_data})


def delete_history(request, entry_id):
    if request.user.is_authenticated:
        mcq_entry = get_object_or_404(MCQ, id=entry_id, user=request.user)
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
    return render(request, "quesGens/profile.html")

def test_results(request):
    return render(request, "quesGens/test_results.html")
