from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from dateutil.relativedelta import relativedelta
from models.user import User
from models.member import Member
from models.trainer import Trainer
from models.membership_plan import MembershipPlan
from models.payment import Payment
from models.announcement import Announcement
from models.attendance import Attendance
from models.equipment import Equipment
from utils.decorators import login_required, admin_required
from utils.email_utils import send_welcome_email, send_membership_renewal_reminder
from werkzeug.security import generate_password_hash
from datetime import date, timedelta, datetime
import secrets
import string
import json
from models.workout import Workout
from models.workout_plan import MemberWorkoutPlan, WorkoutPlanDetail


admin_bp = Blueprint('admin', __name__,url_prefix='/admin')

@admin_bp.route('/equipment')
def equipment_list():
    """View all equipment"""
    try:
        equipment = Equipment.get_all()
        return render_template('admin/equipment_list.html', equipment=equipment)
    except Exception as e:
        flash(f"Error loading equipment list: {str(e)}", "danger")
        return render_template('admin/equipment_list.html', equipment=[])
    
@admin_bp.route('/equipment/add', methods=['GET', 'POST'])
def add_equipment():
    """Add new equipment"""
    if request.method == 'POST':
        try:
            equipment = Equipment(
                name=request.form['name'],
                category=request.form.get('category'),
                brand=request.form.get('brand'),
                model=request.form.get('model'),
                purchase_date=request.form.get('purchase_date'),
                warranty_end_date=request.form.get('warranty_end_date'),
                status=request.form.get('status', 'working'),
                location=request.form.get('location')
            )
            equipment.save()
            flash('Equipment added successfully.', 'success')
            return redirect(url_for('admin.equipment_list'))
        except Exception as e:
            flash(f"Error adding equipment: {str(e)}", "danger")
    return render_template('admin/add_equipment.html')

@admin_bp.route('/equipment/edit/<int:equipment_id>', methods=['GET', 'POST'])
def edit_equipment(equipment_id):
    """Edit equipment details"""
    equipment = Equipment.get_by_id(equipment_id)
    if not equipment:
        flash('Equipment not found.', 'danger')
        return redirect(url_for('admin.equipment_list'))

    if request.method == 'POST':
        try:
            equipment.name = request.form['name']
            equipment.category = request.form.get('category')
            equipment.brand = request.form.get('brand')
            equipment.model = request.form.get('model')
            equipment.purchase_date = request.form.get('purchase_date')
            equipment.warranty_end_date = request.form.get('warranty_end_date')
            equipment.status = request.form.get('status', equipment.status)
            equipment.location = request.form.get('location')
            equipment.save()
            flash('Equipment updated successfully.', 'success')
            return redirect(url_for('admin.equipment_list'))
        except Exception as e:
            flash(f"Error updating equipment: {str(e)}", "danger")

    return render_template('admin/edit_equipment.html', equipment=equipment)

@admin_bp.route('/equipment/maintenance/<int:equipment_id>', methods=['POST'])
def update_equipment_status(equipment_id):
    """Update maintenance status of equipment"""
    equipment = Equipment.get_by_id(equipment_id)
    if not equipment:
        flash('Equipment not found.', 'danger')
        return redirect(url_for('admin.equipment_list'))

    try:
        action = request.form.get('action')
        notes = request.form.get('maintenance_notes')
        next_date = request.form.get('next_maintenance_date')

        if action == 'maintenance':
            equipment.mark_for_maintenance(notes=notes, next_date=next_date)
            flash('Equipment marked for maintenance.', 'success')
        elif action == 'working':
            equipment.mark_as_working()
            flash('Equipment marked as working.', 'success')
        elif action == 'out_of_order':
            equipment.mark_out_of_order(notes=notes)
            flash('Equipment marked as out of order.', 'warning')
        else:
            flash('Invalid action.', 'danger')

    except Exception as e:
        flash(f"Error updating status: {str(e)}", "danger")

    return redirect(url_for('admin.equipment_list'))


