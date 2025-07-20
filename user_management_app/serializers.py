from rest_framework import serializers
from user_management_app.models import User, TransactionHistroy, GameSetting, FriendRequest, FriendList, GameWinnser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'username', 'email', 'logo', 'user_type']


class DefaultUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username',  'full_name', 'logo',
                 'phone_number', 'social_platform']
        
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionHistroy
        fields = ['id', 'wallet', 'amount', 'transaction_type']


class GameSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSetting
        fields = ['id', 'user', 'other_players', 'is_in_game', 'game_type', 'player_numbers', 'entry_fee']


class FriendRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendRequest
        fields = ['id', 'req_sender', 'req_receiver', 'status']

class FriendListSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendList
        fields = ['id', 'user', 'friends']

class UserWithStatusSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'phone_number', 'username', 'email', 'logo', 'status']

    def get_status(self, instance):
        return "unbanned" if instance.is_active else "banned"
    
class CheckPaymentSerializer(serializers.Serializer):
    client_secret = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    

class WithDrawDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'username', 'email', 'logo']
        
        
class BlockedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'role']
        
        
class GameWinnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameWinnser
        fields = ['id', 'user', 'description']
        
        