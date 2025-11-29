"""
Credit account service layer for business logic
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import CreditAccount, AccountStatement, AccountTransaction


class CreditAccountService:
    """信用账户业务逻辑服务"""
    
    @staticmethod
    def create_credit_account(user, credit_limit, payment_term_days=30):
        """为经销商创建信用账户"""
        if user.role != 'dealer':
            raise ValueError("只能为经销商创建信用账户")
        
        if hasattr(user, 'credit_account'):
            raise ValueError("该用户已有信用账户")
        
        account = CreditAccount.objects.create(
            user=user,
            credit_limit=credit_limit,
            payment_term_days=payment_term_days,
            outstanding_debt=0,
            is_active=True
        )
        return account
    
    @staticmethod
    def record_purchase(credit_account, amount, order_id, description=""):
        """记录采购交易（增加欠款）"""
        with transaction.atomic():
            # Check if can place order
            if not credit_account.can_place_order(amount):
                raise ValueError("信用额度不足或账户已停用")
            
            # Update outstanding debt
            credit_account.outstanding_debt += amount
            credit_account.save()
            
            # Calculate due date
            due_date = timezone.now().date() + timedelta(days=credit_account.payment_term_days)
            
            # Create transaction record
            trans = AccountTransaction.objects.create(
                credit_account=credit_account,
                transaction_type='purchase',
                amount=amount,
                balance_after=credit_account.outstanding_debt,
                order_id=order_id,
                due_date=due_date,
                payment_status='unpaid',
                description=description
            )
            
            return trans
    
    @staticmethod
    def record_payment(credit_account, amount, description=""):
        """记录付款交易（减少欠款）"""
        with transaction.atomic():
            # Update outstanding debt
            credit_account.outstanding_debt -= amount
            if credit_account.outstanding_debt < 0:
                credit_account.outstanding_debt = 0
            credit_account.save()
            
            # Create transaction record
            trans = AccountTransaction.objects.create(
                credit_account=credit_account,
                transaction_type='payment',
                amount=amount,
                balance_after=credit_account.outstanding_debt,
                paid_date=timezone.now().date(),
                payment_status='paid',
                description=description
            )
            
            # Mark unpaid transactions as paid (FIFO)
            unpaid_transactions = AccountTransaction.objects.filter(
                credit_account=credit_account,
                transaction_type='purchase',
                payment_status='unpaid'
            ).order_by('created_at')
            
            remaining_payment = amount
            for unpaid_trans in unpaid_transactions:
                if remaining_payment <= 0:
                    break
                
                if unpaid_trans.amount <= remaining_payment:
                    unpaid_trans.payment_status = 'paid'
                    unpaid_trans.paid_date = timezone.now().date()
                    unpaid_trans.save()
                    remaining_payment -= unpaid_trans.amount
            
            return trans
    
    @staticmethod
    def record_refund(credit_account, amount, order_id, description=""):
        """记录退款交易（减少欠款）"""
        with transaction.atomic():
            # Update outstanding debt
            credit_account.outstanding_debt -= amount
            if credit_account.outstanding_debt < 0:
                credit_account.outstanding_debt = 0
            credit_account.save()
            
            # Create transaction record
            trans = AccountTransaction.objects.create(
                credit_account=credit_account,
                transaction_type='refund',
                amount=amount,
                balance_after=credit_account.outstanding_debt,
                order_id=order_id,
                payment_status='paid',
                description=description
            )
            
            return trans
    
    @staticmethod
    def update_overdue_status():
        """更新逾期状态（定时任务调用）"""
        today = timezone.now().date()
        
        # Find all unpaid transactions past due date
        overdue_transactions = AccountTransaction.objects.filter(
            transaction_type='purchase',
            payment_status='unpaid',
            due_date__lt=today
        )
        
        # Update to overdue status
        count = overdue_transactions.update(payment_status='overdue')
        
        return count


class AccountStatementService:
    """对账单业务逻辑服务"""
    
    @staticmethod
    def generate_statement(credit_account, period_start, period_end):
        """生成对账单"""
        with transaction.atomic():
            # Get previous statement
            previous_statement = AccountStatement.objects.filter(
                credit_account=credit_account,
                period_end__lt=period_start
            ).order_by('-period_end').first()
            
            previous_balance = previous_statement.period_end_balance if previous_statement else Decimal('0.00')
            
            # Get transactions in period
            transactions = AccountTransaction.objects.filter(
                credit_account=credit_account,
                created_at__date__gte=period_start,
                created_at__date__lte=period_end
            )
            
            # Calculate amounts
            current_purchases = sum(
                t.amount for t in transactions if t.transaction_type == 'purchase'
            ) or Decimal('0.00')
            
            current_payments = sum(
                t.amount for t in transactions if t.transaction_type == 'payment'
            ) or Decimal('0.00')
            
            current_refunds = sum(
                t.amount for t in transactions if t.transaction_type == 'refund'
            ) or Decimal('0.00')
            
            period_end_balance = previous_balance + current_purchases - current_payments - current_refunds
            
            # Calculate due tracking
            due_within_term = sum(
                t.amount for t in transactions 
                if t.transaction_type == 'purchase' and t.payment_status == 'unpaid'
            ) or Decimal('0.00')
            
            paid_within_term = sum(
                t.amount for t in transactions 
                if t.transaction_type == 'purchase' and t.payment_status == 'paid'
            ) or Decimal('0.00')
            
            overdue_amount = sum(
                t.amount for t in transactions 
                if t.transaction_type == 'purchase' and t.payment_status == 'overdue'
            ) or Decimal('0.00')
            
            # Create statement
            statement = AccountStatement.objects.create(
                credit_account=credit_account,
                period_start=period_start,
                period_end=period_end,
                previous_balance=previous_balance,
                current_purchases=current_purchases,
                current_payments=current_payments,
                current_refunds=current_refunds,
                period_end_balance=period_end_balance,
                due_within_term=due_within_term,
                paid_within_term=paid_within_term,
                overdue_amount=overdue_amount,
                status='draft'
            )
            
            # Link transactions to statement
            transactions.update(statement=statement)
            
            return statement
    
    @staticmethod
    def confirm_statement(statement):
        """确认对账单"""
        if statement.status != 'draft':
            raise ValueError("只能确认草稿状态的对账单")
        
        statement.status = 'confirmed'
        statement.confirmed_at = timezone.now()
        statement.save()
        
        return statement
    
    @staticmethod
    def settle_statement(statement):
        """结清对账单"""
        if statement.status == 'settled':
            raise ValueError("对账单已结清")
        
        with transaction.atomic():
            statement.status = 'settled'
            statement.settled_at = timezone.now()
            statement.save()
            
            # Update credit account outstanding debt
            credit_account = statement.credit_account
            credit_account.outstanding_debt -= statement.period_end_balance
            if credit_account.outstanding_debt < 0:
                credit_account.outstanding_debt = 0
            credit_account.save()
        
        return statement
