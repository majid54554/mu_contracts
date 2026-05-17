"""Rename the workspace from 'First Party' to 'إدارة العقود' on existing
installs. New installs get the renamed workspace via fixtures, but sites
created before this rename need a one-time migration."""

import frappe


def execute():
	if not frappe.db.exists("Workspace", "First Party"):
		return
	if frappe.db.exists("Workspace", "إدارة العقود"):
		# Already renamed (or both exist somehow) — nothing to do.
		return

	frappe.flags.ignore_permissions = True
	frappe.rename_doc("Workspace", "First Party", "إدارة العقود", force=True)

	# Also rename the matching Desktop Icon so the home grid label updates.
	if frappe.db.exists("Desktop Icon", "First Party"):
		frappe.db.set_value("Desktop Icon", "First Party", "link_to", "إدارة العقود")
		frappe.db.set_value("Desktop Icon", "First Party", "label", "إدارة العقود")
		try:
			frappe.rename_doc("Desktop Icon", "First Party", "إدارة العقود", force=True)
		except Exception:
			# Renaming desktop icon is best-effort; failure shouldn't block the patch.
			pass

	frappe.db.commit()
