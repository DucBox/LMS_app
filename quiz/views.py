from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.decorators import lecturer_required
from .forms import (
    EssayForm,
    MCQuestionForm,
    MCQuestionFormSet,
    QuestionForm,
    QuizAddForm,
)
from .models import (
    Course,
    EssayQuestion,
    MCQuestion,
    Progress,
    Question,
    Quiz,
    Sitting,
)


# ########################################################
# Quiz Views
# ########################################################

@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizCreateView(CreateView):
    model = Quiz
    form_class = QuizAddForm
    template_name = "quiz/quiz_form.html"
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.decorators import lecturer_required
from .forms import (
    EssayForm,
    MCQuestionForm,
    MCQuestionFormSet,
    QuestionForm,
    QuizAddForm,
)
from .models import (
    Course,
    EssayQuestion,
    MCQuestion,
    Progress,
    Question,
    Quiz,
    Sitting,
)


# ########################################################
# Quiz Views
# ########################################################

@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizCreateView(CreateView):
    model = Quiz
    form_class = QuizAddForm
    template_name = "quiz/quiz_form.html"

    def get_initial(self):
        initial = super().get_initial()
        course = get_object_or_404(Course, slug=self.kwargs["slug"])
        initial["course"] = course
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
        return context

    def form_valid(self, form):
        form.instance.course = get_object_or_404(Course, slug=self.kwargs["slug"])
        with transaction.atomic():
            self.object = form.save()
            # Chuyển hướng sang trang tạo câu hỏi
            return redirect(
                "mc_create", slug=self.kwargs["slug"], quiz_id=self.object.id
            )


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizUpdateView(UpdateView):
    model = Quiz
    form_class = QuizAddForm
    template_name = "quiz/quiz_form.html"

    def get_object(self, queryset=None):
        return get_object_or_404(Quiz, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            return redirect("quiz_index", self.kwargs["slug"])


@login_required
@lecturer_required
def quiz_delete(request, slug, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    quiz.delete()
    messages.success(request, "Quiz successfully deleted.")
    return redirect("quiz_index", slug=slug)


@login_required
def quiz_list(request, slug):
    course = get_object_or_404(Course, slug=slug)
    quizzes = Quiz.objects.filter(course=course).order_by("-timestamp")

    # Tính số lần làm bài và số lần còn lại
    quizzes_with_attempts = []
    for quiz in quizzes:
        attempts = quiz.sitting_set.filter(user=request.user).count()
        remaining_attempts = max(0, quiz.max_attempts - attempts) if not quiz.single_attempt else 0
        quizzes_with_attempts.append({
            "quiz": quiz,
            "attempts": attempts,
            "remaining_attempts": remaining_attempts,
        })

    return render(
        request, "quiz/quiz_list.html", {"quizzes_with_attempts": quizzes_with_attempts, "course": course}
    )



# ########################################################
# Multiple Choice Question Views
# ########################################################


@method_decorator([login_required, lecturer_required], name="dispatch")
class MCQuestionCreate(CreateView):
    model = MCQuestion
    form_class = MCQuestionForm
    template_name = "quiz/mcquestion_form.html"

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs["quiz"] = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])
    #     return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
        context["quiz_obj"] = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])
        context["quiz_questions_count"] = Question.objects.filter(
            quiz=self.kwargs["quiz_id"]
        ).count()
        if self.request.method == "POST":
            context["formset"] = MCQuestionFormSet(self.request.POST)
        else:
            context["formset"] = MCQuestionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            with transaction.atomic():
                # Save the MCQuestion instance without committing to the database yet
                self.object = form.save(commit=False)
                self.object.save()

                # Retrieve the Quiz instance
                quiz = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])

                # set the many-to-many relationship
                self.object.quiz.add(quiz)

                # Save the formset (choices for the question)
                formset.instance = self.object
                formset.save()

                if "another" in self.request.POST:
                    return redirect(
                        "mc_create",
                        slug=self.kwargs["slug"],
                        quiz_id=self.kwargs["quiz_id"],
                    )
                return redirect("quiz_index", slug=self.kwargs["slug"])
        else:
            return self.form_invalid(form)


