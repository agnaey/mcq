from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),

    path("login/", views.login_page, name="login"),
   path("register/", views.register_page, name="register"),
    path("logout/", views.logout, name="logout"),


    # MCQ Related
    path("generate/", views.generate_mcq, name="generate_mcq"),
    path("result/", views.result, name="result"),
    path("history/", views.history, name="history"),
    path("history/delete/<int:entry_id>/", views.delete_history, name="delete_history"),
    path("download-pdf/", views.download_pdf, name="download_pdf"),

    # Test / Quiz
    path("test/", views.test, name="test"),
    path("test/results/", views.test_results, name="test_results"),
    path("quiz/", views.quiz, name="quiz"),

    # User Auth
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("is_logged_in/", views.is_logged_in, name="is_logged_in"),

    # Static pages
    path("about/", views.about, name="about"),
    path("profile/", views.profile, name="profile"),
]
