from datetime import date
from flask import current_app
from models.database import execute_query

class Payment:
    ALLOWED_STATUSES = ['pending', 'completed', 'failed', 'refunded'] 
    def __init__(self, id=None, member_id=None, membership_plan_id=None, amount=None,
                 payment_method=None, payment_status='pending', transaction_id=None,
                 payment_date=None, due_date=None, notes=None, created_at=None):
        self.id = id
        self.member_id = member_id
        self.membership_plan_id = membership_plan_id
        self.amount = amount
        self.payment_method = payment_method
        self.payment_status = payment_status
        self.transaction_id = transaction_id
        self.payment_date = payment_date
        self.due_date = due_date
        self.notes = notes
        self.created_at = created_at
    
    @classmethod
    def get_member_payments(cls, member_id):
        """Get all payments for a member"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT p.*, mp.name as plan_name 
                   FROM payments p
                   JOIN membership_plans mp ON p.membership_plan_id = mp.id
                   WHERE p.member_id = ? 
                   ORDER BY p.created_at DESC'''
        results = execute_query(query, (member_id,), db_path, fetch=True)
        
        payments = []
        for row in results:
            payment = cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10]
            )
            payment.plan_name = row[11]  # plan_name
            payments.append(payment)
        return payments
    
    @classmethod
    def get_pending_payments(cls):
        """Get all pending payments"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT p.*, u.full_name as member_name, mp.name as plan_name 
                   FROM payments p
                   JOIN members m ON p.member_id = m.id
                   JOIN users u ON m.user_id = u.id
                   JOIN membership_plans mp ON p.membership_plan_id = mp.id
                   WHERE p.payment_status = 'pending' 
                   ORDER BY p.due_date'''
        results = execute_query(query, (), db_path, fetch=True)
        
        payments = []
        for row in results:
            payment = cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10]
            )
            payment.member_name = row[11]  # full_name
            payment.plan_name = row[12]    # plan_name
            payments.append(payment)
        return payments
    
    @classmethod
    def get_revenue_stats(cls, year=None, month=None):
        """Get revenue statistics"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if year and month:
            query = '''SELECT SUM(amount), COUNT(*) 
                       FROM payments 
                       WHERE payment_status = 'completed' 
                       AND strftime('%Y', payment_date) = ? 
                       AND strftime('%m', payment_date) = ?'''
            params = (str(year), f"{month:02d}")
        elif year:
            query = '''SELECT SUM(amount), COUNT(*) 
                       FROM payments 
                       WHERE payment_status = 'completed' 
                       AND strftime('%Y', payment_date) = ?'''
            params = (str(year),)
        else:
            query = '''SELECT SUM(amount), COUNT(*) 
                       FROM payments 
                       WHERE payment_status = 'completed' '''
            params = ()
        
        result = execute_query(query, params, db_path, fetch=True)
        if result and result[0][0]:
            return {'total_revenue': result[0][0], 'total_payments': result[0][1]}
        return {'total_revenue': 0, 'total_payments': 0}
    
    @classmethod
    def get_by_id(cls, payment_id):
        """Fetch a payment by ID"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        query = '''SELECT * FROM payments WHERE id = ?'''
        result = execute_query(query, (payment_id,), db_path, fetch=True)
        
        if result:
            row = result[0]
            return cls(
                id=row[0], member_id=row[1], membership_plan_id=row[2],
                amount=row[3], payment_method=row[4], payment_status=row[5],
                transaction_id=row[6], payment_date=row[7], due_date=row[8],
                notes=row[9], created_at=row[10]
            )
        return None

    def save(self):
        """Save payment to database"""
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        
        if self.id:
            # Update existing payment
            query = '''UPDATE payments 
                       SET member_id=?, membership_plan_id=?, amount=?, payment_method=?, 
                           payment_status=?, transaction_id=?, payment_date=?, due_date=?, notes=? 
                       WHERE id=?'''
            params = (self.member_id, self.membership_plan_id, self.amount,
                     self.payment_method, self.payment_status, self.transaction_id,
                     self.payment_date, self.due_date, self.notes, self.id)
        else:
            # Create new payment
            query = '''INSERT INTO payments (member_id, membership_plan_id, amount,
                       payment_method, payment_status, transaction_id, payment_date,
                       due_date, notes) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            params = (self.member_id, self.membership_plan_id, self.amount,
                     self.payment_method, self.payment_status, self.transaction_id,
                     self.payment_date, self.due_date, self.notes)
        
        result = execute_query(query, params, db_path)
        if not self.id:
            self.id = result
        return self.id