# ########################################################
# Quiz Progress and Marking Views
# ########################################################


@method_decorator([login_required], name="dispatch")
class QuizUserProgressView(TemplateView):
    template_name = "quiz/progress.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        progress, _ = Progress.objects.get_or_create(user=self.request.user)
        context["cat_scores"] = progress.list_all_cat_scores
        context["exams"] = progress.show_exams()
        context["exams_counter"] = context["exams"].count()
        return context


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizMarkingList(ListView):
    model = Sitting
    template_name = "quiz/quiz_marking_list.html"

    def get_queryset(self):
        queryset = Sitting.objects.filter(complete=True)
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                quiz__course__allocated_course__lecturer__pk=self.request.user.id
            )
        quiz_filter = self.request.GET.get("quiz_filter")
        if quiz_filter:
            queryset = queryset.filter(quiz__title__icontains=quiz_filter)
        user_filter = self.request.GET.get("user_filter")
        if user_filter:
            queryset = queryset.filter(user__username__icontains=user_filter)
        return queryset


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizMarkingDetail(DetailView):
    model = Sitting
    template_name = "quiz/quiz_marking_detail.html"

    def post(self, request, *args, **kwargs):
        sitting = self.get_object()
        question_id = request.POST.get("qid")
        if question_id:
            question = Question.objects.get_subclass(id=int(question_id))
            if int(question_id) in sitting.get_incorrect_questions:
                sitting.remove_incorrect_question(question)
            else:
                sitting.add_incorrect_question(question)
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["questions"] = self.object.get_questions(with_answers=True)
        return context


# ########################################################
# Quiz Taking View
# ########################################################


# @method_decorator([login_required], name="dispatch")
# class QuizTake(FormView):
#     form_class = QuestionForm
#     template_name = "quiz/question.html"
#     result_template_name = "quiz/result.html"

#     def dispatch(self, request, *args, **kwargs):
#         self.quiz = get_object_or_404(Quiz, slug=self.kwargs["slug"])
#         self.course = get_object_or_404(Course, pk=self.kwargs["pk"])
#         if not Question.objects.filter(quiz=self.quiz).exists():
#             messages.warning(request, "This quiz has no questions available.")
#             return redirect("quiz_index", slug=self.course.slug)

#         # Kiểm tra số lần làm bài
#         attempts = Sitting.objects.filter(
#             user=request.user, quiz=self.quiz, course=self.course
#         ).count()
#         if attempts >= self.quiz.max_attempts:
#             messages.info(
#                 request,
#                 f"You have reached the maximum number of {self.quiz.max_attempts} attempts for this quiz.",
#             )
#             return redirect("quiz_index", slug=self.course.slug)

#         self.sitting = Sitting.objects.user_sitting(
#             request.user, self.quiz, self.course
#         )
#         if not self.sitting:
#             messages.info(
#                 request,
#                 "You have already completed this quiz. Only one attempt is permitted.",
#             )
#             return redirect("quiz_index", slug=self.course.slug)

#         # Check if this is the last attempt
#         self.total_attempts = attempts + 1
#         self.show_answers = self.total_attempts >= self.quiz.max_attempts

#         self.question = self.sitting.get_first_question()
#         self.progress = self.sitting.progress()

#         return super().dispatch(request, *args, **kwargs)

#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs["question"] = self.question
#         return kwargs

#     def get_form_class(self):
#         if isinstance(self.question, EssayQuestion):
#             return EssayForm
#         return self.form_class

#     def form_valid(self, form):
#         self.form_valid_user(form)
#         if not self.sitting.get_first_question():
#             return self.final_result_user()
#         return super().get(self.request)

#     def form_valid_user(self, form):
#         progress, _ = Progress.objects.get_or_create(user=self.request.user)
#         guess = form.cleaned_data["answers"]
#         is_correct = self.question.check_if_correct(guess)

#         if is_correct:
#             self.sitting.add_to_score(1)
#             progress.update_score(self.question, 1, 1)
#         else:
#             self.sitting.add_incorrect_question(self.question)
#             progress.update_score(self.question, 0, 1)

