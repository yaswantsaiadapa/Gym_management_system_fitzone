from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
import traceback
from models.database import execute_query

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
# removed werkzeug import; using bcrypt instead
from flask_bcrypt import Bcrypt
from datetime import date, timedelta, datetime
import secrets
import string
import json
from models.workout import Workout
from models.workout_plan import MemberWorkoutPlan, WorkoutPlanDetail
def table_exists(table_name, db_path):
    res = execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table_name,), db_path, fetch=True)
    return bool(res)

def column_exists(table_name, column_name, db_path):
    try:
        rows = execute_query(f"PRAGMA table_info({table_name})", (), db_path, fetch=True)
        cols = [r['name'] if isinstance(r, dict) else r[1] for r in rows]
        return column_name in cols
    except Exception:
        return False

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
        flash(f"Error updating status: {str(e)}", 'danger')

    return redirect(url_for('admin.equipment_list'))


# -------------------- Dashboard --------------------
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with statistics and overview"""
    try:
    # Auto-process pending payments (send reminders and cancel expired ones)
    # Safe to call on dashboard load for small DBs. Remove if you prefer cron-only.
        try:
            Payment.process_pending_payments(reminder_before_days=5)
        except Exception as e:
            current_app.logger.warning(f"Auto-processing pending payments failed: {e}")
    except Exception:
        pass
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
        expiring_memberships = Member.get_expiring_soon(15)

        # 🔹 Get recent announcements (latest 5)
        announcements = Announcement.get_all()[:5]

        return render_template(
            'admin/dashboard.html',
            total_members=total_members,
            total_trainers=total_trainers,
            today_attendance=today_attendance,
            total_revenue=revenue_stats.get('total_revenue', 0) if revenue_stats else 0,
            monthly_revenue=monthly_revenue.get('total_revenue', 0) if monthly_revenue else 0,
            pending_payments=len(pending_payments),
            working_equipment=working_equipment,
            maintenance_equipment=maintenance_equipment,
            recent_members=recent_members,
            recent_payments=recent_payments,
            expiring_memberships=expiring_memberships,
            announcements=announcements   # 🔹 pass to template
        )
    except Exception as e:
        print("\n--- DASHBOARD ERROR ---")
        print("Error:", e)
        traceback.print_exc()
        print("--- END ERROR ---\n")
        flash('Error loading dashboard data. Check logs for details.')
        return render_template(
            'admin/dashboard.html',
            total_members=0, total_trainers=0, today_attendance=0,
            total_revenue=0, monthly_revenue=0, pending_payments=0,
            working_equipment=0, maintenance_equipment=0,
            recent_members=[], recent_payments=[], expiring_memberships=[],
            announcements=[]   # 🔹 empty list fallback
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
    trainers = Trainer.get_all_with_details()
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
        while User.get_by_username_or_email(username):
            username = f"{original_username}{counter}"
            counter += 1

        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

        # Create user
        # Use bcrypt only to hash temp_password
        bcrypt = getattr(current_app, 'bcrypt', None)
        if not bcrypt:
            bcrypt = Bcrypt(current_app)
        temp_hashed = bcrypt.generate_password_hash(temp_password)
        if isinstance(temp_hashed, bytes):
            temp_hashed = temp_hashed.decode('utf-8')

        user = User(
            username=username,
            email=email,
            password_hash=temp_hashed,
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
            membership_status='pending_payment',   # <- NEW field
            trainer_id=int(trainer_id) if trainer_id else None
        )
        member_id = member.save()

        if member_id:
            # Initial pending payment (due in 15 days)
            payment_due = start_date + timedelta(days=15)
            payment = Payment(
                member_id=member_id,
                membership_plan_id=membership_plan_id,
                amount=plan.price,
                payment_method=request.form.get('payment_method', 'cash'),
                payment_status='pending',
                due_date=payment_due
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

        # Use bcrypt only to hash temp_password
        bcrypt = getattr(current_app, 'bcrypt', None)
        if not bcrypt:
            bcrypt = Bcrypt(current_app)
        password_hashed = bcrypt.generate_password_hash(temp_password)
        if isinstance(password_hashed, bytes):
            password_hashed = password_hashed.decode('utf-8')

        user = User(
            username=username,
            email=email,
            password_hash=password_hashed,
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

@admin_bp.route("/members/<int:member_id>/delete", methods=["GET"])
@admin_required
def confirm_delete_member(member_id):
    member = Member.get_by_id(member_id)
    if not member:
        flash("Member not found.", "danger")
        return redirect(url_for("admin.members"))
    return render_template("admin/confirm_delete_member.html", member=member)

@admin_bp.route("/members/<int:member_id>/delete", methods=["POST"])
@admin_required
def delete_member(member_id):
    """
    Safe deletion handler:
     - If force=1 -> try to permanently remove rows from tables that contain member_id
     - If not force -> perform soft-delete (disable user, mark member removed)
    This implementation checks table existence and column presence before running DELETE,
    to avoid sqlite OperationalError for missing tables or different schema.
    """
    force = request.form.get("force", "0") == "1"
    member = Member.get_by_id(member_id)
    if not member:
        flash("Member not found.", "danger")
        return redirect(url_for("admin.members"))

    db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")

    try:
        if not force:
            # Soft-delete (non-destructive)
            if hasattr(member, "delete"):
                ok = member.delete()
            else:
                execute_query("UPDATE users SET is_active = 0 WHERE id = ?", (member.user_id,), db_path)
                execute_query("UPDATE members SET membership_status = ? WHERE id = ?", ("removed", member_id), db_path)
                ok = True

            if ok:
                flash(f"Member {getattr(member, 'full_name', member_id)} deactivated.", "success")
            else:
                flash("Failed to deactivate member. See logs.", "danger")
            return redirect(url_for("admin.members"))

        # If force -> destructive delete, but only on tables that exist and have member_id column.
        # List of candidate tables to try (ordered roughly by likely relationships).
        candidate_tables = [
            "payments",
            "attendance",
            "member_progress",
            "member_workout_plans",
            "member_workout_plans",    # repeated safe
            "member_workout_plans",    # harmless duplicates ok
            "diet_plans",
            "diet_plan_meals",
            # skip workout_plan tables that don't reference member directly
            # "workout_plan_details",
            # "workouts",
        ]

        # Helper: check table existence
        def table_exists(table_name):
            q = "SELECT name FROM sqlite_master WHERE type='table' AND name = ?"
            res = execute_query(q, (table_name,), db_path, fetch=True)
            return bool(res)

        # Helper: check if column exists in table
        def column_exists(table_name, column_name):
            try:
                res = execute_query(f"PRAGMA table_info({table_name})", (), db_path, fetch=True)
                cols = [r['name'] if isinstance(r, dict) else r[1] for r in res]
                return column_name in cols
            except Exception:
                return False

        # Run deletes only on tables that exist and have 'member_id' column
        deleted_summary = []
        for tbl in candidate_tables:
            if not table_exists(tbl):
                current_app.logger.debug("Skipping delete: table not found: %s", tbl)
                continue
            # prefer 'member_id' but some tables might use 'member' or 'members_id' — check common variants
            col = None
            for candidate_col in ("member_id", "memberid", "members_id", "member"):
                if column_exists(tbl, candidate_col):
                    col = candidate_col
                    break
            if not col:
                current_app.logger.debug("Table %s exists but no member_id-like column; skipping", tbl)
                continue

            # perform delete
            try:
                execute_query(f"DELETE FROM {tbl} WHERE {col} = ?", (member_id,), db_path)
                deleted_summary.append(tbl)
            except Exception:
                current_app.logger.exception("Failed to delete rows from %s for member %s", tbl, member_id)

        # Finally remove member row and user row if present
        if table_exists("members"):
            try:
                execute_query("DELETE FROM members WHERE id = ?", (member_id,), db_path)
                deleted_summary.append("members")
            except Exception:
                current_app.logger.exception("Failed to delete members row %s", member_id)

        if getattr(member, "user_id", None):
            # deactivate or delete user row
            try:
                execute_query("DELETE FROM users WHERE id = ?", (member.user_id,), db_path)
                deleted_summary.append("users")
            except Exception:
                current_app.logger.exception("Failed to delete user row for member %s", member_id)

        flash(f"Member {getattr(member, 'full_name', member_id)} permanently deleted (tables affected: {', '.join(deleted_summary)})", "success")
    except Exception:
        current_app.logger.exception("Error deleting member %s", member_id)
        flash("An error occurred while deleting the member. See logs.", "danger")

    return redirect(url_for("admin.members"))


# -------- Trainer delete / confirm --------
@admin_bp.route("/trainers/<int:trainer_id>/delete", methods=["GET"])
@admin_required
def confirm_delete_trainer(trainer_id):
    trainer = Trainer.get_by_id(trainer_id)
    if not trainer:
        flash("Trainer not found.", "danger")
        return redirect(url_for("admin.trainers"))
    return render_template("admin/confirm_delete_trainer.html", trainer=trainer)

@admin_bp.route("/trainers/<int:trainer_id>/delete", methods=["POST"])
@admin_required
def delete_trainer(trainer_id):
    force = request.form.get("force", "0") == "1"
    trainer = Trainer.get_by_id(trainer_id)
    if not trainer:
        flash("Trainer not found.", "danger")
        return redirect(url_for("admin.trainers"))

    db_path = current_app.config.get("DATABASE_PATH", "gym_management.db")

    if not force:
        if hasattr(trainer, "delete"):
            ok = trainer.delete()
        else:
            if table_exists("users", db_path) and getattr(trainer, "user_id", None):
                execute_query("UPDATE users SET is_active = 0 WHERE id = ?", (trainer.user_id,), db_path)
            if table_exists("trainers", db_path):
                execute_query("UPDATE trainers SET status = ? WHERE id = ?", ("removed", trainer_id), db_path)
            ok = True

        flash(f"Trainer {getattr(trainer,'full_name',trainer_id)} deactivated." if ok else "Failed to deactivate trainer.", "success" if ok else "danger")
        return redirect(url_for("admin.trainers"))

    # force -> permanent delete (schema-aware)
    deleted = []
    try:
        # member_workout_plans (remove assignments)
        if table_exists("member_workout_plans", db_path) and column_exists("member_workout_plans", "trainer_id", db_path):
            execute_query("DELETE FROM member_workout_plans WHERE trainer_id = ?", (trainer_id,), db_path)
            deleted.append("member_workout_plans")

        # diet_plans assigned to this trainer (if trainer owns them)
        if table_exists("diet_plans", db_path) and column_exists("diet_plans", "trainer_id", db_path):
            # if diet_plan_meals exists, cleanup meals first
            plans = execute_query("SELECT id FROM diet_plans WHERE trainer_id = ?", (trainer_id,), db_path, fetch=True)
            plan_ids = [r['id'] if isinstance(r, dict) else r[0] for r in plans] if plans else []
            if plan_ids and table_exists("diet_plan_meals", db_path) and column_exists("diet_plan_meals", "diet_plan_id", db_path):
                for pid in plan_ids:
                    execute_query("DELETE FROM diet_plan_meals WHERE diet_plan_id = ?", (pid,), db_path)
                deleted.append("diet_plan_meals")
            execute_query("DELETE FROM diet_plans WHERE trainer_id = ?", (trainer_id,), db_path)
            deleted.append("diet_plans")

        # attendance rows where trainer was present/assigned
        if table_exists("attendance", db_path) and column_exists("attendance", "trainer_id", db_path):
            execute_query("DELETE FROM attendance WHERE trainer_id = ?", (trainer_id,), db_path)
            deleted.append("attendance")

        # finally remove trainer row and user row
        if table_exists("trainers", db_path):
            execute_query("DELETE FROM trainers WHERE id = ?", (trainer_id,), db_path)
            deleted.append("trainers")
        if getattr(trainer, "user_id", None) and table_exists("users", db_path):
            execute_query("DELETE FROM users WHERE id = ?", (trainer.user_id,), db_path)
            deleted.append("users")

        flash(f"Trainer permanently deleted (tables affected: {', '.join(deleted)})", "success")
    except Exception:
        current_app.logger.exception("Error permanently deleting trainer %s", trainer_id)
        flash("An error occurred while permanently deleting the trainer. See logs.", "danger")

    return redirect(url_for("admin.trainers"))

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

@admin_bp.route('/membership-plans/<int:plan_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_membership_plan(plan_id):
    plan = MembershipPlan.get_by_id(plan_id)
    if not plan:
        flash("Membership plan not found!", "danger")
        return redirect(url_for("admin.membership_plans"))

    if request.method == "POST":
        try:
            plan.name = request.form.get("name")
            plan.description = request.form.get("description")
            plan.duration_months = request.form.get("duration_months")
            plan.price = request.form.get("price")
            features_raw = request.form.get("features", "")
            plan.features = [f.strip() for f in features_raw.split(",") if f.strip()]
            plan.is_active = bool(request.form.get("is_active"))

            plan.save()
            flash(f"✅ Plan '{plan.name}' updated successfully!", "success")
            return redirect(url_for("admin.membership_plans"))

        except Exception as e:
            flash(f"Error updating plan: {str(e)}", "danger")

    return render_template("admin/edit_membership_plan.html", plan=plan)

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
        if not payment:
            flash('Payment not found!')
            return redirect(url_for('admin.payments'))

        transaction_id = request.form.get('transaction_id') or None

        if new_status == 'completed':
            success = Payment.mark_completed(payment_id, transaction_id=transaction_id)
            if success:
                flash('Payment marked as completed and membership activated!')
            else:
                flash('Payment updated but failed to activate membership; check logs.', 'warning')
        else:
            # For pending/failed/refunded, just update the payment row
            payment.payment_status = new_status
            if transaction_id:
                payment.transaction_id = transaction_id
            payment.save()
            flash(f'Payment status updated to {new_status}.')

    except Exception as e:
        current_app.logger.exception(f'Error updating payment {payment_id}: {e}')
        flash('Error updating payment. Check logs.')

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

@admin_bp.route('/announcements/<int:announcement_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_announcement(announcement_id):
    announcement = Announcement.get_by_id(announcement_id)
    if not announcement:
        flash('Announcement not found.', 'error')
        return redirect(url_for('admin.announcements'))

    if request.method == 'POST':
        try:
            announcement.title = request.form.get('title')
            announcement.content = request.form.get('content')
            announcement.announcement_type = request.form.get('announcement_type')
            announcement.target_audience = request.form.get('target_audience')
            announcement.is_public = 1 if request.form.get('is_public') else 0
            announcement.start_date = request.form.get('start_date') or None
            announcement.end_date = request.form.get('end_date') or None

            announcement.save()
            flash('Announcement updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating announcement: {str(e)}', 'error')

    return render_template('admin/edit_announcement.html', announcement=announcement)

@admin_bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@admin_required
def delete_announcement(announcement_id):
    try:
        announcement = Announcement.get_by_id(announcement_id)
        if not announcement:
            flash('Announcement not found.', 'error')
        else:
            announcement.delete()
            flash('Announcement deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting announcement: {str(e)}', 'error')

    return redirect(url_for('admin.announcements'))

# -------------------- Reports --------------------
@admin_bp.route('/reports')
@admin_required
def reports():
    """
    Admin reports page:
      - member_stats (from Member.get_statistics)
      - revenue_stats (from Payment model or aggregated here)
      - attendance_stats (aggregated here)
      - revenue_labels / revenue_data for last 12 months
      - attendance_labels / attendance_data for last 14 days
    """
    try:
        # basic aggregates (reuse model helpers where available)
        member_stats = Member.get_statistics()
        revenue_stats = Payment.get_revenue_stats() or {'total_revenue': 0, 'total_payments': 0}
        # Attempt monthly revenue for the current month
        monthly_revenue = Payment.get_revenue_stats(year=date.today().year, month=date.today().month) or {'total_revenue': 0}
        revenue_stats['monthly_revenue'] = monthly_revenue.get('total_revenue', 0)

        # Attendance aggregates for current month (optional helper)
        attendance_stats = Attendance.get_monthly_stats(date.today().year, date.today().month) or {
            'total_sessions': 0, 'present': 0, 'absent': 0, 'attendance_rate': 0
        }

        # ---------------- Revenue time series (last 12 months) ----------------
        # Build list of month keys (YYYY-MM) and pretty labels (Mon YYYY)
        today = date.today()
        months = []
        month_keys = []
        for i in range(11, -1, -1):  # 11 months ago .. current month
            m = (today.replace(day=1) - relativedelta(months=i))
            key = m.strftime("%Y-%m")
            label = m.strftime("%b %Y")
            month_keys.append(key)
            months.append(label)

        # Query payments grouped by YYYY-MM
        start_month = (today.replace(day=1) - relativedelta(months=11)).strftime("%Y-%m-01")
        sql = """
            SELECT strftime('%Y-%m', payment_date) as ym, IFNULL(SUM(amount),0) as total
            FROM payments
            WHERE payment_status = 'completed'
              AND payment_date IS NOT NULL
              AND DATE(payment_date) >= DATE(?) 
            GROUP BY ym
            ORDER BY ym;
        """
        rows = execute_query(sql, (start_month,), current_app.config.get("DATABASE_PATH", None), fetch=True) or []
        # Normalize returned rows into a dict ym->total
        revenue_map = {}
        for r in rows:
            # rows may be dicts or tuples depending on your execute_query implementation
            ym = r['ym'] if isinstance(r, dict) else r[0]
            total = r['total'] if isinstance(r, dict) else r[1]
            revenue_map[ym] = float(total or 0)

        revenue_data = [revenue_map.get(k, 0) for k in month_keys]

        # ---------------- Attendance time series (last 14 days) ----------------
        days = []
        day_keys = []
        days_back = 13  # last 14 days including today
        for i in range(days_back, -1, -1):
            d = today - timedelta(days=i)
            key = d.isoformat()  # YYYY-MM-DD
            label = d.strftime("%b %d")
            day_keys.append(key)
            days.append(label)

        sql_att = """
            SELECT DATE(date) as d, 
                   SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count
            FROM attendance
            WHERE DATE(date) >= DATE(?)
            GROUP BY d
            ORDER BY d;
        """
        start_day = (today - timedelta(days=days_back)).isoformat()
        att_rows = execute_query(sql_att, (start_day,), current_app.config.get("DATABASE_PATH", None), fetch=True) or []
        att_map = {}
        for r in att_rows:
            d = r['d'] if isinstance(r, dict) else r[0]
            cnt = r['present_count'] if isinstance(r, dict) else r[1]
            att_map[d] = int(cnt or 0)

        attendance_data = [att_map.get(k, 0) for k in day_keys]

        # Prepare JSON payloads for Chart.js
        revenue_labels = json.dumps(months)
        revenue_json = json.dumps(revenue_data)
        attendance_labels = json.dumps(days)
        attendance_json = json.dumps(attendance_data)

        return render_template(
            'admin/reports.html',
            member_stats=member_stats,
            revenue_stats={
                'total_revenue': revenue_stats.get('total_revenue', 0),
                'monthly_revenue': revenue_stats.get('monthly_revenue', 0),
                'pending_amount': getattr(Payment, 'get_pending_amount', lambda: 0)() if hasattr(Payment, 'get_pending_amount') else 0
            },
            attendance_stats={
                'total_sessions': attendance_stats.get('total_sessions', 0),
                'present': attendance_stats.get('present', 0),
                'attendance_rate': attendance_stats.get('attendance_rate', 0)
            },
            revenue_labels=revenue_labels,
            revenue_data=revenue_json,
            attendance_labels=attendance_labels,
            attendance_data=attendance_json
        )

    except Exception as e:
        current_app.logger.exception("Failed building reports data")
        flash("Error building reports. Check logs.", "danger")
        # fallback: render with empty series but preserve other functionality
        return render_template(
            'admin/reports.html',
            member_stats=Member.get_statistics() if hasattr(Member, 'get_statistics') else {},
            revenue_stats={ 'total_revenue': 0, 'monthly_revenue': 0, 'pending_amount': 0 },
            attendance_stats={ 'total_sessions': 0, 'present': 0, 'attendance_rate': 0 },
            revenue_labels=json.dumps([]),
            revenue_data=json.dumps([]),
            attendance_labels=json.dumps([]),
            attendance_data=json.dumps([])
        )


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

            # Create/record payment first: due in 15 days by default
            payment_due = date.today() + timedelta(days=15)
            payment = Payment(
                member_id=member.id,
                membership_plan_id=int(plan_id),
                amount=amount,
                payment_method=payment_method,
                payment_status=payment_status,
                due_date=payment_due
            )
            if payment_status == 'completed':
                payment.payment_date = date.today().isoformat()

            payment_id = payment.save()
            if not payment_id:
                flash('Could not create payment record.', 'danger')
                return redirect(url_for('admin.renew_membership', member_id=member_id))

            # Extend membership ONLY if payment is completed now
            if payment_status == 'completed':
                if member.membership_end_date and member.membership_end_date >= date.today():
                    start_date = member.membership_end_date + timedelta(days=1)
                else:
                    start_date = date.today()

                end_date = start_date + relativedelta(months=plan.duration_months)

                member.membership_plan_id = int(plan_id)
                member.membership_start_date = start_date
                member.membership_end_date = end_date
                member.membership_status = 'active'   # keep field naming consistent
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
