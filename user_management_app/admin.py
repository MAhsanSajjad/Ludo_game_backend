from django.contrib import admin
from user_management_app.models import User, TransactionHistroy, Wallet, GameSetting, FriendRequest, FriendList
# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email']


@admin.register(Wallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'balance', 'created_at', 'updated_at']

@admin.register(TransactionHistroy)
class TransactionHistroyAdmin(admin.ModelAdmin):
    list_display = ['id', 'wallet', 'amount', 'transaction_type']

@admin.register(GameSetting)
class GameSettingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user',  'is_in_game', 'game_type', 'player_numbers', 'entry_fee', 'created_at']

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'req_sender', 'req_receiver', 'status']

@admin.register(FriendList)
class FriendListAdmin(admin.ModelAdmin):
    list_display = ['id', 'user']