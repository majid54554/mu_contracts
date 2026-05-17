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
	# Best-effort: download the Chromium binary so PDF rendering "just works".
	# Failure here is non-fatal — wkhtmltopdf still works as a fallback.
	_setup_playwright_chromium()


def after_migrate():
	"""Run after every `bench migrate` so the defaults stay in place."""
	_ensure_default_print_format()
	_ensure_contract_settings()
	frappe.db.commit()


@frappe.whitelist()
def install_chromium():
	"""Whitelisted helper so the user can re-trigger the Chromium download
	from Desk if the initial post-install attempt failed. Requires System
	Manager role."""
	if "System Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw("Only System Manager can install Chromium.")
	import io
	import contextlib

	buf = io.StringIO()
	with contextlib.redirect_stdout(buf):
		_setup_playwright_chromium()
	return buf.getvalue()


def _setup_playwright_chromium():
	"""Download the Chromium binary that Playwright drives. Runs once after
	install; safe to call again — Playwright skips if it's already there.

	If this fails (no network, no permission to write to the cache dir, missing
	system libraries on Linux) the app still works — _html_to_pdf falls back
	to wkhtmltopdf. We just log it and tell the operator how to retry."""
	import subprocess
	import sys

	try:
		print("→ Installing Chromium binary for Playwright (one-time, ~170MB)...")
		result = subprocess.run(
			[sys.executable, "-m", "playwright", "install", "chromium"],
			capture_output=True,
			text=True,
			timeout=600,
		)
		if result.returncode == 0:
			print("✅ Chromium binary installed. PDF generation uses Chrome quality.")
		else:
			print(f"⚠️  Chromium install failed (exit {result.returncode}):")
			print(result.stderr[-2000:] if result.stderr else "(no error output)")
			print()
			print("Retry manually on the server:")
			print("    ./env/bin/playwright install chromium")
			print("    Linux only: sudo ./env/bin/playwright install-deps chromium")
	except FileNotFoundError:
		print("⚠️  Playwright Python package not found. Run:")
		print("    ./env/bin/pip install playwright")
	except subprocess.TimeoutExpired:
		print("⚠️  Chromium download timed out (10 min). Retry manually:")
		print("    ./env/bin/playwright install chromium")
	except Exception as e:
		print(f"⚠️  Unexpected error setting up Playwright: {e}")


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