#         if not self.quiz.answers_at_end:
#             self.previous = {
#                 "previous_answer": guess,
#                 "previous_outcome": is_correct,
#                 "previous_question": self.question,
#                 "answers": self.question.get_choices(),
#                 "question_type": {self.question.__class__.__name__: True},
#             }
#         else:
#             self.previous = {}

#         self.sitting.add_user_answer(self.question, guess)
#         self.sitting.remove_first_question()

#         # Update self.question and self.progress for the next question
#         self.question = self.sitting.get_first_question()
#         self.progress = self.sitting.progress()

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context["question"] = self.question
#         context["quiz"] = self.quiz
#         context["course"] = self.course
#         context["show_answers"] = self.show_answers  # Truyền giá trị để kiểm soát hiển thị
#         if hasattr(self, "previous"):
#             context["previous"] = self.previous
#         if hasattr(self, "progress"):
#             context["progress"] = self.progress
#         if self.question.figure:
#             print(f"Question Image URL: {self.question.figure.url}")
#         else:
#             print("No Image for this question.")
#         return context

#     def final_result_user(self):
#         print("DEBUG - Final Result User Function Called")
#         self.sitting.mark_quiz_complete()
#         questions = self.sitting.get_questions(with_answers=True)
        
#         # Xử lý từng câu hỏi để kiểm tra đáp án đúng/sai
#         processed_questions = []
#         for question in questions:
#             user_answer = question.user_answer
#             correct_choices = question.get_choices_correct()
#             is_correct = question.check_if_correct(user_answer) if user_answer else False
            
#             # Debug thông tin từng câu hỏi
#             print(f"DEBUG - Question ID: {question.id}")
#             print(f"Question: {question.content}")
#             print(f"User Answer: {user_answer}")
#             print(f"Is Correct: {is_correct}")
#             print(f"Correct Answer: {correct_answer}")
            
#             processed_questions.append({
#                 'question': question,
#                 'user_answer': user_answer,
#                 'is_correct': is_correct,
#                 'correct_answer': correct_answer,
#                 'explanation': question.explanation,
#             })
        
#         results = {
#             "course": self.course,
#             "quiz": self.quiz,
#             "score": self.sitting.get_current_score,
#             "max_score": self.sitting.get_max_score,
#             "percent": self.sitting.get_percent_correct,
#             "sitting": self.sitting,
#             "questions": processed_questions,
#             "show_answers": self.show_answers,  # Kiểm soát hiển thị đáp án
#         }

#         return render(self.request, self.result_template_name, results)
#     def get_initial(self):
#         initial = super().get_initial()
#         course = get_object_or_404(Course, slug=self.kwargs["slug"])
#         initial["course"] = course
#         return initial

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
#         return context

