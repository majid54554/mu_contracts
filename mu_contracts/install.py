"""Post-install setup for the mu_contracts app.

Runs after `bench install-app mu_contracts` and after every `bench migrate`
(via after_migrate). Idempotent — safe to re-run.
"""

import frappe


def after_install():
	"""Post-install hook — called once after the app is installed."""
	_ensure_default_print_format()
	_ensure_contract_settings()
	frappe.db.commit()


def after_migrate():
	"""Run after every `bench migrate` so the defaults stay in place."""
	_ensure_default_print_format()
	_ensure_contract_settings()
	frappe.db.commit()


def _ensure_default_print_format():
	"""Make sure the 'Contract Employee' print format is the default for the
	Contract Employee doctype. Fixtures load the Print Format itself; this just
	wires up the Property Setter that flags it as the default."""
	pf_name = "Contract Employee"
	if not frappe.db.exists("Print Format", pf_name):
		return

	# Set as default via Property Setter (the standard Frappe way).
	exists = frappe.db.exists(
		"Property Setter",
		{
			"doc_type": "Contract Employee",
			"property": "default_print_format",
		},
	)
	if exists:
		frappe.db.set_value("Property Setter", exists, "value", pf_name)
		return

	frappe.get_doc(
		{
			"doctype": "Property Setter",
			"doctype_or_field": "DocType",
			"doc_type": "Contract Employee",
			"property": "default_print_format",
			"property_type": "Data",
			"value": pf_name,
		}
	).insert(ignore_permissions=True)


def _ensure_contract_settings():
	"""Create the Contract Settings single doc with default values if it's
	missing — Frappe normally lazy-creates single doctypes, but we want the
	defaults filled in even before the user opens the page."""
	if not frappe.db.exists("DocType", "Contract Settings"):
		return
	doc = frappe.get_single("Contract Settings")
	# Only set defaults if the field is empty (don't overwrite user edits).
	defaults = {
		"company_name": "مؤسسة وجهات المرشدين للخدمات العامة",
		"commercial_registration": "4031252525",
		"unified_number": "7024160462",
		"city": "مكة المكرمة",
		"first_party_name": "محمد إبراهيم محمود جليسه",
		"first_party_id": "1004874507",
		"first_party_birth_date": "20 / 12 / 1416",
		"first_party_role": "المالك",
	}
	changed = False
	for k, v in defaults.items():
		if not getattr(doc, k, None):
			setattr(doc, k, v)
			changed = True
	if changed:
		doc.save(ignore_permissions=True)
