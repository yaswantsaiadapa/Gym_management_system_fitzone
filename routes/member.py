from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.member import Member
from utils.decorators import login_required
from utils.helpers import calculate_expiry_date
from datetime import date

member_bp = Blueprint('member', __name__)

@member_bp.route('/join_member')
@login_required
def join_member():
    """Display join member form"""
    return render_template('join_member.html')

@member_bp.route('/join_member', methods=['POST'])
@login_required
def join_member_post():
    """Process join member form"""
    try:
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        weight = float(request.form.get('weight'))
        height = float(request.form.get('height'))
        payment_status = request.form.get('payment_status')
        
        # Validate required fields
        if not all([name, phone, email, weight, height, payment_status]):
            flash('All fields are required!')
            return redirect(url_for('member.join_member'))
        
        if payment_status == 'done':
            membership_date = date.today()
            expiry_date = calculate_expiry_date(membership_date)
            
            member = Member(
                name=name,
                phone=phone,
                email=email,
                weight=weight,
                height=height,
                payment_status=payment_status,
                membership_date=membership_date,
                expiry_date=expiry_date
            )
            
            member_id = member.save()
            if member_id:
                flash(f'Member {name} added successfully!')
            else:
                flash('Error adding member. Please try again.')
        else:
            flash('Payment not completed. Member not added.')
            
    except ValueError as e:
        flash('Please enter valid numeric values for weight and height.')
    except Exception as e:
        flash('An error occurred while adding the member.')
    
    return redirect(url_for('dashboard.index'))

@member_bp.route('/renew_membership')
@login_required
def renew_membership():
    """Display renew membership form"""
    members = Member.get_all_active()
    return render_template('renew_membership.html', members=members)

@member_bp.route('/renew_membership', methods=['POST'])
@login_required
def renew_membership_post():
    """Process renew membership form"""
    try:
        member_id = int(request.form.get('member_id'))
        payment_status = request.form.get('payment_status')
        
        if not member_id or not payment_status:
            flash('Please select a member and payment status!')
            return redirect(url_for('member.renew_membership'))
        
        if payment_status == 'done':
            member = Member.get_by_id(member_id)
            if member:
                new_expiry = calculate_expiry_date(date.today())
                member.renew_membership(new_expiry, payment_status)
                flash(f'Membership renewed successfully for {member.name}!')
            else:
                flash('Member not found!')
        else:
            flash('Payment not completed. Membership not renewed.')
            
    except ValueError:
        flash('Invalid member selected.')
    except Exception as e:
        flash('An error occurred while renewing membership.')
    
    return redirect(url_for('dashboard.index'))

@member_bp.route('/list_members')
@login_required
def list_members():
    """Display all active members"""
    members = Member.get_all_active()
    return render_template('list_members.html', members=members)

@member_bp.route('/member_details/<int:member_id>')
@login_required
def member_details(member_id):
    """Display detailed member information"""
    member = Member.get_by_id(member_id)
    if not member:
        flash('Member not found!')
        return redirect(url_for('member.list_members'))
    
    attendance_records = member.get_attendance_history()
    return render_template('member_details.html', 
                         member=member, 
                         attendance_records=attendance_records)