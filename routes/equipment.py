from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.equipment import Equipment
from utils.decorators import login_required

equipment_bp = Blueprint('equipment', __name__)

@equipment_bp.route('/list_equipment')
@login_required
def list_equipment():
    """Display all equipment with their status"""
    equipment = Equipment.get_all()
    return render_template('list_equipment.html', equipment=equipment)

@equipment_bp.route('/add_equipment')
@login_required
def add_equipment():
    """Display add equipment form"""
    return render_template('add_equipment.html')

@equipment_bp.route('/add_equipment', methods=['POST'])
@login_required
def add_equipment_post():
    """Process add equipment form"""
    try:
        name = request.form.get('name')
        status = request.form.get('status', 'working')
        
        if not name:
            flash('Equipment name is required!')
            return redirect(url_for('equipment.add_equipment'))
        
        equipment = Equipment(name=name, status=status)
        equipment_id = equipment.save()
        
        if equipment_id:
            flash(f'Equipment "{name}" added successfully!')
        else:
            flash('Error adding equipment. Please try again.')
            
    except Exception as e:
        flash('An error occurred while adding equipment.')
    
    return redirect(url_for('equipment.list_equipment'))

@equipment_bp.route('/equipment/<int:equipment_id>/maintenance', methods=['POST'])
@login_required
def mark_maintenance(equipment_id):
    """Mark equipment for maintenance"""
    equipment = Equipment.get_by_id(equipment_id)
    if not equipment:
        flash('Equipment not found!')
        return redirect(url_for('equipment.list_equipment'))
    
    equipment.mark_for_maintenance()
    flash(f'Equipment "{equipment.name}" marked for maintenance.')
    return redirect(url_for('equipment.list_equipment'))

@equipment_bp.route('/equipment/<int:equipment_id>/working', methods=['POST'])
@login_required
def mark_working(equipment_id):
    """Mark equipment as working"""
    equipment = Equipment.get_by_id(equipment_id)
    if not equipment:
        flash('Equipment not found!')
        return redirect(url_for('equipment.list_equipment'))
    
    equipment.mark_as_working()
    flash(f'Equipment "{equipment.name}" marked as working.')
    return redirect(url_for('equipment.list_equipment'))

@equipment_bp.route('/api/equipment/stats')
@login_required
def equipment_stats():
    """API endpoint for equipment statistics"""
    working_count = Equipment.get_working_count()
    maintenance_count = Equipment.get_maintenance_count()
    total_count = working_count + maintenance_count
    
    return jsonify({
        'total': total_count,
        'working': working_count,
        'maintenance': maintenance_count,
        'working_percentage': round((working_count / total_count * 100) if total_count > 0 else 0, 2)
    })