# -------------------- Dashboard --------------------
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with statistics and overview"""
    try:
        # Get key statistics
        total_members = Member.get_count_active()
        total_trainers = Trainer.get_count_active()
        today_attendance = Attendance.get_todays_attendance()

        # Financial stats
        revenue_stats = Payment.get_revenue_stats()
        monthly_revenue = Payment.get_revenue_stats(year=date.today().year, month=date.today().month)

        # Pending payments
        pending_payments = Payment.get_pending_payments()

        # Equipment stats
        working_equipment = Equipment.get_working_count()
        maintenance_equipment = Equipment.get_maintenance_count()

        # Recent activity
        recent_members = Member.get_recent(5)
        recent_payments = Payment.get_recent(5)

        # Memberships expiring soon
        expiring_memberships = Member.get_expiring_soon(30)

        return render_template(
            'admin/dashboard.html',
            total_members=total_members,
            total_trainers=total_trainers,
            today_attendance=today_attendance,
            total_revenue = revenue_stats.get('total_revenue', 0) if revenue_stats else 0,
            monthly_revenue = monthly_revenue.get('total_revenue', 0) if monthly_revenue else 0,

            pending_payments=len(pending_payments),
            working_equipment=working_equipment,
            maintenance_equipment=maintenance_equipment,
            recent_members=recent_members,
            recent_payments=recent_payments,
            expiring_memberships=expiring_memberships
        )
    except Exception as e:
        flash('Error loading dashboard data.')
        return render_template(
            'admin/dashboard.html',
            total_members=0, total_trainers=0, today_attendance=0,
            total_revenue=0, monthly_revenue=0, pending_payments=0,
            working_equipment=0, maintenance_equipment=0,
            recent_members=[], recent_payments=[], expiring_memberships=[]
        )

# -------------------- Members --------------------
@admin_bp.route('/members')
@admin_required
def members():
    members = Member.get_all_with_details()
    membership_plans = MembershipPlan.get_all_active()
    trainers = Trainer.get_all_active()
    return render_template('admin/members.html', members=members,
                           membership_plans=membership_plans, trainers=trainers)

@admin_bp.route('/members/add')
@admin_required
def add_member_form():
    membership_plans = MembershipPlan.get_all_active()
    trainers = Trainer.get_all_active()
    return render_template('admin/add_member.html',
                           membership_plans=membership_plans, trainers=trainers)

@admin_bp.route('/members/add', methods=['POST'])
@admin_required
def add_member():
    """Add new member"""
    try:
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        membership_plan_id = request.form.get('membership_plan_id')
        trainer_id = request.form.get('trainer_id') or None

        # Optional
        emergency_contact = request.form.get('emergency_contact')
        emergency_phone = request.form.get('emergency_phone')
        address = request.form.get('address')
        date_of_birth = request.form.get('date_of_birth') or None
        weight = request.form.get('weight') or None
        height = request.form.get('height') or None
        medical_conditions = request.form.get('medical_conditions')
        fitness_goals = request.form.get('fitness_goals')

        if not all([full_name, email, phone, membership_plan_id]):
            flash('Please fill in all required fields!')
            return redirect(url_for('admin.add_member_form'))

        # Username & password
        username = email.split('@')[0].lower()
        counter = 1
        original_username = username
        while User.get_by_username(username):
            username = f"{original_username}{counter}"
            counter += 1

        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(temp_password),
            role='member',
            full_name=full_name,
            phone=phone
        )
        user_id = user.save()
        if not user_id:
            flash('Error creating user account!')
            return redirect(url_for('admin.add_member_form'))

        # Membership dates
        plan = MembershipPlan.get_by_id(membership_plan_id)
        if not plan:
            flash('Invalid membership plan selected!')
            return redirect(url_for('admin.add_member_form'))

        start_date = date.today()
        end_date = start_date + relativedelta(months=plan.duration_months)

        # Member profile
        member = Member(
            user_id=user_id,
            membership_plan_id=membership_plan_id,
            phone=phone,
            emergency_contact=emergency_contact,
            emergency_phone=emergency_phone,
            address=address,
            date_of_birth=date_of_birth,
            weight=float(weight) if weight else None,
            height=float(height) if height else None,
            medical_conditions=medical_conditions,
            fitness_goals=fitness_goals,
            membership_start_date=start_date,
            membership_end_date=end_date,
            trainer_id=int(trainer_id) if trainer_id else None
        )
        member_id = member.save()

        if member_id:
            # Initial payment
            payment = Payment(
                member_id=member_id,
                membership_plan_id=membership_plan_id,
                amount=plan.price,
                payment_method='cash',
                payment_status='pending',
                due_date=start_date
            )
            payment.save()

            # Welcome email
            try:
                send_welcome_email(user.email, user.full_name, username, temp_password)
            except Exception as e:
                current_app.logger.error(f"Failed to send welcome email to {user.email}: {e}")

            flash(f'Member {full_name} added successfully! Temporary password: {temp_password}')
        else:
            flash('Error creating member profile!')

    except Exception as e:
        flash(f'An error occurred while adding the member: {str(e)}')

    return redirect(url_for('admin.members'))

@admin_bp.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
def edit_member(member_id):
    member = Member.get_by_id(member_id)
    if not member:
        flash("Member not found!", "danger")
        return redirect(url_for("admin.list_members"))

    user = User.get_by_id(member.user_id)

    if request.method == "POST":
        try:
            # Update user details
            user.full_name = request.form.get("full_name")
            user.email = request.form.get("email")
            user.phone = request.form.get("phone")
            user.update()

            # Update member details
            member.weight = request.form.get("weight")
            member.height = request.form.get("height")
            member.membership_start_date = request.form.get("membership_start_date")
            member.membership_end_date = request.form.get("membership_end_date")
            member.status = request.form.get("status")
            member.update()

            flash("Member details updated successfully!", "success")
            return redirect(url_for("admin.list_members"))

        except Exception as e:
            flash("Error updating member. Please try again.", "danger")
            print("Error:", e)

    return render_template("admin/edit_member.html", member=member, user=user)
# -------------------- Trainers --------------------
@admin_bp.route('/trainers')
@admin_required
def trainers():
    trainers = Trainer.get_all_with_details()
    return render_template('admin/trainers.html', trainers=trainers)

@admin_bp.route('/trainers/add')
@admin_required
def add_trainer_form():
    return render_template('admin/add_trainer.html')

@admin_bp.route('/trainers/add', methods=['POST'])
@admin_required
def add_trainer():
    try:
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        specialization = request.form.get('specialization')
        experience_years = request.form.get('experience_years')
        certification = request.form.get('certification')
        salary = request.form.get('salary')
        working_hours = request.form.get('working_hours')
        bio = request.form.get('bio')

        if not all([full_name, email, phone, specialization]):
            flash('Please fill in all required fields!')
            return redirect(url_for('admin.add_trainer_form'))

        username = email.split('@')[0].lower()
        counter = 1
        original_username = username
        while User.get_by_username(username):
            username = f"{original_username}{counter}"
            counter += 1

        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(temp_password),
            role='trainer',
            full_name=full_name,
            phone=phone
        )
        user_id = user.save()
        if not user_id:
            flash('Error creating user account!')
            return redirect(url_for('admin.add_trainer_form'))

        trainer = Trainer(
            user_id=user_id,
            phone=phone,
            specialization=specialization,
            experience_years=int(experience_years) if experience_years else None,
            certification=certification,
            salary=float(salary) if salary else None,
            working_hours=working_hours,
            bio=bio
        )
        trainer_id = trainer.save()

        if trainer_id:
            try:
                send_welcome_email(email, full_name, username, temp_password)
            except Exception as e:
                print(f"Failed to send welcome email: {e}")

            flash(f'Trainer {full_name} added successfully! Temporary password: {temp_password}')
        else:
            flash('Error creating trainer profile!')

    except Exception as e:
        flash(f'An error occurred while adding the trainer: {str(e)}')

    return redirect(url_for('admin.trainers'))

# -------------------- Membership Plans --------------------
@admin_bp.route('/membership-plans')
@admin_required
def membership_plans():
    plans = MembershipPlan.get_all()
    return render_template('admin/membership_plans.html', plans=plans)

@admin_bp.route('/membership-plans/add', methods=['GET', 'POST'])
@admin_required
def add_membership_plan():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            duration_months = int(request.form.get('duration_months'))
            price = float(request.form.get('price'))
            features = request.form.getlist('features')
            features = json.dumps(features) if features else "[]"

            if not all([name, duration_months, price]):
                flash('Please fill in all required fields!')
                return redirect(url_for('admin.add_membership_plan'))

            plan = MembershipPlan(
                name=name,
                description=description,
                duration_months=duration_months,
                price=price,
                features=str(features)
            )

            plan_id = plan.save()
            if plan_id:
                flash(f'Membership plan "{name}" created successfully!')
            else:
                flash('Error creating membership plan!')

        except Exception as e:
            flash(f'An error occurred: {str(e)}')

        return redirect(url_for('admin.membership_plans'))

    return render_template('admin/add_membership_plan.html')

@admin_bp.route('/workouts')
@admin_required
def workouts():
    workouts = Workout.get_all()
    return render_template('admin/workouts.html', workouts=workouts)

@admin_bp.route('/workouts/add', methods=['GET', 'POST'])
@admin_required
def add_workout():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            category = request.form.get('category')
            equipment_needed = request.form.get('equipment_needed')

            if not name:
                flash('Workout name is required!')
                return redirect(url_for('admin.add_workout'))

            workout = Workout(
                name=name,
                description=description,
                category=category,
                equipment_needed=equipment_needed
            )
            workout_id = workout.save()
            if workout_id:
                flash(f'Workout "{name}" added successfully!')
            else:
                flash('Error adding workout!')
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
        return redirect(url_for('admin.workouts'))

    return render_template('admin/add_workout.html')

@admin_bp.route('/workout-plans')
@admin_required
def workout_plans():
    plans = MemberWorkoutPlan.get_all_with_details()
    members = Member.get_all_active()
    trainers = Trainer.get_all_active()
    return render_template('admin/workout_plans.html', plans=plans,
                           members=members, trainers=trainers)

@admin_bp.route('/workout-plans/add', methods=['GET', 'POST'])
@admin_required
def add_workout_plan():
    if request.method == 'POST':
        try:
            member_id = request.form.get('member_id')
            trainer_id = request.form.get('trainer_id')
            name = request.form.get('name')
            description = request.form.get('description')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')

            if not all([member_id, trainer_id, name]):
                flash('Member, Trainer and Plan Name are required!')
                return redirect(url_for('admin.add_workout_plan'))

            plan = MemberWorkoutPlan(
                member_id=member_id,
                trainer_id=trainer_id,
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date
            )
            plan_id = plan.save()
            if plan_id:
                flash(f'Workout Plan "{name}" created successfully!')
            else:
                flash('Error creating workout plan!')
        except Exception as e:
            flash(f'An error occurred: {str(e)}')

        return redirect(url_for('admin.workout_plans'))

    members = Member.get_all_active()
    trainers = Trainer.get_all_active()
    return render_template('admin/add_workout_plan.html',
                           members=members, trainers=trainers)

@admin_bp.route('/workout-plans/<int:plan_id>/add-detail', methods=['GET', 'POST'])
@admin_required
def add_workout_plan_detail(plan_id):
    if request.method == 'POST':
        try:
            workout_id = request.form.get('workout_id')
            day_of_week = request.form.get('day_of_week')
            sets = request.form.get('sets')
            reps = request.form.get('reps')
            weight = request.form.get('weight')
            rest_seconds = request.form.get('rest_seconds')
            notes = request.form.get('notes')

            if not workout_id:
                flash('Workout is required!')
                return redirect(url_for('admin.add_workout_plan_detail', plan_id=plan_id))

            detail = WorkoutPlanDetail(
                plan_id=plan_id,
                workout_id=workout_id,
                day_of_week=day_of_week,
                sets=sets,
                reps=reps,
                weight=weight,
                rest_seconds=rest_seconds,
                notes=notes
            )
            detail_id = detail.save()
            if detail_id:
                flash('Workout detail added successfully!')
            else:
                flash('Error adding workout detail!')
        except Exception as e:
            flash(f'An error occurred: {str(e)}')

        return redirect(url_for('admin.workout_plans'))

    workouts = Workout.get_all()
    return render_template('admin/add_workout_plan_detail.html',
                           workouts=workouts, plan_id=plan_id)


# -------------------- Payments --------------------
@admin_bp.route('/payments')
@admin_required
def payments():
    payments = Payment.get_all_with_details()
    pending_payments = Payment.get_pending_payments()
    return render_template('admin/payments.html',
                           payments=payments,
                           pending_payments=pending_payments)

@admin_bp.route('/payments/<int:payment_id>/update', methods=['POST'])
@admin_required
def update_payment_status(payment_id):
    """Update payment status"""
    new_status = request.form.get('status')

    if new_status not in ['pending', 'completed', 'failed', 'refunded']:
        flash('Invalid payment status!')
        return redirect(url_for('admin.payments'))

    try:
        payment = Payment.get_by_id(payment_id)
        if payment:
            payment.payment_status = new_status
            if new_status == 'completed':
                payment.payment_date = date.today()
            payment.save()
            flash('Payment status updated successfully!')
        else:
            flash('Payment not found!')
    except Exception as e:
        flash(f'Error updating payment: {str(e)}')

    return redirect(url_for('admin.payments'))

# -------------------- Announcements --------------------
@admin_bp.route('/announcements')
@admin_required
def announcements():
    announcements = Announcement.get_all()
    return render_template('admin/announcements.html', announcements=announcements)

@admin_bp.route('/announcements/add', methods=['GET', 'POST'])
@admin_required
def add_announcement():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            content = request.form.get('content')
            announcement_type = request.form.get('announcement_type')
            target_audience = request.form.get('target_audience')
            is_public = request.form.get('is_public') in ['on', '1', 'true', 'True']
            start_date = request.form.get('start_date')
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            end_date = request.form.get('end_date')
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            if not all([title, content, announcement_type, target_audience]):
                flash('Please fill in all required fields!')
                return redirect(url_for('admin.add_announcement'))

            announcement = Announcement(
                title=title,
                content=content,
                announcement_type=announcement_type,
                target_audience=target_audience,
                is_public=is_public,
                start_date=start_date,
                end_date=end_date,
                created_by=session['user_id']
            )

            announcement_id = announcement.save()
            if announcement_id:
                flash(f'Announcement "{title}" created successfully!')
            else:
                flash('Error creating announcement!')

        except Exception as e:
            flash(f'An error occurred: {str(e)}')

        return redirect(url_for('admin.announcements'))

    return render_template('admin/add_announcement.html')

# -------------------- Reports --------------------
@admin_bp.route('/reports')
@admin_required
def reports():
    member_stats = Member.get_statistics()
    revenue_stats = Payment.get_revenue_stats()
    attendance_stats = Attendance.get_monthly_stats(date.today().year, date.today().month)

    return render_template('admin/reports.html',
                           member_stats=member_stats,
                           revenue_stats=revenue_stats,
                           attendance_stats=attendance_stats)

# -------------------- Renewal Reminders --------------------
@admin_bp.route('/send-renewal-reminders', methods=['POST'])
@admin_required
def send_renewal_reminders():
    try:
        expiring_members = Member.get_expiring_soon(30)
        sent_count = 0

        for member in expiring_members:
            days_remaining = (member.membership_end_date - date.today()).days
            try:
                send_membership_renewal_reminder(
                    member.email,
                    member.full_name,
                    member.membership_end_date.strftime('%Y-%m-%d'),
                    days_remaining
                )
                sent_count += 1
            except Exception as e:
                print(f"Failed to send reminder to {member.email}: {e}")

        flash(f'Renewal reminders sent to {sent_count} members!')

    except Exception as e:
        flash(f'Error sending renewal reminders: {str(e)}')

    return redirect(url_for('admin.dashboard'))
@admin_bp.route('/members/<int:member_id>/renew', methods=['GET', 'POST'])
@admin_required
def renew_membership(member_id):
    """Admin: renew a member's plan. Membership dates extend ONLY if payment is completed."""
    # Fetch member
    member = Member.get_by_id(member_id)
    if not member:
        flash('Member not found!', 'danger')
        return redirect(url_for('admin.members'))

    if request.method == 'POST':
        try:
            # Required form fields
            plan_id = request.form.get('membership_plan_id')
            payment_method = request.form.get('payment_method', 'cash')  # e.g. cash/upi/card/online
            payment_status = request.form.get('payment_status', 'completed')  # 'completed' or 'pending'
            amount_str = request.form.get('amount')  # optional override of price

            # Validate plan
            plan = MembershipPlan.get_by_id(plan_id)
            if not plan:
                flash('Invalid membership plan selected!', 'danger')
                return redirect(url_for('admin.renew_membership', member_id=member_id))

            amount = float(amount_str) if amount_str else float(plan.price)

            # Create/record payment first
            payment = Payment(
                member_id=member.id,
                membership_plan_id=int(plan_id),
                amount=amount,
                payment_method=payment_method,
                payment_status=payment_status,
                due_date=date.today()  # adjust if you prefer a specific due date
            )
            if payment_status == 'completed':
                payment.payment_date = date.today()

            payment_id = payment.save()
            if not payment_id:
                flash('Could not create payment record.', 'danger')
                return redirect(url_for('admin.renew_membership', member_id=member_id))

            # Extend membership ONLY if payment is completed
            if payment_status == 'completed':
                # Start next period right after current end if active; otherwise start today
                if member.membership_end_date and member.membership_end_date >= date.today():
                    start_date = member.membership_end_date + timedelta(days=1)
                else:
                    start_date = date.today()

                end_date = start_date + relativedelta(months=plan.duration_months)

                member.membership_plan_id = int(plan_id)
                member.membership_start_date = start_date
                member.membership_end_date = end_date
                member.status = 'active'
                member.save()

                flash(f'Membership renewed successfully until {end_date}.', 'success')
            else:
                flash('Pending payment created. Membership will renew after payment is completed.', 'info')

            return redirect(url_for('admin.members'))

        except Exception as e:
            current_app.logger.exception('Error processing membership renewal')
            flash('Error processing renewal. Please try again.', 'danger')
            return redirect(url_for('admin.renew_membership', member_id=member_id))

    # GET → show renewal form
    plans = MembershipPlan.get_all_active()
    return render_template(
        'admin/renew_member.html',
        member=member,
        plans=plans
    )