#     def form_valid(self, form):
#         form.instance.course = get_object_or_404(Course, slug=self.kwargs["slug"])
#         with transaction.atomic():
#             self.object = form.save()
#             # Chuyển hướng sang trang tạo câu hỏi
#             return redirect(
#                 "mc_create", slug=self.kwargs["slug"], quiz_id=self.object.id
#             )


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizUpdateView(UpdateView):
    model = Quiz
    form_class = QuizAddForm
    template_name = "quiz/quiz_form.html"

    def get_object(self, queryset=None):
        return get_object_or_404(Quiz, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            return redirect("quiz_index", self.kwargs["slug"])


@login_required
@lecturer_required
def quiz_delete(request, slug, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    quiz.delete()
    messages.success(request, "Quiz successfully deleted.")
    return redirect("quiz_index", slug=slug)


@login_required
def quiz_list(request, slug):
    course = get_object_or_404(Course, slug=slug)
    quizzes = Quiz.objects.filter(course=course).order_by("-timestamp")

    # Tính số lần làm bài và số lần còn lại
    quizzes_with_attempts = []
    for quiz in quizzes:
        attempts = quiz.sitting_set.filter(user=request.user).count()
        remaining_attempts = max(0, quiz.max_attempts - attempts) if not quiz.single_attempt else 0
        quizzes_with_attempts.append({
            "quiz": quiz,
            "attempts": attempts,
            "remaining_attempts": remaining_attempts,
        })

    return render(
        request, "quiz/quiz_list.html", {"quizzes_with_attempts": quizzes_with_attempts, "course": course}
    )



# ########################################################
# Multiple Choice Question Views
# ########################################################


@method_decorator([login_required, lecturer_required], name="dispatch")
class MCQuestionCreate(CreateView):
    model = MCQuestion
    form_class = MCQuestionForm
    template_name = "quiz/mcquestion_form.html"

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs["quiz"] = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])
    #     return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(Course, slug=self.kwargs["slug"])
        context["quiz_obj"] = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])
        context["quiz_questions_count"] = Question.objects.filter(
            quiz=self.kwargs["quiz_id"]
        ).count()
        if self.request.method == "POST":
            context["formset"] = MCQuestionFormSet(self.request.POST)
        else:
            context["formset"] = MCQuestionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            with transaction.atomic():
                # Save the MCQuestion instance without committing to the database yet
                self.object = form.save(commit=False)
                self.object.save()
                if self.object.figure:
                    print(f"Uploaded Image Path: {self.object.figure.path}")  # Full path
                    print(f"Uploaded Image URL: {self.object.figure.url}")   # Relative URL
                else:
                    print("No image uploaded")
                # Retrieve the Quiz instance
                quiz = get_object_or_404(Quiz, id=self.kwargs["quiz_id"])

                # set the many-to-many relationship
                self.object.quiz.add(quiz)

                # Save the formset (choices for the question)
                formset.instance = self.object
                formset.save()

                if "another" in self.request.POST:
                    return redirect(
                        "mc_create",
                        slug=self.kwargs["slug"],
                        quiz_id=self.kwargs["quiz_id"],
                    )
                return redirect("quiz_index", slug=self.kwargs["slug"])
        else:
            return self.form_invalid(form)


# ########################################################
# Quiz Progress and Marking Views
# ########################################################


@method_decorator([login_required], name="dispatch")
class QuizUserProgressView(TemplateView):
    template_name = "quiz/progress.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        progress, _ = Progress.objects.get_or_create(user=self.request.user)
        context["cat_scores"] = progress.list_all_cat_scores
        context["exams"] = progress.show_exams()
        context["exams_counter"] = context["exams"].count()
        return context


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizMarkingList(ListView):
    model = Sitting
    template_name = "quiz/quiz_marking_list.html"

    def get_queryset(self):
        queryset = Sitting.objects.filter(complete=True)
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                quiz__course__allocated_course__lecturer__pk=self.request.user.id
            )
        quiz_filter = self.request.GET.get("quiz_filter")
        if quiz_filter:
            queryset = queryset.filter(quiz__title__icontains=quiz_filter)
        user_filter = self.request.GET.get("user_filter")
        if user_filter:
            queryset = queryset.filter(user__username__icontains=user_filter)
        return queryset


@method_decorator([login_required, lecturer_required], name="dispatch")
class QuizMarkingDetail(DetailView):
    model = Sitting
    template_name = "quiz/quiz_marking_detail.html"

    def post(self, request, *args, **kwargs):
        sitting = self.get_object()
        question_id = request.POST.get("qid")
        if question_id:
            question = Question.objects.get_subclass(id=int(question_id))
            if int(question_id) in sitting.get_incorrect_questions:
                sitting.remove_incorrect_question(question)
            else:
                sitting.add_incorrect_question(question)
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["questions"] = self.object.get_questions(with_answers=True)
        return context


# ########################################################
# Quiz Taking View
# ########################################################


