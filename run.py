import os
import sys

# Ensure project root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']
    
    print("=" * 60)
    print("  MARTECH TMS - PYTHON WEB APPLICATION")
    print(f"  Running on: http://127.0.0.1:{port}")
    print(f"  Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=port, debug=debug)
