from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import date, datetime, timedelta
from models.user import User
from models.member import Member
from models.membership_plan import MembershipPlan
from models.payment import Payment
from utils.decorators import login_required, admin_required

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/process')
@login_required
@admin_required
def process_payment():
    """Display payment processing form"""
    members = Member.get_all_active()
    membership_plans = MembershipPlan.get_all_active()
    return render_template('payment/process.html', 
                         members=members,
                         membership_plans=membership_plans)

@payment_bp.route('/process', methods=['POST'])
@login_required
@admin_required
def process_payment_post():
    """Process payment"""
    try:
        member_id = request.form.get('member_id')
        membership_plan_id = request.form.get('membership_plan_id')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        transaction_id = request.form.get('transaction_id')
        due_date = request.form.get('due_date')
        notes = request.form.get('notes')
        
        if not all([member_id, membership_plan_id, amount, payment_method]):
            flash('All required fields must be filled')
            return redirect(url_for('payment.process_payment'))
        
        # Create payment record
        payment = Payment(
            member_id=int(member_id),
            membership_plan_id=int(membership_plan_id),
            amount=float(amount),
            payment_method=payment_method,
            payment_status='completed',
            transaction_id=transaction_id,
            payment_date=date.today(),
            due_date=datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None,
            notes=notes
        )
        
        payment_id = payment.save()
        if payment_id:
            # Update member's membership dates
            member = Member.get_by_id(member_id)
            membership_plan = MembershipPlan.get_by_id(membership_plan_id)
            
            if member and membership_plan:
                # Extend membership
                current_end = member.membership_end_date or date.today()
                new_end = current_end + timedelta(days=membership_plan.duration_months * 30)
                member.membership_end_date = new_end
                member.status = 'active'
                member.save()
                
            flash('Payment processed successfully!')
        else:
            flash('Error processing payment')
            
    except Exception as e:
        flash('Error processing payment')
    
    return redirect(url_for('admin.manage_payments'))

@payment_bp.route('/pending')
@login_required
@admin_required
def pending_payments():
    """View all pending payments"""
    pending_payments = Payment.get_pending_payments()
    return render_template('payment/pending.html', pending_payments=pending_payments)

@payment_bp.route('/history')
@login_required
def payment_history():
    """View payment history"""
    # Different views based on user role
    if session.get('role') == 'admin':
        # Admin can see all payments
        payments = Payment.get_all_payments() if hasattr(Payment, 'get_all_payments') else []
    elif session.get('role') == 'member':
        # Member can see their own payments
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)
        payments = Payment.get_member_payments(member.id) if member else []
    else:
        flash('Access denied')
        return redirect(url_for('dashboard.index'))
    
    return render_template('payment/history.html', payments=payments)

@payment_bp.route('/<int:payment_id>/update_status', methods=['POST'])
@login_required
@admin_required
def update_payment_status(payment_id):
    """Update payment status"""
    new_status = request.form.get('status')
    
    if new_status not in ['completed', 'failed', 'refunded']:
        flash('Invalid payment status')
        return redirect(url_for('payment.pending_payments'))
    
    # Get payment record (would need to extend Payment model)
    payment = Payment.get_by_id(payment_id) if hasattr(Payment, 'get_by_id') else None
    
    if not payment:
        flash('Payment not found')
        return redirect(url_for('payment.pending_payments'))
    
    payment.payment_status = new_status
    payment.save()
    
    flash(f'Payment status updated to {new_status}!')
    return redirect(url_for('payment.pending_payments'))

@payment_bp.route('/generate_invoice/<int:payment_id>')
@login_required
def generate_invoice(payment_id):
    """Generate invoice for payment"""
    payment = Payment.get_by_id(payment_id) if hasattr(Payment, 'get_by_id') else None
    
    if not payment:
        flash('Payment not found')
        return redirect(url_for('payment.history'))
    
    # Check access permissions
    if session.get('role') == 'member':
        user_id = session['user_id']
        member = Member.get_by_user_id(user_id)
        if not member or payment.member_id != member.id:
            flash('Access denied')
            return redirect(url_for('payment.history'))
    
    member = Member.get_by_id(payment.member_id)
    membership_plan = MembershipPlan.get_by_id(payment.membership_plan_id)
    
    return render_template('payment/invoice.html',
                         payment=payment,
                         member=member,
                         membership_plan=membership_plan)

@payment_bp.route('/reports')
@login_required
@admin_required
def payment_reports():
    """Payment reports and analytics"""
    # Get date range from request
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start = date.today() - timedelta(days=30)
        end = date.today()
    
    # Get revenue statistics
    current_month = date.today()
    monthly_revenue = Payment.get_revenue_stats(current_month.year, current_month.month)
    yearly_revenue = Payment.get_revenue_stats(current_month.year)
    
    return render_template('payment/reports.html',
                         monthly_revenue=monthly_revenue,
                         yearly_revenue=yearly_revenue,
                         start_date=start,
                         end_date=end)

@payment_bp.route('/api/revenue_chart')
@login_required
@admin_required
def revenue_chart_data():
    """API endpoint for revenue chart data"""
    try:
        # Get monthly revenue for the past 12 months
        today = date.today()
        chart_data = []
        
        for i in range(12):
            month_date = today - timedelta(days=i*30)
            revenue_data = Payment.get_revenue_stats(month_date.year, month_date.month)
            chart_data.append({
                'month': month_date.strftime('%b %Y'),
                'revenue': revenue_data.get('total_revenue', 0),
                'payments': revenue_data.get('total_payments', 0)
            })
        
        return jsonify(chart_data)
    except Exception as e:
        return jsonify({'error': 'Failed to load chart data'}), 500