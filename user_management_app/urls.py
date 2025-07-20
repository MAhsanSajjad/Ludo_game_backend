from django.urls import path
from . import views
from .views import *

urlpatterns = [
    path('Login/', views.UserLogin.as_view()),
    path('SocialLogin/', views.SocialLoginApiView.as_view()),
    path('UpdateProfile/', views.UpdateProfile.as_view()),
    path('SelectPlayer/', views.GameSettingCreateAPIView.as_view()),
    path('UserList/', views.UserListAPIView.as_view()),
    path('SendFriendRequest/', views.SendFriendRequestAPIView.as_view()),
    path('FriendList/<int:id>/', views.FriendListAPIView.as_view()),
    path('GameWinner/', views.SetGameWinnerAPIView.as_view()),
  
    path('AdminLogin/', views.AdminLoginAPIView.as_view()),
    path('BanUser/<int:id>/', views.BanUserAPIView.as_view()),
    path('UnBanUser/<int:id>/', views.UnbanUserAPIView.as_view()),
    path('Logout/', views.AdminLogoutAPIView.as_view()),
    path('UserStats/', views.StatsAPIView.as_view()),
    path('MatchPlayed/', views.MatchStatsAPIView.as_view()),
    path('TotalBet/', views.TotalBetPlacedAPIView.as_view()),
    path('ToggleBan/<int:id>/', views.ToggleBanUserAPIView.as_view()),
    path('ActivePlayers/', views.UserPlayedThisWeekAPIView.as_view()),
    path('TwoPlayerMatches/', views.TwoPlayerMatchesAPIView.as_view()),
    path('FourPlayerMatches/', views.FourPlayerMatchesAPIView.as_view()),
    path('AdminRevenue/', views.TotalRevenueAPIView.as_view()),
    path('AdminUserList/', views.UsersAPIView.as_view()),
    path('UserDetail/', views.UsersAPIView.as_view()),
    path('UserDetail/<int:id>/', views.UserDetailWithResetBalanceAPIView.as_view()),
    path('UserDetailss/<int:id>/', views.UserDetailAPIView.as_view()),
    path('Resetbalance/<int:id>/', views.UserDetailWithResetBalanceAPIView.as_view()),
    path('ResetBalance/<int:id>/', views.ResetWalletBalanceView.as_view()),
    path('MatchHistory/<int:id>/', views.MatchHistoryAPIView.as_view()),
    path('UserListDetails/', views.UsersDetailWithIDAPIView.as_view()),
    path('UserListDetails/<int:id>/', views.UsersDetailWithIDAPIView.as_view()),
    path('DailyWinners/', views.DailyWinnersCountAPIView.as_view()),
    path('TotalWithdraw/', views.TotalWithdrawnAmountAPIView.as_view()),
    path('TransactionHistroy/', views.UsersWithWithdrawalsAPIView.as_view()),
    path('TransactionHistroy/<int:id>/', views.TransactionHistoryAPIView.as_view()),
]


