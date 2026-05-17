app_name = "mu_contracts"
app_title = "MU Contracts"
app_publisher = "Majid"
app_description = "Arabic Employee Contracts e-signing system"
app_email = "majid54554@gmail.com"
app_license = "mit"

jinja = {
	"methods": [
		"mu_contracts.api.format_hijri",
		"mu_contracts.api.format_gregorian",
		"mu_contracts.api.add_hijri_days",
		"mu_contracts.api.get_contract_settings",
	]
}

# Fixtures — exported to JSON so they ship with the app and are recreated on
# fresh installs. Includes the Print Format, default-PF Property Setter, and
# the Workspace with its shortcuts.
fixtures = [
	{
		"dt": "Print Format",
		"filters": [["name", "=", "Contract Employee"]],
	},
	{
		"dt": "Property Setter",
		"filters": [
			["doc_type", "=", "Contract Employee"],
			["property", "=", "default_print_format"],
		],
	},
	{
		"dt": "Workspace",
		"filters": [["name", "=", "First Party"]],
	},
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "mu_contracts",
# 		"logo": "/assets/mu_contracts/logo.png",
# 		"title": "MU Contracts",
# 		"route": "/mu_contracts",
# 		"has_permission": "mu_contracts.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mu_contracts/css/mu_contracts.css"
# app_include_js = "/assets/mu_contracts/js/mu_contracts.js"

# include js, css files in header of web template
# web_include_css = "/assets/mu_contracts/css/mu_contracts.css"
# web_include_js = "/assets/mu_contracts/js/mu_contracts.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mu_contracts/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "mu_contracts/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "mu_contracts.utils.jinja_methods",
# 	"filters": "mu_contracts.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "mu_contracts.install.after_install"
after_migrate = "mu_contracts.install.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "mu_contracts.uninstall.before_uninstall"
# after_uninstall = "mu_contracts.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mu_contracts.utils.before_app_install"
# after_app_install = "mu_contracts.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mu_contracts.utils.before_app_uninstall"
# after_app_uninstall = "mu_contracts.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "mu_contracts.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mu_contracts.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"mu_contracts.tasks.all"
# 	],
# 	"daily": [
# 		"mu_contracts.tasks.daily"
# 	],
# 	"hourly": [
# 		"mu_contracts.tasks.hourly"
# 	],
# 	"weekly": [
# 		"mu_contracts.tasks.weekly"
# 	],
# 	"monthly": [
# 		"mu_contracts.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "mu_contracts.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "mu_contracts.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "mu_contracts.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mu_contracts.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mu_contracts.utils.before_request"]
# after_request = ["mu_contracts.utils.after_request"]

# Job Events
# ----------
# before_job = ["mu_contracts.utils.before_job"]
# after_job = ["mu_contracts.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"mu_contracts.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

