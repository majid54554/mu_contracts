"""Diagnostic script for PDF rendering issues.

Run on the customer server with:
    bench --site SITE execute mu_contracts.diagnose.run

It prints which PDF generator the app will end up using, whether the font
files are reachable on disk, whether Playwright is installed, etc.
"""

import os
import subprocess

import frappe


def run():
	print("=" * 60)
	print("mu_contracts PDF diagnostic")
	print("=" * 60)

	# 1. Frappe version
	try:
		import frappe as _f
		print(f"Frappe version: {_f.__version__}")
	except Exception as e:
		print(f"Frappe version check failed: {e}")

	# 2. Built-in Chrome PDF generator (v17+)?
	try:
		from frappe.utils.pdf import get_chrome_pdf  # noqa: F401
		print("✅ frappe.utils.pdf.get_chrome_pdf is available (v17+)")
	except ImportError:
		print("❌ frappe.utils.pdf.get_chrome_pdf NOT available (older Frappe)")

	# 3. pdf_generator hook (print_designer app)
	hooks = frappe.get_hooks("pdf_generator") or []
	if hooks:
		print(f"✅ pdf_generator hook(s) registered: {hooks}")
	else:
		print("❌ No pdf_generator hook registered (no print_designer app)")

	# 4. Playwright installed?
	try:
		import playwright  # noqa: F401
		print(f"✅ Playwright Python package: {playwright.__version__}")
		# Check chromium binary
		try:
			from playwright.sync_api import sync_playwright
			with sync_playwright() as p:
				path = p.chromium.executable_path
				print(f"   Chromium binary: {path}")
				print(f"   Exists: {os.path.exists(path)}")
		except Exception as e:
			print(f"   ⚠️  Chromium check failed: {e}")
	except ImportError:
		print("❌ Playwright NOT installed (pip install playwright)")

	# 5. wkhtmltopdf
	try:
		r = subprocess.run(["wkhtmltopdf", "--version"], capture_output=True, text=True, timeout=5)
		print(f"   wkhtmltopdf: {r.stdout.strip() or r.stderr.strip()}")
	except FileNotFoundError:
		print("   wkhtmltopdf: not installed")
	except Exception as e:
		print(f"   wkhtmltopdf check failed: {e}")

	print()
	print("--- Font files in app ---")
	font_dir = frappe.get_app_path("mu_contracts", "public", "fonts")
	if os.path.isdir(font_dir):
		for f in sorted(os.listdir(font_dir)):
			full = os.path.join(font_dir, f)
			size = os.path.getsize(full)
			print(f"   {f}: {size:,} bytes")
	else:
		print(f"   ❌ Font dir not found: {font_dir}")

	# Also check the built /assets path
	site_path = frappe.utils.get_site_path() if hasattr(frappe.utils, "get_site_path") else None
	# Sites/assets is typically at bench/sites/assets
	assets_dir = os.path.abspath(os.path.join(frappe.get_app_path("frappe"), "..", "..", "..", "sites", "assets", "mu_contracts", "fonts"))
	if os.path.isdir(assets_dir):
		print(f"   ✅ Asset symlink/copy exists: {assets_dir}")
		for f in sorted(os.listdir(assets_dir)):
			full = os.path.join(assets_dir, f)
			print(f"     {f}: {os.path.getsize(full):,} bytes")
	else:
		print(f"   ⚠️  No /assets/mu_contracts/fonts in built assets — run `bench build --app mu_contracts`")
		print(f"     (expected at {assets_dir})")

	print()
	print("--- Sample PDF render ---")
	from mu_contracts.api import _build_contract_pdf_bytes, _inline_app_assets

	# Find any signed employee, otherwise create a temp one
	emps = frappe.get_all("Contract Employee", limit=1, order_by="creation desc")
	if not emps:
		print("❌ No Contract Employee records to test with — create one first.")
		return
	emp = frappe.get_doc("Contract Employee", emps[0].name)
	print(f"   Test employee: {emp.name} | {emp.employee_name}")

	# Render HTML and check inlining worked
	pf_name = "Contract Employee"
	try:
		html_raw = frappe.get_print(
			doctype="Contract Employee",
			name=emp.name,
			print_format=pf_name,
			no_letterhead=True,
			as_pdf=False,
		)
		print(f"   Raw HTML length: {len(html_raw):,} chars")
		print(f"   Has /assets/mu_contracts/fonts/ URL?: {'/assets/mu_contracts/fonts/' in html_raw}")
		html_inlined = _inline_app_assets(html_raw)
		print(f"   After inlining: {len(html_inlined):,} chars")
		print(f"   Has data:font/...base64?: {'data:font/' in html_inlined or 'data:application/x-font' in html_inlined}")
		print(f"   Has /assets/ URLs still?: {'/assets/mu_contracts/fonts/' in html_inlined}")
	except Exception as e:
		print(f"   ❌ Render failed: {e}")
		import traceback; traceback.print_exc()
		return

	try:
		pdf = _build_contract_pdf_bytes(emp)
		print(f"   ✅ PDF generated: {len(pdf):,} bytes")
	except Exception as e:
		print(f"   ❌ PDF generation failed: {e}")
		import traceback; traceback.print_exc()

	print()
	print("=" * 60)
	print("Send the FULL output above to debug the issue.")
	print("=" * 60)
