"""
Constants matching CodeIgniter 4 Constants.php exactly.
"""

class Constants:
    IS_DEV = True
    JIRA_LINK = 'https://jira.secext.samsung.net/browse/'
    JIRA_CREATE_ISSUE = 'https://jira.secext.samsung.net/secure/CreateIssue!default.jspa'
    JIRA_SSGTM_TICKET = 'https://jira.secext.samsung.net/browse/GTA-31005'
    JIRA_TAGGING_SUPPORT = 'https://jira.secext.samsung.net/secure/ViewProfile.jspa?name=tagging.jira%40concentrix.com'
    MT_JIRA_LINK = 'https://devops.sdsdev.co.kr/jira/browse/'

    AL_RULES_SEARCH_PARAMETER = 'rules?filter%5Bname%5D=CONTAINS+'
    AL_LIBRARY_CREATE = 'publishing/new'

    LP_WRITE_PATH = 'uploads/lp/'
    LP_PATH = 'uploads/lp/'
    NEW_TAG_FILE_WRITE_PATH = 'uploads/new_tag_requests/'
    ACTIVITY_LOGS_FILE_WRITE_PATH = 'uploads/activity_logs/'

    JIRA_TYPE_DATE_EXTENSION_RULE = 1
    JIRA_TYPE_NEW_TAG = 2
    JIRA_TYPE_NEW_RULE = 3
    JIRA_TYPE_MASTER_APPROVAL = 4
    JIRA_TYPE_UPDATE_RULE = 5
    JIRA_TYPE_MAINTENANCE_TICKET = 6
    JIRA_TYPE_OTHER = 7

    JIRA_TICKET_TYPES = {
        JIRA_TYPE_DATE_EXTENSION_RULE: 'Date Extension Rule',
        JIRA_TYPE_NEW_TAG: 'New Tag',
        JIRA_TYPE_NEW_RULE: 'New Rule',
        JIRA_TYPE_MASTER_APPROVAL: 'Master Approval',
        JIRA_TYPE_UPDATE_RULE: 'Update Rule',
        JIRA_TYPE_MAINTENANCE_TICKET: 'Maintenance Ticket',
        JIRA_TYPE_OTHER: 'Other',
    }

    JIRA_CREATE_TICKET_TYPES = {
        JIRA_TYPE_MASTER_APPROVAL: 'Master Approval',
        JIRA_TYPE_MAINTENANCE_TICKET: 'Maintenance Ticket',
        JIRA_TYPE_OTHER: 'Other',
    }

    REQUEST_TYPES = {
        JIRA_TYPE_NEW_TAG: 'New Tag',
        JIRA_TYPE_NEW_RULE: 'New Rule',
    }

    REQUEST_TYPE_FIELD = {
        JIRA_TYPE_NEW_TAG: 'new-tag-request',
        JIRA_TYPE_NEW_RULE: 'new-rule-request',
    }

    STATUS_ENABLED = 1
    STATUS_DISABLED = 2
    STATUS_EXPIRED = 3
    STATUS_PENDING_VERIFICATION = 4
    STATUS_UPDATED_IN_AL = 5
    STATUS_NEW_TAG_SUBMITTED = 6
    STATUS_NEW_RULE_SUBMITTED = 7
    STATUS_ENDED = 8
    STATUS_ON_HOLD = 9
    STATUS_INVALID = 10
    STATUS_DEFAULT = 145
    STATUS_ALL = 999

    STATUS = {
        STATUS_ALL: 'All Statuses',
        STATUS_DEFAULT: 'Default',
        STATUS_ENABLED: 'Enabled',
        STATUS_DISABLED: 'Disabled',
        STATUS_EXPIRED: 'Expired',
        STATUS_PENDING_VERIFICATION: 'Pending Verification',
        STATUS_UPDATED_IN_AL: 'Updated in AL',
        STATUS_NEW_TAG_SUBMITTED: 'New Tag Request Submitted',
        STATUS_NEW_RULE_SUBMITTED: 'New Rule Request Submitted',
        STATUS_ENDED: 'Ended',
        STATUS_INVALID: 'Invalid / Deleted',
        STATUS_ON_HOLD: 'On-Hold / Blocked',
    }

    TAG_STATUS = {
        STATUS_ENABLED: 'Enabled',
        STATUS_DISABLED: 'Disabled',
        STATUS_EXPIRED: 'Expired',
        STATUS_PENDING_VERIFICATION: 'Pending Verification',
        STATUS_UPDATED_IN_AL: 'Updated in AL',
        STATUS_NEW_TAG_SUBMITTED: 'New Tag Request Submitted',
        STATUS_NEW_RULE_SUBMITTED: 'New Rule Request Submitted',
        STATUS_ENDED: 'Ended',
        STATUS_INVALID: 'Invalid / Deleted',
        STATUS_ON_HOLD: 'On-Hold / Blocked',
    }

    STATUS_DEFAULT_VALUE = [1, 4, 5, 6, 7, 9]

    STATUS_REQUEST_HQ_REVIEW = 1
    STATUS_REQUEST_PENDING_ITEMS = 2
    STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED = 3
    STATUS_REQUEST_APPROVED = 4
    STATUS_REQUEST_REJECTED = 5
    STATUS_REQUEST_PUBLISHED = 6

    STATUS_REQUESTS = {
        STATUS_REQUEST_HQ_REVIEW: 'HQ Review',
        STATUS_REQUEST_PENDING_ITEMS: 'On-Hold Req',
        STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED: 'New Rule Request Submitted',
        STATUS_REQUEST_APPROVED: 'Approved',
        STATUS_REQUEST_REJECTED: 'Rejected',
        STATUS_REQUEST_PUBLISHED: 'Published',
    }

    SUBSIDIARY_SGE = 1
    SUBSIDIARY_SESAR = 2
    SUBSIDIARY_SETK = 3
    SUBSIDIARY_SEIL = 4
    SUBSIDIARY_SEILPS = 5
    SUBSIDIARY_SELV = 6
    SUBSIDIARY_SEEG = 7
    SUBSIDIARY_SEMAG = 8
    SUBSIDIARY_SEPAK = 9
    SUBSIDIARY_MENAO = 10
    SUBSIDIARY_AFRICA_RHQ = 11
    SUBSIDIARY_IRAN_RHQ = 12
    SUBSIDIARY_SDS = 13

    SUBSIDIARIES = {
        SUBSIDIARY_SGE: 'SGE',
        SUBSIDIARY_SESAR: 'SESAR',
        SUBSIDIARY_SETK: 'SETK',
        SUBSIDIARY_SEIL: 'SEIL',
        SUBSIDIARY_SEILPS: 'SEILPS',
        SUBSIDIARY_SELV: 'SELV',
        SUBSIDIARY_SEEG: 'SEEG',
        SUBSIDIARY_SEMAG: 'SEMAG',
        SUBSIDIARY_SEPAK: 'SEPAK',
    }

    ACTIVITY_LOG_SUBSIDIARIES = {
        SUBSIDIARY_SGE: 'SGE',
        SUBSIDIARY_SESAR: 'SESAR',
        SUBSIDIARY_SETK: 'SETK',
        SUBSIDIARY_SEIL: 'SEIL',
        SUBSIDIARY_SEILPS: 'SEILPS',
        SUBSIDIARY_SELV: 'SELV',
        SUBSIDIARY_SEEG: 'SEEG',
        SUBSIDIARY_SEMAG: 'SEMAG',
        SUBSIDIARY_SEPAK: 'SEPAK',
        SUBSIDIARY_MENAO: 'MENAO',
        SUBSIDIARY_AFRICA_RHQ: 'Africa RHQ',
        SUBSIDIARY_IRAN_RHQ: 'Iran RHQ',
        SUBSIDIARY_SDS: 'SDS',
    }

    ATTACHMENT_APPROVAL = 1
    ATTACHMENT_EMAIL_REQUEST = 2
    ATTACHMENT_REQUEST_FORM = 3
    ATTACHMENT_DOCUMENTATION = 4
    ATTACHMENT_OTHER = 5
    ATTACHMENTS = {
        ATTACHMENT_APPROVAL: 'Approval',
        ATTACHMENT_EMAIL_REQUEST: 'Email Request',
        ATTACHMENT_REQUEST_FORM: 'Request Form',
        ATTACHMENT_DOCUMENTATION: 'Documentation',
        ATTACHMENT_OTHER: 'Other',
    }

    YES = 1
    NO = 0
    YES_NO = {
        NO: 'No',
        YES: 'Yes',
    }

    ACC_TYPE = {
        0: 'System',
        1: 'Admin',
        2: 'User',
    }

    IS_EPP = {
        0: 'No',
        1: 'Yes',
    }

    IS_ACTIVE = {
        0: 'Inactive',
        1: 'Active',
    }

    PURPOSE_GOAL_NEW_TAG = [
        'What is the official website of the platform/company?',
        'What is the duration of usage? Will it be used for a specific campaign or as part of an ongoing effort without a defined end date?',
        'Any KPIs applied to review this tag bi-monthly as we need to extend every 2 months?',
        'Performance thresholds that will determine renewal or deactivation of this tag?',
        'What is your internal process for reviewing and validating these KPIs every two months?',
    ]

    INTEGRATION_RESULT_PAGE_LOAD = {
        'If the <b>Page Load Rule</b> is included': 'Confirm (Y/N)',
        '1) Check the rule is normally generated': 'Y / N',
        '2) Confirm that no script errors occur': 'Y / N',
        '3) Check that the page loads normally': 'Y / N',
        '4) Confirm that all contents in the page are loaded normally': 'Y / N',
    }

    INTEGRATION_RESULT_EVENT_CLICK = {
        'If the <b>Event Click Rule</b> is included': 'Confirm (Y/N)',
        '1) Check whether the rule is normally generated': 'Y / N',
        '2) Check that no script errors occur': 'Y / N',
        '3) When an event occurs, whether the functions corresponding to the event operate normally as before': 'Y / N',
        '4) After the event occurs, there is no impact on the expected User Journey': 'Y / N',
    }

    TEAM_MEDIA_TAGGING = 1
    TEAM_DWF = 2
    TEAM_CRM = 3
    TEAM_SPOKE = 4
    TEAM_OTHER = 5
    TEAMS = {
        TEAM_MEDIA_TAGGING: 'Media Tagging',
        TEAM_DWF: 'DWF',
        TEAM_CRM: 'CRM 2.0',
        TEAM_SPOKE: 'Spoke',
    }

    PROJECT_MEDIA_TAGGING = 1
    PROJECT_DWF = 2
    PROJECT_CRM = 3
    PROJECT_SPOKE = 4
    PROJECT_OTHER = 5
    PROJECTS = TEAMS

    USER_SYSTEM = 0
    USER_SYSTEM_LABEL = 'System'
    USER_MARIE = 1
    USER_KHRISTINE = 2
    USER_LUCKY = 3
    USER_JANITHA = 4
    USER_GEORGE = 5
    USER_OTHER = 6
    USERS = {
        USER_MARIE: 'Marie',
        USER_KHRISTINE: 'Khristine',
        USER_LUCKY: 'Lucky',
        USER_JANITHA: 'Janitha',
        USER_GEORGE: 'George',
        USER_OTHER: 'Other',
    }

    USER_ROLE_MEDIA_TAGGING = 1
    USER_ROLE_MARTECH = 2
    USER_ROLE_ADMIN = 3
    USER_ROLES = {
        USER_ROLE_MEDIA_TAGGING: 'Media Tagging',
        USER_ROLE_MARTECH: 'Martech',
        USER_ROLE_ADMIN: 'Admin',
    }

    USER_ACCESS_LEVELS = {
        USER_MARIE: USER_ROLE_MEDIA_TAGGING,
        USER_LUCKY: USER_ROLE_ADMIN,
        USER_GEORGE: USER_ROLE_MEDIA_TAGGING,
        USER_KHRISTINE: USER_ROLE_MARTECH,
        USER_JANITHA: USER_ROLE_MARTECH,
        USER_OTHER: USER_ROLE_ADMIN,
    }

    USER_TEAMS = {
        USER_MARIE: TEAM_MEDIA_TAGGING,
        USER_LUCKY: TEAM_MEDIA_TAGGING,
        USER_GEORGE: TEAM_MEDIA_TAGGING,
        USER_KHRISTINE: TEAM_DWF,
        USER_JANITHA: TEAM_CRM,
        USER_OTHER: TEAM_CRM,
    }

    USER_ROLES_ACCESS = {
        USER_ROLE_MEDIA_TAGGING: {
            'dashboard': True,
            'tags': True,
            'tag-requests': True,
            'properties': True,
            'vendors': True,
            'jira': True,
            'tasks': True,
            'settings': False,
            'reports': True,
        },
        USER_ROLE_MARTECH: {
            'dashboard': True,
            'tags': False,
            'tag-requests': False,
            'properties': False,
            'vendors': False,
            'jira': False,
            'tasks': True,
            'settings': False,
            'reports': False,
        },
        USER_ROLE_ADMIN: {
            'dashboard': True,
            'tags': True,
            'tag-requests': True,
            'properties': True,
            'vendors': True,
            'jira': True,
            'tasks': True,
            'settings': True,
            'reports': True,
        },
    }

    ACTIVITY_LOGS_STATUS_TO_DO = 1
    ACTIVITY_LOGS_STATUS_INVESTIGATION = 2
    ACTIVITY_LOGS_STATUS_IMPLEMENTATION = 3
    ACTIVITY_LOGS_STATUS_QA = 4
    ACTIVITY_LOGS_STATUS_REVIEW = 5
    ACTIVITY_LOGS_STATUS_COMPLETED = 6
    ACTIVITY_LOGS_STATUS_BLOCKED = 7
    ACTIVITY_LOGS_STATUS = {
        ACTIVITY_LOGS_STATUS_TO_DO: 'Not yet started',
        ACTIVITY_LOGS_STATUS_INVESTIGATION: 'In Progress - Investigation',
        ACTIVITY_LOGS_STATUS_IMPLEMENTATION: 'In Progress - Implementation',
        ACTIVITY_LOGS_STATUS_QA: 'Testing - QA',
        ACTIVITY_LOGS_STATUS_REVIEW: 'Pending Review',
        ACTIVITY_LOGS_STATUS_COMPLETED: 'Completed',
        ACTIVITY_LOGS_STATUS_BLOCKED: 'Blocked/On Hold',
    }
    ACTIVITY_LOG_STATUS = ACTIVITY_LOGS_STATUS


    TAG_REQUEST_STATUS_REFERENCE_MAPPING = {
        STATUS_REQUEST_HQ_REVIEW: {
            'task': ACTIVITY_LOGS_STATUS_REVIEW,
            'tag': STATUS_PENDING_VERIFICATION,
        },
        STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED: {
            'task': ACTIVITY_LOGS_STATUS_REVIEW,
            'tag': STATUS_PENDING_VERIFICATION,
        },
        STATUS_REQUEST_PENDING_ITEMS: {
            'task': ACTIVITY_LOGS_STATUS_BLOCKED,
            'tag': STATUS_ON_HOLD,
        },
        STATUS_REQUEST_APPROVED: {
            'task': ACTIVITY_LOGS_STATUS_COMPLETED,
            'tag': STATUS_NEW_TAG_SUBMITTED,
        },
        STATUS_REQUEST_PUBLISHED: {
            'task': ACTIVITY_LOGS_STATUS_COMPLETED,
            'tag': STATUS_ENABLED,
        },
    }

    TASK_STATUS_REFERENCE_MAPPING = {
        ACTIVITY_LOGS_STATUS_REVIEW: {
            'request': STATUS_REQUEST_HQ_REVIEW,
            'tag': STATUS_PENDING_VERIFICATION
        },
        ACTIVITY_LOGS_STATUS_COMPLETED: {
            'request': STATUS_REQUEST_PUBLISHED,
            'tag': STATUS_ENABLED
        },
        ACTIVITY_LOGS_STATUS_BLOCKED: {
            'request': STATUS_REQUEST_PENDING_ITEMS,
            'tag': STATUS_ON_HOLD
        },
    }

    ACTIVITY_TYPE_TASK = 1
    ACTIVITY_TYPE_SUPPORT = 2
    ACTIVITY_TYPE_TROUBLESHOOTING = 3
    ACTIVITY_TYPE_REQUEST = 4
    ACTIVITY_TYPE_MEETING = 5
    ACTIVITY_TYPE_RENEWAL = 6
    ACTIVITY_TYPE_OTHER = 7
    ACTIVITY_TYPE_DEVELOPMENT = 8
    ACTIVITY_TYPES = {
        ACTIVITY_TYPE_TASK: 'Task',
        ACTIVITY_TYPE_SUPPORT: 'Support',
        ACTIVITY_TYPE_TROUBLESHOOTING: 'Troubleshooting',
        ACTIVITY_TYPE_REQUEST: 'Request',
        ACTIVITY_TYPE_MEETING: 'Meeting',
        ACTIVITY_TYPE_RENEWAL: 'Renewal',
        ACTIVITY_TYPE_DEVELOPMENT: 'Development',
        ACTIVITY_TYPE_OTHER: 'Other',
    }

    ACTIVITY_SIZE_S = 1
    ACTIVITY_SIZE_M = 2
    ACTIVITY_SIZE_L = 3
    ACTIVITY_SIZE_XL = 4
    ACTIVITY_SIZE_SPRINT = 5
    ACTIVITY_SIZES = {
        ACTIVITY_SIZE_S: 'S',
        ACTIVITY_SIZE_M: 'M',
        ACTIVITY_SIZE_L: 'L',
        ACTIVITY_SIZE_XL: 'XL',
        ACTIVITY_SIZE_SPRINT: 'Sprint',
    }

    ACTIVITY_SIZES_DESCRIPTIONS = {
        ACTIVITY_SIZE_S: 'S (Small): Minor tasks / quick fixes (estimated effort < 2 hours)',
        ACTIVITY_SIZE_M: 'M (Medium): Standard tag setups / simple troubleshooting (estimated effort: 2-5 hours)',
        ACTIVITY_SIZE_L: 'L (Large): New tag integrations / complex tracking rules (estimated effort: 1-2 days)',
        ACTIVITY_SIZE_XL: 'XL (Extra Large): Major property setups / migrations / custom JS (estimated effort: 3-5 days)',
        ACTIVITY_SIZE_SPRINT: 'Sprint: Massive undertakings / entire sprint effort (estimated effort: 1-2 weeks)',
    }

    PRIORITY_LOW = 1
    PRIORITY_MEDIUM = 2
    PRIORITY_HIGH = 3
    PRIORITY_CRITICAL = 4
    PRIORITY_BLOCKER = 5
    PRIORITY_DEFAULT = 10
    PRIORITIES = {
        PRIORITY_DEFAULT: 'Default',
        PRIORITY_LOW: 'Low',
        PRIORITY_MEDIUM: 'Medium',
        PRIORITY_HIGH: 'High',
        PRIORITY_CRITICAL: 'Critical',
        PRIORITY_BLOCKER: 'Blocker',
    }

    CAMPAIGN_STATUS_NEW = 1
    CAMPAIGN_STATUS_EXISTING = 2
    CAMPAIGN_STATUS = {
        CAMPAIGN_STATUS_NEW: 'New',
        CAMPAIGN_STATUS_EXISTING: 'Existing',
    }

    COMMENT_TYPE_COMMENT = 1
    COMMENT_TYPE_UPDATE = 2
    COMMENT_TYPES = {
        COMMENT_TYPE_COMMENT: 'Comment',
        COMMENT_TYPE_UPDATE: 'Update',
    }

    # Helper function for user colors on Dashboard
    @classmethod
    def get_user_color(cls, user_id):
        colors = {
            cls.USER_MARIE: '#7B1FA2',
            cls.USER_KHRISTINE: '#C2185B',
            cls.USER_LUCKY: '#1B5E20',
            cls.USER_JANITHA: '#1565C0',
            cls.USER_GEORGE: '#E65100',
        }
        return colors.get(int(user_id or 0), '#0071E3')


