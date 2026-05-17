import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1
	# Expose the CSRF token via the controller — the Jinja sandbox in older
	# Frappe versions (v15) refuses direct access to frappe.session inside
	# templates and raises "Illegal template", so we pass it in as a variable.
	context.csrf_token = (
		frappe.session.csrf_token if frappe.session.user != "Guest" else ""
	)
	return context
