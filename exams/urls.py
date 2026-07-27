from django.urls import path
from . import views

urlpatterns = [
    path('', views.exam_list, name='exam_list'),
    path('<int:exam_set_id>/', views.exam_detail, name='exam_detail'),
    path('start/<int:exam_set_id>/', views.start_exam, name='start_exam'),
    path('attempt/<int:attempt_id>/section/<int:section_id>/', views.take_section, name='take_section'),
    path('attempt/<int:attempt_id>/retake/', views.retake_exam, name='retake_exam'),
    path('attempt/<int:attempt_id>/exact/', views.exact_exam, name='exact_exam'),
    path('attempt/<int:attempt_id>/exact/content/', views.exact_exam_content, name='exact_exam_content'),
    path('attempt/<int:attempt_id>/exact/complete/', views.complete_exact_exam, name='complete_exact_exam'),
    path('results/<int:attempt_id>/', views.results, name='results'),
]
