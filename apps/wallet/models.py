from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class TransactionType(models.TextChoices):
    CREDIT = 'CREDIT', _('Credit / Deposit')
    DEBIT = 'DEBIT', _('Debit / Booking Payment')

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=5, default='INR')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def credit(self, amount, description, ref=""):
        self.balance += amount
        self.save()
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=TransactionType.CREDIT,
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference_id=ref
        )
        return self.balance

    def debit(self, amount, description, ref=""):
        if self.balance < amount:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        self.save()
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=TransactionType.DEBIT,
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference_id=ref
        )
        return self.balance

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₹{self.balance}"


class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()}: ₹{self.amount} ({self.wallet.user.username})"
