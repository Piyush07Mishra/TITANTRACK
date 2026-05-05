from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from catrentapp import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('signup/', views.admin_signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('operator-dashboard/', views.operator_dashboard, name='operator_dashboard'),
    path('add/', views.add, name="add"),
    path('delete/<int:pk>/', views.delete_machine, name="delete_machine"),
    path('download/<int:pk>/', views.download_qr, name="download_qr"),
    path('checkout/<str:equipment_id>/', views.qr_scan_info, name="checkout"),
    path('checkin/<int:rental_id>/', views.checkin_machine, name="checkin_machine"),
    path('forecast/<str:equipment_type>/', views.generate_forecast, name="generate_forecast"),
    path('forecast_image/<str:equipment_type>/', views.get_forecast_image, name="get_forecast_image"),
    path('', views.rental_dashboard, name="rental_dashboard"),
    path('anomaly-data/', views.anomaly_data, name="anomaly_data"),
    path('api/operators/list/', views.operator_list_api, name="operator_list_api"),
    path('api/operators/save/', views.operator_save_api, name="operator_save_api"),
    path('api/operators/delete/<int:operator_id>/', views.operator_delete_api, name="operator_delete_api"),
    path('api/operators/reset/<int:operator_id>/', views.operator_reset_credentials_api, name="operator_reset_credentials_api"),
    path('regenerate-qr/', views.manual_regenerate_qr, name="manual_regenerate_qr"),
    path('send-reminders/', views.send_rental_reminders, name="send_rental_reminders"),
]