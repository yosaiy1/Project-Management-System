# Status codes
STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'
STATUS_WARNING = 'warning'
STATUS_INFO = 'info'

# Task statuses
TASK_STATUS_TODO = 'todo'
TASK_STATUS_IN_PROGRESS = 'inprogress'
TASK_STATUS_BLOCKED = 'blocked'
TASK_STATUS_DONE = 'done'
TASK_STATUS_CHOICES = [
    (TASK_STATUS_TODO, 'To Do'),
    (TASK_STATUS_IN_PROGRESS, 'In Progress'),
    (TASK_STATUS_DONE, 'Done'),
]

# Notification types
NOTIFICATION_INFO = 'info'
NOTIFICATION_SUCCESS = 'success'
NOTIFICATION_WARNING = 'warning'
NOTIFICATION_ERROR = 'error'

# Message strings
MSG_PERMISSION_DENIED = "You don't have permission to perform this action."
MSG_TASK_STATUS_UPDATED = "Task status updated successfully."
MSG_INVALID_REQUEST = "Invalid request method."
MSG_SUCCESS = "Operation completed successfully."
MSG_ERROR = "An error occurred."
MSG_LOGIN_SUCCESS = "Login successful!"
MSG_LOGOUT_SUCCESS = "You have been logged out successfully."
MSG_PASSWORD_CHANGE_SUCCESS = "Your password was successfully updated!"
MSG_INVALID_FILE = "Invalid file type or size"
MSG_FILE_UPLOAD_ERROR = "Error uploading file"
MSG_AVATAR_UPDATE_ERROR = "Error updating profile picture"

# Project statuses
PROJECT_STATUS_ACTIVE = 'active'
PROJECT_STATUS_COMPLETED = 'completed'
PROJECT_STATUS_ON_HOLD = 'on_hold'

# Pagination settings
ITEMS_PER_PAGE = 10
MAX_PAGE_DISPLAY = 5

# Cache timeouts (in seconds)
CACHE_TIMEOUT_SHORT = 300  # 5 minutes
CACHE_TIMEOUT_MEDIUM = 3600  # 1 hour
CACHE_TIMEOUT_LONG = 86400  # 24 hours

# Rate limiting
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_TIMEOUT = 300  # 5 minutes