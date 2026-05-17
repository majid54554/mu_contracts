"""Clean up the leftover 'First Party' workspace on sites where the v01
rename_workspace patch couldn't actually rename (Frappe v15 sometimes fails
the rename silently, so the fixture-imported 'إدارة العقود' coexists with
the old 'First Party' workspace + desktop icon).

This patch:
  1. Repoints every Workspace Sidebar Item / Workspace Shortcut that still
     references "First Party" to "إدارة العقود".
  2. Deletes the leftover "First Party" Workspace + Desktop Icon.
"""

import frappe


def execute():
	# Only run cleanup when both workspaces exist — single-workspace setups
	# are handled by the original rename_workspace patch.
	has_old = frappe.db.exists("Workspace", "First Party")
	has_new = frappe.db.exists("Workspace", "إدارة العقود")
	if not has_old:
		return

	if has_new:
		# Repoint sidebar items still pointing at the old name
		try:
			frappe.db.sql(
				"""UPDATE `tabWorkspace Sidebar Item`
				   SET link_to = %s
				   WHERE link_to = 'First Party' AND link_type = 'Workspace'""",
				("إدارة العقود",),
			)
		except Exception:
			frappe.log_error(title="cleanup_old_first_party: sidebar repoint failed",
				message=frappe.get_traceback())

		# Some Frappe versions have Workspace Shortcut as a separate doctype
		# with a "link_to" field — only update if the table is there.
		try:
			frappe.db.sql(
				"""UPDATE `tabWorkspace Shortcut`
				   SET link_to = %s
				   WHERE link_to = 'First Party'""",
				("إدارة العقود",),
			)
		except Exception:
			# Table or column may not exist on this version — safe to ignore.
			pass

		# Remove the leftover workspace
		try:
			frappe.delete_doc("Workspace", "First Party",
				ignore_permissions=True, force=True, delete_permanently=True)
		except TypeError:
			# delete_permanently isn't a parameter in older versions
			try:
				frappe.delete_doc("Workspace", "First Party",
					ignore_permissions=True, force=True)
			except Exception:
				frappe.db.delete("Workspace", {"name": "First Party"})
		except Exception:
			frappe.db.delete("Workspace", {"name": "First Party"})
	else:
		# Old name exists but new doesn't — try renaming one more time
		try:
			frappe.flags.ignore_permissions = True
			frappe.rename_doc("Workspace", "First Party", "إدارة العقود", force=True)
		except Exception:
			frappe.log_error(title="cleanup_old_first_party: rename retry failed",
				message=frappe.get_traceback())

	# Always clean up the matching Desktop Icon
	if frappe.db.exists("Desktop Icon", "First Party"):
		try:
			frappe.delete_doc("Desktop Icon", "First Party",
				ignore_permissions=True, force=True)
		except Exception:
			frappe.db.delete("Desktop Icon", {"name": "First Party"})

	frappe.db.commit()