class JiraMapping:
    PRIORITY_LOW = 'Low'
    PRIORITY_MEDIUM = 'Medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'Critical'
    PRIORITY_BLOCKER = 'Blocker'
    PRIORITY_MINOR = 'Minor'

    PRIORITIES = {
        Constants.PRIORITY_LOW: PRIORITY_LOW,
        Constants.PRIORITY_MEDIUM: PRIORITY_MEDIUM,
        Constants.PRIORITY_HIGH: PRIORITY_HIGH,
        Constants.PRIORITY_CRITICAL: PRIORITY_CRITICAL,
        Constants.PRIORITY_BLOCKER: PRIORITY_BLOCKER,
        Constants.PRIORITY_DEFAULT: PRIORITY_MINOR,
    }

    ESTIMATE_S = '1h'
    ESTIMATE_M = '3h'
    ESTIMATE_L = '1d'
    ESTIMATE_XL = '3d'
    ESTIMATE_SPRINT = '1w'

    ESTIMATES = {
        Constants.ACTIVITY_SIZE_S: ESTIMATE_S,
        Constants.ACTIVITY_SIZE_M: ESTIMATE_M,
        Constants.ACTIVITY_SIZE_L: ESTIMATE_L,
        Constants.ACTIVITY_SIZE_XL: ESTIMATE_XL,
        Constants.ACTIVITY_SIZE_SPRINT: ESTIMATE_SPRINT,
    }

    JIRA_STATUS_TODO = 'To Do'
    JIRA_STATUS_IN_PROGRESS = 'In Progress'
    JIRA_STATUS_CLOSED = 'Closed'

    STATUS_MAPPING = {
        Constants.ACTIVITY_LOGS_STATUS_TO_DO: JIRA_STATUS_TODO,
        Constants.ACTIVITY_LOGS_STATUS_INVESTIGATION: JIRA_STATUS_IN_PROGRESS,
        Constants.ACTIVITY_LOGS_STATUS_IMPLEMENTATION: JIRA_STATUS_IN_PROGRESS,
        Constants.ACTIVITY_LOGS_STATUS_QA: JIRA_STATUS_IN_PROGRESS,
        Constants.ACTIVITY_LOGS_STATUS_REVIEW: JIRA_STATUS_IN_PROGRESS,
        Constants.ACTIVITY_LOGS_STATUS_COMPLETED: JIRA_STATUS_CLOSED,
        Constants.ACTIVITY_LOGS_STATUS_BLOCKED: JIRA_STATUS_TODO,
    }

    TRANSITIONS = {
        JIRA_STATUS_TODO: {
            JIRA_STATUS_IN_PROGRESS: '11',
            JIRA_STATUS_CLOSED: '51',
        },
        JIRA_STATUS_IN_PROGRESS: {
            JIRA_STATUS_TODO: '21',
            JIRA_STATUS_CLOSED: '31',
        },
        JIRA_STATUS_CLOSED: {
            JIRA_STATUS_IN_PROGRESS: '41',
            JIRA_STATUS_TODO: '61',
        }
    }

