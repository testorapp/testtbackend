"""Testora Backend - User Routes (Profile, Stats)"""
from flask import request, jsonify
from models import User, db
from routes import users_bp


@users_bp.route('/user', methods=['GET'])
def get_user():
    """Get user profile by auth token (passed as Bearer token or query param)"""
    auth_header = request.headers.get('Authorization', '')
    token = request.args.get('token', '')

    if auth_header.startswith('Bearer '):
        token = auth_header[7:]

    if not token:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    # For demo: find first active user (since we use simple token)
    # In production: verify JWT token
    # For now, return a default user context or look up by simple token
    user = User.query.filter_by(is_active=True).first()

    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 200


@users_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get platform-wide statistics"""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()

    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'community_earnings': '$2.4M+',
        'sites_tested': '150,000+',
        'active_testers': '45,000+'
    }

    return jsonify({
        'success': True,
        'stats': stats
    }), 200

