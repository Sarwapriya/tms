import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    BASE_DIR = basedir
    SECRET_KEY = os.getenv('SECRET_KEY', 'martech-tms-fallback-secret-key-2026')

    
    # Database Configuration (MySQL by default, seamlessly supports MSSQL)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:@127.0.0.1:3306/tag_monitoring-dev?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Storage and Upload Paths
    STORAGE_DIR = os.path.join(basedir, 'storage')
    UPLOAD_DIR = os.path.join(STORAGE_DIR, 'uploads')
    BACKUP_DIR = os.path.join(STORAGE_DIR, 'backups')
    LP_UPLOAD_DIR = os.path.join(UPLOAD_DIR, 'lp')
    NEW_TAG_UPLOAD_DIR = os.path.join(UPLOAD_DIR, 'new_tag_requests')
    ACTIVITY_LOG_UPLOAD_DIR = os.path.join(UPLOAD_DIR, 'activity_logs')
    PROFILE_UPLOAD_DIR = os.path.join(UPLOAD_DIR, 'profile_photos')
    
    SYSTEM_SETTINGS_FILE = os.path.join(STORAGE_DIR, 'system_settings.json')
    AUTO_BACKUP_SETTINGS_FILE = os.path.join(STORAGE_DIR, 'auto_backup_settings.json')
    
    # File limits
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB
    
    # Jira Settings
    MT_JIRA_LINK = os.getenv('MT_JIRA_LINK', 'https://devops.sdsdev.co.kr/jira/browse/')
    MT_JIRA_AUTH_TOKEN = os.getenv('MT_JIRA_AUTH_TOKEN', '')
    MT_JIRA_PROJECT_KEY = os.getenv('MT_JIRA_PROJECT_KEY', 'TMS')
    MT_JIRA_CREATE_ISSUE = os.getenv('MT_JIRA_CREATE_ISSUE', '')
    MT_JIRA_EDIT_ISSUE = os.getenv('MT_JIRA_EDIT_ISSUE', '')
    MT_JIRA_UPDATE_STATUS = os.getenv('MT_JIRA_UPDATE_STATUS', '')
    MT_JIRA_UPLOAD_ATTACHMENT = os.getenv('MT_JIRA_UPLOAD_ATTACHMENT', '')
    MT_JIRA_ADD_COMMENT = os.getenv('MT_JIRA_ADD_COMMENT', '')
    MT_JIRA_UPDATE_COMMENT = os.getenv('MT_JIRA_UPDATE_COMMENT', '')

    # AI Chat API (Fabrix)
    FABRIX_API_URL = os.getenv('FABRIX_API_URL', 'https://nsds-api.fabrix-s.samsungsds.com/sds/trial/api-llm')
    FABRIX_API_TOKEN = os.getenv('FABRIX_API_TOKEN', '')
    FABRIX_CLIENT = os.getenv('FABRIX_CLIENT', '')
    FABRIX_REPORT_API_URL = os.getenv('FABRIX_REPORT_API_URL', 'https://nsds-api.fabrix-s.samsungsds.com/sds/trial/api-chat')
    FABRIX_REPORT_API_TOKEN = os.getenv('FABRIX_REPORT_API_TOKEN', '')
    FABRIX_REPORT_CLIENT = os.getenv('FABRIX_REPORT_CLIENT', '')

    # Samsung Electronics Jira Configuration
    GTA_JIRA_PROJECT_KEY = os.getenv('GTA_JIRA_PROJECT_KEY', 'GTA')
    GTA_JIRA_AUTH_TOKEN = os.getenv('GTA_JIRA_AUTH_TOKEN', '')
    GTA_JIRA_UPDATE_STATUS = os.getenv('GTA_JIRA_UPDATE_STATUS', 'https://jira.secext.samsung.net/jira/rest/api/2/issue/{key}/transitions')