@method_decorator([login_required], name="dispatch")
class QuizTake(FormView):
    form_class = QuestionForm
    template_name = "quiz/question.html"
    result_template_name = "quiz/result.html"

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, slug=self.kwargs["slug"])
        self.course = get_object_or_404(Course, pk=self.kwargs["pk"])
        if not Question.objects.filter(quiz=self.quiz).exists():
            messages.warning(request, "This quiz has no questions available.")
            return redirect("quiz_index", slug=self.course.slug)

        # Kiểm tra số lần làm bài
        attempts = Sitting.objects.filter(
            user=request.user, quiz=self.quiz, course=self.course
        ).count()
        if attempts >= self.quiz.max_attempts:
            messages.info(
                request,
                f"You have reached the maximum number of {self.quiz.max_attempts} attempts for this quiz.",
            )
            return redirect("quiz_index", slug=self.course.slug)

        self.sitting = Sitting.objects.user_sitting(
            request.user, self.quiz, self.course
        )
        if not self.sitting:
            messages.info(
                request,
                "You have already completed this quiz. Only one attempt is permitted.",
            )
            return redirect("quiz_index", slug=self.course.slug)

        # Check if this is the last attempt
        self.total_attempts = attempts + 1
        self.show_answers = self.total_attempts >= self.quiz.max_attempts

        self.question = self.sitting.get_first_question()
        self.progress = self.sitting.progress()

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["question"] = self.question
        return kwargs

    def get_form_class(self):
        if isinstance(self.question, EssayQuestion):
            return EssayForm
        return self.form_class

    def form_valid(self, form):
        self.form_valid_user(form)
        if not self.sitting.get_first_question():
            return self.final_result_user()
        return super().get(self.request)

    def form_valid_user(self, form):
        progress, _ = Progress.objects.get_or_create(user=self.request.user)
        guess = form.cleaned_data["answers"]
        is_correct = self.question.check_if_correct(guess)

        if is_correct:
            self.sitting.add_to_score(1)
            progress.update_score(self.question, 1, 1)
        else:
            self.sitting.add_incorrect_question(self.question)
            progress.update_score(self.question, 0, 1)

        if not self.quiz.answers_at_end:
            self.previous = {
                "previous_answer": guess,
                "previous_outcome": is_correct,
                "previous_question": self.question,
                "answers": self.question.get_choices(),
                "question_type": {self.question.__class__.__name__: True},
            }
        else:
            self.previous = {}

        self.sitting.add_user_answer(self.question, guess)
        self.sitting.remove_first_question()

        # Update self.question and self.progress for the next question
        self.question = self.sitting.get_first_question()
        self.progress = self.sitting.progress()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["question"] = self.question
        context["quiz"] = self.quiz
        context["course"] = self.course
        context["show_answers"] = self.show_answers  # Truyền giá trị để kiểm soát hiển thị
        if hasattr(self, "previous"):
            context["previous"] = self.previous
        if hasattr(self, "progress"):
            context["progress"] = self.progress
        return context

    def final_result_user(self):
        print("DEBUG - Final Result User Function Called")
        self.sitting.mark_quiz_complete()
        questions = self.sitting.get_questions(with_answers=True)
        
        # Xử lý từng câu hỏi để kiểm tra đáp án đúng/sai
        processed_questions = []
        for question in questions:
            user_answer = question.user_answer
            user_answer_text = question.answer_choice_to_string(user_answer)  # Lấy text của đáp án người dùng
            correct_choices = question.get_choices_correct()
            is_correct = question.check_if_correct(user_answer) if user_answer else False
            
            # Debug thông tin từng câu hỏi
            print(f"DEBUG - Question ID: {question.id}")
            print(f"Question: {question.content}")
            print(f"User Answer: {user_answer_text}")
            print(f"Is Correct: {is_correct}")
            print(f"Correct Answer: {correct_choices}")
            
            processed_questions.append({
                'question': question,
                'user_answer': user_answer_text,
                'is_correct': is_correct,
                'correct_answer': correct_choices,
                'explanation': question.explanation,
            })
        
        results = {
            "course": self.course,
            "quiz": self.quiz,
            "score": self.sitting.get_current_score,
            "max_score": self.sitting.get_max_score,
            "percent": self.sitting.get_percent_correct,
            "sitting": self.sitting,
            "questions": processed_questions,
            "show_answers": self.show_answers,  # Kiểm soát hiển thị đáp án
        }

        return render(self.request, self.result_template_name, results)