"""Testora Backend - Test Sites Routes"""
from flask import request, jsonify
from routes import tests_bp

# Sample brand sites
SAMPLE_SITES = [
    {'id': 1, 'name': 'Quartze', 'pay': '$12.00', 'status': 'Active'},
    {'id': 2, 'name': 'Playable', 'pay': '$15.00', 'status': 'Active'},
    {'id': 3, 'name': 'Optilink', 'pay': '$10.00', 'status': 'Active'},
    {'id': 4, 'name': 'Tundra', 'pay': '$18.00', 'status': 'Active'},
    {'id': 5, 'name': 'Blooxe', 'pay': '$14.00', 'status': 'Active'},
    {'id': 6, 'name': 'Nexus', 'pay': '$11.00', 'status': 'Active'},
    {'id': 7, 'name': 'Vortex', 'pay': '$9.00', 'status': 'Active'},
    {'id': 8, 'name': 'Zenith', 'pay': '$13.00', 'status': 'Active'},
]


@tests_bp.route('/sites', methods=['GET'])
def get_sites():
    """Get all available test sites"""
    return jsonify({
        'success': True,
        'sites': SAMPLE_SITES
    }), 200


@tests_bp.route('/sites/<int:site_id>', methods=['GET'])
def get_site(site_id):
    """Get a single test site by ID"""
    for site in SAMPLE_SITES:
        if site['id'] == site_id:
            return jsonify({
                'success': True,
                'site': site
            }), 200

    return jsonify({
        'success': False,
        'message': 'Site not found.'
    }), 404


@tests_bp.route('/sites/redirect/<int:site_id>', methods=['GET'])
def redirect_site(site_id):
    """Get the external redirect URL for a test site"""
    target_url = 'https://sites.google.com/view/quartze'
    return jsonify({
        'success': True,
        'redirect_url': target_url
    }), 200

