import random
import string
import stripe
from decimal import Decimal
from django.db.models import Q
from user_management_app.models import *
from user_management_app.serializers import *
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth.hashers import make_password
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.generics import ListAPIView
from fcm_django.models import FCMDevice
from rest_framework import filters
from .pagination import StandardResultSetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.timezone import now, timedelta
from django.conf import settings
from decimal import Decimal
from datetime import datetime


# Create your views here.
class UserLogin(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')

        if not phone_number:
            return Response({'message': 'phone_number is required'}, status=status.HTTP_400_BAD_REQUEST)

        username = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'username': username}
        )

        if created:
            user.set_password(phone_number)
            user.is_active = True
            user.save()
        else:
            if not user.is_active:
                return Response({'success': False, 'response':{'message': 'User is banned and cannot log in.'}}, status=status.HTTP_403_FORBIDDEN)
      
        wallet, created = Wallet.objects.get_or_create(user=user)

        token, _ = Token.objects.get_or_create(user=user)
        access_token = token.key

        serializer = UserSerializer(user)
        message = "User logged in successfully" if not created else "User created and logged in successfully"

        return Response({"Success": True, "message": message, "response": serializer.data, "access_token": access_token}, status=status.HTTP_200_OK)

class UpdateProfile(APIView):
    permission_classes = [IsAuthenticated]    
    
    def patch(self, request):
        user = request.user
        
        username = request.data.get('username')
        phone_number = request.data.get('phone_number')
        email = request.data.get('email')
        password = request.data.get('password')

        if username:
            user.username = username

        if email:
            if email != user.email and User.objects.filter(email=email).exists():
                return Response({'success': False, 'message': 'Email already exists!'}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email

        if phone_number:
            if phone_number != user.phone_number and User.objects.filter(phone_number=phone_number).exists():
                return Response({'success': False, 'message': 'Phone number already exists!'}, status=status.HTTP_400_BAD_REQUEST)
            user.phone_number = phone_number
        if password:
            user.set_password(password)

        user.save()

        return Response({'success': True, 'message': 'Profile updated successfully'}, status=status.HTTP_200_OK)

class SocialLoginApiView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email').lower().strip() if 'email' in request.data else None
        user_d_id = request.data.get('device_id', None)
        full_name = request.data.get('full_name', None)
        social_platform = request.data.get('social_platform', None)

        if not email or not user_d_id or not social_platform:
            return Response({"success": False, 'response': {'message': 'email, device id, and social_platform required!'}},
                            status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(email=email).first()        
        if not user:
            username = email.split('@')[0]
            hashed_password = make_password(username)
            user = User.objects.create(
                username=username,
                password=hashed_password,
                email=email,
                full_name=full_name,
                social_platform=social_platform,
            )

        user.is_active = True
        user.save()

        token, created = Token.objects.get_or_create(user=user)

        access_token = token.key
        
        wallet, created = Wallet.objects.get_or_create(user=user)
        serializer = DefaultUserSerializer(user)
        
        try:
            fcm_device = FCMDevice.objects.get(device_id=user.id)
            fcm_device.delete()
        except:
            pass

        if user_d_id:
            fcm_device, created = FCMDevice.objects.get_or_create(
                registration_id=user_d_id,
                defaults={'user': user, 'device_id': user_d_id}
            )

        return Response({'success': True, 'response': {'data': serializer.data, 'access_token': access_token}}, status=status.HTTP_200_OK)
    
class CreateDepositIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            amount = int(float(request.data.get('amount')) * 100)
            currency = 'cad'

            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                payment_method_types=['card'],
            )
            return Response({'client_secret': payment_intent.client_secret}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Stripe Payment
class PaymentAPIView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        
        amount = request.data.get('amount')

        serializer = CheckPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            client_secret = serializer.validated_data['client_secret']
            intent = stripe.PaymentIntent.retrieve(client_secret)
            if intent == 'succeeded':

                balance = Wallet.objects.filter(user=request.user).first()
                if not balance:
                    balance = Wallet.objects.create(user=request.user,  balance=0, coin=0)

                balance.balance += amount
                balance.save()

                TransactionHistroy.objects.create(user=request.user, amount=amount, transaction_type='deposit')
                
                return Response({"success": True, 'response': {'message': 'Payment Successful'}},
                            status=status.HTTP_200_OK)

            else:
                return Response({"success": False, 'response': {'message': 'Payment Incomplete'}},
                            status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            return Response({"success": False, 'response': {'message': str(e)}},
            status=status.HTTP_400_BAD_REQUEST)
        


class TransactionHistroyAPIView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        
        amount = request.data.get('amount')
        balance = Wallet.objects.filter(user=request.user).first()
        if not balance:
            balance = Wallet.objects.create(user=request.user,  balance=0, coin=0)

        if amount > balance.balance:
            return Response({"success": False, 'response': {'message': 'Insufficient Balance'}},
                            status=status.HTTP_400_BAD_REQUEST)
        

        TransactionHistroy.objects.create(user=request.user, amount=amount, transaction_type='withdraw')
        return Response({"success": True, 'response': {'message': 'Withdraw request sent Successful'}}),
            
    def get(self, request):
        
        transaction_type = request.GET.get('transaction_type')
        if not transaction_type:
            return Response({"success": False, 'response': {'message': 'transaction_type is required'}},
                            status=status.HTTP_400_BAD_REQUEST)

        transaction = TransactionHistroy.objects.create(user=request.user, transaction_type=transaction_type)

        serializer = TransactionSerializer(transaction)

        return Response(
            {"success": True, 'response': {'message': 'Withdraw request sent successfully', 'data': serializer.data}},
            status=status.HTTP_201_CREATED
        )
class ConfirmDepositView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            payment_intent_id = request.data.get('payment_intent_idamount')

            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if payment_intent.status == 'succeeded':
                wallet = Wallet.objects.get_or_create(user=user)
                amount = payment_intent.amount / 100

                wallet.balance += amount
                wallet.save()

                transaction = TransactionHistroy.objects.create(
                    wallet=wallet, 
                    amount=amount, 
                    transaction_type='deposit'
                )
                transaction.save()

                return Response({"success": True, "message": "Deposit successful!", "balance": wallet.balance}, status=status.HTTP_200_OK)
            else:
                return Response({"success": False, "message": "Payment not confirmed!"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GameSettingCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        other_players = data.get('other_players', [])
        player_numbers = data.get('player_numbers')
        entry_fee = data.get('entry_fee', 0.00)

        if player_numbers > 4:
            return Response({'success': False, 'response': {'message': 'Player count must be 4 or less'}}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(other_players, int):
            other_players = [other_players]

        players = User.objects.filter(id__in=other_players)

        if len(players) + 1 != player_numbers:
            return Response({'success': False, 'response': {'message': 'Player count mismatch'}}, status=status.HTTP_400_BAD_REQUEST)

        all_users = list(players) + [request.user]
        insufficient_funds = []

        for user in all_users:
            wallet = Wallet.objects.filter(user=user).first()
            if not wallet or wallet.balance < entry_fee:
                insufficient_funds.append(user.username)

        if insufficient_funds:
            return Response(
                {'success': False, 'response': {'message': 'Insufficient funds', 'details': {username: 'Insufficient balance' for username in insufficient_funds}}}, status=status.HTTP_400_BAD_REQUEST)

        for user in all_users:
            wallet = Wallet.objects.get(user=user)
            wallet.balance -= entry_fee
            wallet.save()

        game_setting = GameSetting.objects.create(
            user=request.user,
            is_in_game=data.get('is_in_game', False),
            game_type=data.get('game_type'),
            player_numbers=player_numbers,
            entry_fee=entry_fee
        )
        game_setting.other_players.set(players)
        serializer = GameSettingSerializer(game_setting)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UserListAPIView(ListAPIView):
    serializer_class = UserSerializer
    pagination_class = StandardResultSetPagination

    def get_queryset(self):
        username = self.request.GET.get('username')
        queryset = User.objects.all()
        if username:
            queryset = queryset.filter(username=username)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({'success': True, 'response': {'data': serializer.data, 'Total_user': queryset.count()}})

        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True,'response': {'data': serializer.data, 'Total_user': queryset.count()}})


class SendFriendRequestAPIView(APIView):
    def post(self, request):
        from_user = request.user
        target_user_id = request.data.get('target_user_id')

        if not target_user_id:
            return Response({"success": False, "message": "Target user ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if str(from_user.id) == target_user_id:
            return Response({"success": False, "message": "You cannot send a friend request to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            to_user = User.objects.get(id=target_user_id)
            friend_request, created = FriendRequest.objects.get_or_create(
                req_sender=from_user,
                req_receiver=to_user
            )

            if not created:
                return Response({"success": False, "message": "Friend request already sent."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = FriendRequestSerializer(friend_request)
            return Response({"success": True, "message": "Friend request sent successfully.", "data": serializer.data}, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response({"success": False, "message": "Target user not found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FriendListAPIView(APIView):
    def put(self, request, id):
        try:
            friend_request = FriendRequest.objects.get(id=id)
        except FriendRequest.DoesNotExist:
            return Response(
                {"success": False, "message": "Friend request not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        status_action = request.data.get('status')

        if status_action == 'accepted':
            sender, created = FriendList.objects.get_or_create(user=friend_request.req_sender)
            receiver, created = FriendList.objects.get_or_create(user=friend_request.req_receiver)
            sender.friends.add(friend_request.req_receiver)
            receiver.friends.add(friend_request.req_sender)

            friend_request.status = 'accepted'
            friend_request.save()

            return Response({'success': True, 'response': {'message': f"Friend request from {friend_request.req_sender.username} to {friend_request.req_receiver.username} has been accepted successfully."}}, status=status.HTTP_200_OK)

        elif status_action == 'rejected':
            friend_request.status = 'rejected'
            friend_request.save()
            return Response({'success': True,'response':{'message': f"Friend request from {friend_request.req_sender.username} to {friend_request.req_receiver.username} has been rejected."}}, status=status.HTTP_200_OK)

        return Response({"success": False, "message": "Invalid status provided. Use 'accepted' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST)

class SetGameWinnerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        game_setting_id = request.data.get("game_setting_id")
        game_winner_id = request.data.get("game_winner_id")
        winning_amount = request.data.get("winning_amount")

        if not game_setting_id or not game_winner_id or not winning_amount:
            return Response(
                {"success": False, "message": "game_setting_id, game_winner_id, and winning_amount are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            game_setting = GameSetting.objects.get(id=game_setting_id)
        except GameSetting.DoesNotExist:
            return Response({"success": False, "message": "GameSetting not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            game_winner = User.objects.get(id=game_winner_id)
        except User.DoesNotExist:
            return Response({"success": False, "message": "Game winner not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            game_setting.game_winner = game_winner
            game_setting.save()

            winning_amount = Decimal(winning_amount)

            total_entry_fee = game_setting.entry_fee * (game_setting.other_players.count() + 1)

            game_winner_wallet, created = Wallet.objects.get_or_create(user=game_winner)
            game_winner_wallet.balance += winning_amount
            game_winner_wallet.save()

            amount_difference = total_entry_fee - winning_amount
            if amount_difference > 0:
                admin_user = User.objects.filter(is_superuser=True, is_staff=True).order_by('date_joined').first()
                if admin_user:
                    admin_wallet, created = Wallet.objects.get_or_create(user=admin_user)
                    admin_wallet.balance += amount_difference
                    admin_wallet.save()

            return Response(
                {"success": True, "message": "Game winner and admin wallets updated successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AdminLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'message': 'Email and Password are required!'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                user.is_active = True
                user.save()

            token, created = Token.objects.get_or_create(user=user)
            return Response({'message': 'Login successful', 'data': UserSerializer(user).data, 'token': token.key}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


class BanUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        user = User.objects.filter(id=id).first()
        if user:
            user.is_active = False
            user.save()
            serializer = UserSerializer(user)
            return Response({'success':True, 'response':{'message': 'User Banned Successfully', 'data': serializer.data}}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

class UnbanUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        user = User.objects.filter(id=id).first()
        if user:
            user.is_active = True
            user.save()
            return Response({'success':True, 'response':{'message': f'User with ID {id} has been unbanned.'}}, status=status.HTTP_200_OK)
        else:
            return Response({'success':False, 'response':{'message': 'User not found.'}}, status=status.HTTP_404_NOT_FOUND)


class ToggleBanUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        user = User.objects.filter(id=id).first()
        if user:
            user.is_active = not user.is_active
            user.save()

            serializer = UserSerializer(user)

            return Response({
                'success': True,
                'response': {
                    'message': f"User has been {'unbanned' if user.is_active else 'banned'}.",
                    'user': serializer.data}}, status=status.HTTP_200_OK)
        
        return Response({'success': False,'response': {'message': 'User not found.'}}, status=status.HTTP_404_NOT_FOUND)




class UsersAPIView(ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserWithStatusSerializer
    pagination_class = StandardResultSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['username', 'email', 'phone_number']
    filterset_fields = ['is_active', 'email', 'phone_number']
                        
class AdminLogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        tokens = Token.objects.filter(user=user)
        if tokens.exists():
            tokens.delete()
            return Response({'success': True, 'response': {'message': 'Logout successfully'}}, status=status.HTTP_200_OK)
        else:
            return Response({'success': False, 'response': {'message': 'Token not found.'}}, status=status.HTTP_404_NOT_FOUND)

class StatsAPIView(APIView):

    def get(self, request):
        today = now().date()

        total_users_today = User.objects.count()

        total_users_till_yesterday = User.objects.filter(date_joined__lt=today).count()

        if total_users_till_yesterday > 0:
            user_percentage_change = ((total_users_today - total_users_till_yesterday) / total_users_till_yesterday) * 100
        else:
            user_percentage_change = total_users_today * 100

        return Response({'success': True, 'response': {'data':{
            'total_users': total_users_today,
            'percentage': round(user_percentage_change, 2)}}}, status=status.HTTP_200_OK)

class MatchStatsAPIView(APIView):
    def get(self, request):
        today = now().date()

        matches_today = GameSetting.objects.filter(created_at__date=today).count()

        current_week_start = today - timedelta(days=today.weekday())
        previous_week_start = current_week_start - timedelta(days=7)

        matches_current_week = GameSetting.objects.filter(created_at__date__gte=current_week_start).count()
        matches_previous_week = GameSetting.objects.filter(
            created_at__date__gte=previous_week_start, created_at__date__lt=current_week_start
        ).count()

        if matches_previous_week == 0:
            percentage_change = 0 if matches_current_week == 0 else 100
        else:
            percentage_change = ((matches_current_week - matches_previous_week) / matches_previous_week) * 100

        response_data = {
            "matches_today": matches_today,
            "percentage_change_from_last_week": round(percentage_change, 2)}

        return Response({"success": True, "data": response_data}, status=status.HTTP_200_OK)


class TotalBetPlacedAPIView(APIView):
    def get(self, request):
        today = now().date()
        current_week_start = today - timedelta(days=today.weekday())
        previous_week_start = current_week_start - timedelta(days=7)
        previous_week_end = current_week_start - timedelta(days=1)

        total_bet_all_time = 0
        all_games = GameSetting.objects.all()
        for game in all_games:
            total_players_in_game = 1 + game.other_players.count()  # Total players in the game
            total_bet_all_time += total_players_in_game * game.entry_fee  # Total bet for this game

        total_bet_current_week = 0
        games_current_week = GameSetting.objects.filter(
            created_at__date__gte=current_week_start, created_at__date__lte=today
        )
        for game in games_current_week:
            total_players_in_game = 1 + game.other_players.count()
            total_bet_current_week += total_players_in_game * game.entry_fee

        total_bet_previous_week = 0
        games_previous_week = GameSetting.objects.filter(
            created_at__date__gte=previous_week_start, created_at__date__lte=previous_week_end
        )
        for game in games_previous_week:
            total_players_in_game = 1 + game.other_players.count()
            total_bet_previous_week += total_players_in_game * game.entry_fee

        if total_bet_previous_week > 0:
            percentage_change = ((total_bet_current_week - total_bet_previous_week) / total_bet_previous_week) * 100
        else:
            percentage_change = 100 if total_bet_current_week > 0 else 0

        return Response({
            'success': True,
            'response': {
                'data': {
                    'total_bet': round(total_bet_all_time, 2),
                    'bet_placed_current_week': round(total_bet_current_week, 2),
                    'percentage_change': round(percentage_change, 2),
                }
            }
        }, status=status.HTTP_200_OK)



class UserPlayedThisWeekAPIView(APIView):
    def get(self, request):
        today = now().date()
        current_week_start = today - timedelta(days=today.weekday())
        previous_week_start = current_week_start - timedelta(days=7)
        previous_week_end = current_week_start - timedelta(days=1)

        total_players_current_week = 0
        total_players_previous_week = 0

        games_current_week = GameSetting.objects.filter(created_at__date__gte=current_week_start, created_at__date__lte=today)
        for game in games_current_week:
            if game.is_in_game:
                total_players_current_week += 1
            total_players_current_week += game.other_players.count()

        games_previous_week = GameSetting.objects.filter(created_at__date__gte=previous_week_start, created_at__date__lte=previous_week_end)
        for game in games_previous_week:
            if game.is_in_game: 
                total_players_previous_week += 1
            total_players_previous_week += game.other_players.count()

        if total_players_previous_week > 0:
            player_percentage_change = ((total_players_current_week - total_players_previous_week) / total_players_previous_week) * 100
        else:
            player_percentage_change = 0 if total_players_current_week == 0 else 100

        return Response({
            'success': True,
            'response': {
                'data': {
                    'Active_players': total_players_current_week,
                    'player_percentage': round(player_percentage_change, 2),
                }
            }
        }, status=status.HTTP_200_OK)


class TwoPlayerMatchesAPIView(APIView):
    def get(self, request):
        total_two_player_matches = GameSetting.objects.filter(player_numbers=2).count()

        two_player_matches = GameSetting.objects.filter(player_numbers=2)
        total_bets = sum(2 * match.entry_fee for match in two_player_matches)

        average_bet = total_bets / total_two_player_matches if total_two_player_matches > 0 else 0

        today = now().date()
        yesterday = today - timedelta(days=1)

        two_player_matches_yesterday = GameSetting.objects.filter(player_numbers=2, created_at__date=yesterday).count()
        two_player_matches_today = GameSetting.objects.filter(player_numbers=2, created_at__date=today).count()

        if two_player_matches_yesterday > 0:
            percentage_change = ((two_player_matches_today - two_player_matches_yesterday) / two_player_matches_yesterday) * 100
        else:
            percentage_change = 100 if two_player_matches_today > 0 else 0

        return Response({
            'success': True,
            'response': {
                'data': {
                    'two_player_matches': total_two_player_matches,
                    'total_bets': round(total_bets, 2),
                    'average_bet': round(average_bet, 2),
                    'percentage_change_from_yesterday': round(percentage_change, 2),}}}, status=status.HTTP_200_OK)


class FourPlayerMatchesAPIView(APIView):
    def get(self, request):
        total_four_player_matches = GameSetting.objects.filter(player_numbers=4).count()

        four_player_matches = GameSetting.objects.filter(player_numbers=4)
        total_bets = sum(4 * match.entry_fee for match in four_player_matches)

        average_bet = total_bets / total_four_player_matches if total_four_player_matches > 0 else 0

        today = now().date()
        yesterday = today - timedelta(days=1)

        four_player_matches_yesterday = GameSetting.objects.filter(player_numbers=4, created_at__date=yesterday).count()
        four_player_matches_today = GameSetting.objects.filter(player_numbers=4, created_at__date=today).count()

        if four_player_matches_yesterday > 0:
            percentage_change = ((four_player_matches_today - four_player_matches_yesterday) / four_player_matches_yesterday) * 100
        else:
            percentage_change = 100 if four_player_matches_today > 0 else 0

        return Response({
            'success': True,
            'response': {
                'data': {
                    'four_player_matches': total_four_player_matches,
                    'total_bets': round(total_bets, 2),
                    'average_bet': round(average_bet, 2),
                    'percentage_change_from_yesterday': round(percentage_change, 2),}}}, status=status.HTTP_200_OK)

class TotalRevenueAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_difference = Decimal('0.0')

        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not month or not year:
            current_date = datetime.now()
            month = current_date.month
            year = current_date.year

        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return Response(
                {"success": False, "response": {"message": "Invalid month or year format."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (1 <= month <= 12):
            return Response(
                {"success": False, "response": {"message": "Month must be between 1 and 12."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin_user = User.objects.filter(is_superuser=True, is_staff=True).first()
        if admin_user:
            games = GameSetting.objects.filter(
                game_winner__isnull=False,
                created_at__month=month,
                created_at__year=year
            )
            for game in games:
                total_entry_fee = game.entry_fee * (game.other_players.count() + 1)
                winning_amount = Wallet.objects.filter(user=game.game_winner).first().balance
                amount_difference = total_entry_fee - winning_amount
                if amount_difference > 0:
                    total_difference += amount_difference

        return Response(
            {
                "success": True,
                "response": {
                    "total_revenue": [round(total_difference, 2)],
                    "month": month,
                    "year": year
                }
            },
            status=status.HTTP_200_OK,
        )



class UserDetailAPIView(APIView):

    def get(self, request, id):
        user = User.objects.get(id=id)

        wallet = Wallet.objects.get(user=user)
        total_balance = wallet.balance

        games_played = GameSetting.objects.filter(user=user) | GameSetting.objects.filter(other_players=user)
        
        games_played = games_played.distinct()

        total_matches_played = games_played.count()

        match_history = []
        for game in games_played:
            is_in_game = user == game.user or user in game.other_players.all()

            if is_in_game:
                is_winner = game.game_winner == user
                status = 'Win' if is_winner else 'Lose'

                game_date = game.created_at.strftime("%b. %d, %Y, %I:%M %p")

                match_history.append({
                    'game_id': game.id,
                    'status': status,
                    'game_date': game_date,
                })

        serializer = UserSerializer(user)

        return Response({
            'success': True,
            'data': serializer.data,
            'total_balance': total_balance,
            'total_matches_played': total_matches_played,
            'match_history': match_history
        })


class UserDetailWithResetBalAPIView(APIView):

    def get(self, request, id):
        reset_balance = request.query_params.get('reset_balance', None)

        user = User.objects.get(id=id)
        wallet = Wallet.objects.get(user=user)

        if reset_balance == 'true':
            wallet.balance = 0.00
            wallet.save()
            return Response({
                'message': f'Wallet balance for {user.username} has been reset to 0.00.',
                'success': True
            }, status=status.HTTP_200_OK)

        total_balance = wallet.balance

        games_played = GameSetting.objects.filter(user=user) | GameSetting.objects.filter(other_players=user)
        games_played = games_played.distinct()

        total_matches_played = games_played.count()

        match_history = []
        for game in games_played:
            is_in_game = user == game.user or user in game.other_players.all()

            if is_in_game:
                is_winner = game.game_winner == user
                status = 'Win' if is_winner else 'Lose'

                game_date = game.created_at.strftime("%b. %d, %Y, %I:%M %p")

                match_history.append({
                    'game_id': game.id,
                    'status': status,
                    'game_date': game_date,
                })

        serializer = UserSerializer(user)

        return Response({
            'success': True,
            'data': serializer.data,
            'total_balance': total_balance,
            'total_matches_played': total_matches_played,
            'match_history': match_history
        })


class ResetWalletBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        user = User.objects.filter(id=id).first()

        if not user:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

        wallet = Wallet.objects.filter(user=user).first()

        if not wallet:
            return Response({
                'error': 'Wallet not found for this user'
            }, status=status.HTTP_404_NOT_FOUND)

        wallet.balance = 0.00
        wallet.save()

        return Response({
            'message': f'Wallet balance for {user.username} has been reset to 0.00.'
        }, status=status.HTTP_200_OK)
    

class UserDetailWithResetBalanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        user = User.objects.filter(id=id).first()

        if not user:
            return Response({'success': False, 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        wallet = Wallet.objects.filter(user=user).first()
        if not wallet:
            return Response({'success': False, 'message': 'Wallet not found for the user.'}, status=status.HTTP_404_NOT_FOUND)

        total_balance = wallet.balance
        games_played = GameSetting.objects.filter(user=user) | GameSetting.objects.filter(other_players=user)
        total_matches_played = games_played.distinct().count()

        if request.query_params.get('reset_balance') == 'true':
            if request.user.is_admin:
                wallet.balance = 0.00
                wallet.save()
                return Response({
                    'success': True,
                    'message': f'Wallet balance for {user.username} has been reset to 0.00.',
                    'data': UserSerializer(user).data,
                    'total_balance': wallet.balance,
                    'total_matches_played': total_matches_played,
                    'status': 'banned' if not user.is_active else 'unbanned'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'You do not have permission to reset the balance.'
                }, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(user)
        return Response({
            'success': True,
            'data': serializer.data,
            'total_balance': total_balance,
            'total_matches_played': total_matches_played,
            'status': 'banned' if not user.is_active else 'unbanned'
        }, status=status.HTTP_200_OK)

class MatchHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        user = User.objects.get(id=id)

        games = GameSetting.objects.filter(user=user) | GameSetting.objects.filter(other_players=user)

        match_history = []

        for game in games:
            is_winner = game.game_winner == user

            game_date = game.created_at

            match_history.append({
                'game_id': game.id,
                'status': 'Win' if is_winner else 'Lose',
                'game_date': game_date,
            })

        return Response({
            'success': True,
            'match_history': match_history
        }, status=status.HTTP_200_OK)


class TransactionHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        user = User.objects.filter(id=id).first()

        if not user:
            return Response({"success": False, "response": {"message": "User not found."}}, status=404)

        wallet = Wallet.objects.filter(user__id=id).first()

        if not wallet:
            return Response({"success": False, "response": {"message": "Wallet not found for this user."}}, status=404)

        transaction_type = request.query_params.get("transaction_type")
        if not transaction_type:
            return Response({"success": False, "response": {"message": 'transaction_type is required.'}}, status=400)

        if transaction_type not in ["deposit", "withdraw"]:
            return Response({
                "success": False,
                "response": {"message": f"Invalid transaction_type: '{transaction_type}'. Valid values are 'deposit' or 'withdraw'."}
            }, status=400)

        transactions = TransactionHistroy.objects.filter(wallet=wallet, transaction_type=transaction_type)

        transaction_history = [
            {
                "id": transaction.id,
                "amount": f"{transaction.amount:.2f}",
                "transaction_type": transaction.transaction_type,
                "transaction_time": transaction.created_at.strftime("%b. %d, %Y, %I:%M %p")
            }
            for transaction in transactions
        ]

        total_balance = wallet.balance

        return Response({
            "success": True,
            "response": {
                "total_balance": f"{total_balance:.2f}",
                "transactions": transaction_history
            }
        }, status=200)


class UsersDetailWithIDAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, id=None):
        if id:
            user = User.objects.filter(id=id).first()
            if not user:
                return Response({'success': False, 'message': 'User not found'}, status=404)

            wallet = Wallet.objects.filter(user=user).first()
            total_balance = wallet.balance if wallet else 0 

            games_played = GameSetting.objects.filter(user=user) | GameSetting.objects.filter(other_players=user)
            games_played = games_played.distinct()

            total_matches_played = games_played.count()

            match_history = []
            for game in games_played:
                is_in_game = user == game.user or user in game.other_players.all()

                if is_in_game:
                    is_winner = game.game_winner == user
                    status = 'Win' if is_winner else 'Lose'

                    game_date = game.created_at.strftime("%b. %d, %Y, %I:%M %p")

                    match_history.append({
                        'game_id': game.id,
                        'status': status,
                        'game_date': game_date,
                    })

            serializer = UserSerializer(user)

            return Response({
                'success': True,
                'data': serializer.data,
                'total_balance': total_balance,
                'total_matches_played': total_matches_played,
                'match_history': match_history
            })

        else:
            search_query = request.query_params.get('search', None)
            is_active = request.query_params.get('is_active', None)
            email = request.query_params.get('email', None)
            phone_number = request.query_params.get('phone_number', None)

            queryset = User.objects.all()

            if is_active is not None:
                queryset = queryset.filter(is_active=is_active)
            if email:
                queryset = queryset.filter(email=email)
            if phone_number:
                queryset = queryset.filter(phone_number=phone_number)

            if search_query:
                queryset = queryset.filter(
                    Q(username__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(phone_number__icontains=search_query)
                )

            paginator = StandardResultSetPagination()
            paginated_queryset = paginator.paginate_queryset(queryset, request)

            serializer = UserWithStatusSerializer(paginated_queryset, many=True)

            return paginator.get_paginated_response(serializer.data)

class DailyWinnersCountAPIView(APIView):
    def get(self, request):
        today = now().date()

        daily_winners_count = GameSetting.objects.filter(game_winner__isnull=False, created_at__date=today).count()

        return Response({'success': True, 'daily_winners': daily_winners_count, 'message': 'Daily winners count retrieved successfully'})

class TotalWithdrawnAmountAPIView(APIView):
    def get(self, request):
        withdrawals = TransactionHistroy.objects.filter(transaction_type='withdraw')

        total_withdrawn = sum(withdrawal.amount for withdrawal in withdrawals)

        return Response({
            'success': True,
            'total_withdrawn_amount': total_withdrawn,
            'message': 'Total withdrawn amount retrieved successfully'
        })



class UsersWithWithdrawalsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.filter(
            id__in=TransactionHistroy.objects.filter(transaction_type='withdraw').values('wallet__user').distinct()
        )

        serializer = WithDrawDetailSerializer(users, many=True)

        return Response(
            {"success": True, "response": {"users": serializer.data}},
            status=status.HTTP_200_OK
        )

class UserBlock(APIView):
    permission_classes = [AllowAny]
    def post(self, request, id):
        user = User.objects.filter(id=id).first()
        if not user:
            return Response({'success':False, 'response':{'message': 'User not found!'}}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active=False
        user.save()
        return Response({'success': True, 'response':{'message': 'Player Blocked Successfully!'}}, status=status.HTTP_200_OK)