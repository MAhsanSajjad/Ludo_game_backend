from django.db import models
from utils_app.models import BaseModelWithCreatedInfo, Province, City, AppLanguage
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from user_management_app.constants import SOCIAL_PLATFORM_CHOICES, TRANSACTION_CHOICES, GAME_TYPE_CHOICES, STATUS_CHOICES, USER_TYPE_CHOICES

# Create your models here.
class MyAccountManager(BaseUserManager):
    def create_user(self, phone_number, username, password=None):
        if not phone_number:
            raise ValueError('Users must have an phone_number.')
        if not username:
            raise ValueError('Users must have a username')

        user = self.model(
            phone_number=phone_number,
            username=username,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, phone_number, username, password):
        user = self.create_user(
            phone_number=phone_number,
            password=password,
            username=username,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(using=self._db)

        return user

class User(AbstractBaseUser, PermissionsMixin):

    # Required Fields
    email = models.EmailField(verbose_name="email", max_length=60, unique=True, null=True, blank=True)
    username = models.CharField(max_length=30, unique=True)
    date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    last_login = models.DateTimeField(verbose_name='last login', auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # User Defined Fields
    full_name = models.CharField(max_length=128, null=True, blank=True)
    phone_number = models.CharField(max_length=128,  unique=True, null=True, blank=True)
    logo = models.ImageField(upload_to='Logo/User_logo', null=True, blank=True)
    social_platform = models.CharField(max_length=255, choices=SOCIAL_PLATFORM_CHOICES, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=255,  null=True, blank=True)
    user_type = models.CharField(max_length=255, choices=USER_TYPE_CHOICES, default='user')



    # User Defined Fields


    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['phone_number']

    objects = MyAccountManager()

    def _str_(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True
    


class Wallet(BaseModelWithCreatedInfo):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.user.username} wallet"
    

class TransactionHistroy(BaseModelWithCreatedInfo):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_CHOICES)

    def __str__(self):
        return f"{self.transaction_type} of {self.amount} to {self.wallet.user.username} Wallet"


class GameSetting(BaseModelWithCreatedInfo):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    other_players = models.ManyToManyField(User, blank=True, related_name='gamesetting_other_players')
    is_in_game = models.BooleanField(default=False)
    game_type = models.CharField(max_length=255, choices=GAME_TYPE_CHOICES)
    player_numbers = models.PositiveIntegerField()
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)   
    game_winner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='Game_Winner') 

class FriendRequest(BaseModelWithCreatedInfo):
    req_sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='Request_sender')
    req_receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='Request_receiver')
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='pending')

class FriendList(BaseModelWithCreatedInfo):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='friendlist_user')
    friends = models.ManyToManyField(User, blank=True, related_name='friendlist_friends')
    # rejected_user = models.ManyToManyField(User, blank=True, related_name='friendlist_friends')
    
    