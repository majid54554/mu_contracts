import base64
import secrets
from contextlib import contextmanager
from datetime import date as _date

import frappe
from frappe import _


@contextmanager
def _as_administrator():
	"""Run the block as Administrator if the current user is Guest.
	Guest endpoints on /sign need to read/write Contract Employee records,
	but Guest has no permission on that doctype. We authenticate the visitor
	via phone + national_id + token, so it's safe to elevate inside these
	endpoints."""
	original = frappe.session.user
	if original == "Guest":
		frappe.set_user("Administrator")
	try:
		yield
	finally:
		if frappe.session.user != original:
			frappe.set_user(original)


def format_hijri(date_input=None):
	from hijri_converter import Gregorian

	if date_input is None:
		d = _date.today()
	elif isinstance(date_input, str):
		d = frappe.utils.getdate(date_input)
	else:
		d = date_input
	h = Gregorian(d.year, d.month, d.day).to_hijri()
	return f"{h.day:02d} / {h.month:02d} / {h.year}"


def format_gregorian(date_input=None):
	if date_input is None:
		d = _date.today()
	elif isinstance(date_input, str):
		d = frappe.utils.getdate(date_input)
	else:
		d = date_input
	return f"{d.day:02d} / {d.month:02d} / {d.year}"


def add_hijri_days(date_input, days):
	from hijri_converter import Gregorian
	from datetime import timedelta

	if isinstance(date_input, str):
		d = frappe.utils.getdate(date_input)
	else:
		d = date_input
	d2 = d + timedelta(days=int(days))
	h = Gregorian(d2.year, d2.month, d2.day).to_hijri()
	return f"{h.day:02d} / {h.month:02d} / {h.year}"


def get_contract_settings():
	"""Jinja-safe accessor for the Contract Settings single — returns a plain
	dict so the print format template can read settings.company_name etc.
	(frappe.get_single is not whitelisted inside the safe_exec Jinja sandbox.)"""
	return frappe.db.get_singles_dict("Contract Settings") or {}

CACHE_PREFIX = "ec_token:"
TOKEN_TTL = 1800


def _get_print_format_name():
	pf = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Contract Employee", "property": "default_print_format"},
		"value",
	)
	if pf and frappe.db.exists("Print Format", pf):
		return pf
	rows = frappe.get_all(
		"Print Format",
		filters={"doc_type": "Contract Employee", "disabled": 0},
		pluck="name",
		limit=1,
	)
	return rows[0] if rows else None


def _normalize_phone(phone):
	return "".join(c for c in str(phone or "") if c.isdigit() or c == "+")


def _phone_variants(phone):
	"""Return every plausible way the same Saudi phone number could be stored
	in the DB so a single user-entered number matches all common formats:
	  0501234567, +966501234567, 966501234567, 00966501234567, 501234567.
	"""
	digits = "".join(c for c in str(phone or "") if c.isdigit())
	if not digits:
		return []

	# Strip leading country-code prefixes to find the local 9-digit part.
	if digits.startswith("00966"):
		local = digits[5:]
	elif digits.startswith("966"):
		local = digits[3:]
	elif digits.startswith("0") and len(digits) > 9:
		local = digits[1:]
	else:
		local = digits

	variants = {
		digits,                    # what user typed (digits only)
		str(phone).strip(),        # raw input (in case it had +/spaces)
		_normalize_phone(phone),   # digits + leading +
	}
	if local:
		variants.update({
			local,                 # 501234567
			"0" + local,           # 0501234567
			"966" + local,         # 966501234567
			"+966" + local,        # +966501234567
			"00966" + local,       # 00966501234567
		})
	return [v for v in variants if v]


def _fallback_template():
	"""Last-resort template used only if the Print Format is missing.
	Normal installs ship the 'Contract Employee' Print Format via fixtures,
	so this template should almost never render in production."""
	return """
<div class="contract-document">
  <h2 style="text-align:center;margin-bottom:24px">عقد عمل</h2>
  <p>تم إبرام هذا العقد بتاريخ <strong>{{ today }}</strong> بين:</p>
  <p><strong>الطرف الأول:</strong> الشركة (صاحب العمل)</p>
  <p><strong>الطرف الثاني:</strong> {{ employee_name }} حامل/ة الهوية رقم {{ national_id }}، رقم الجوال {{ phone_number }}.</p>
  <h4 style="margin-top:24px">بنود العقد</h4>
  <ol style="line-height:2">
    <li>المسمى الوظيفي: <strong>{{ position }}</strong></li>
    <li>المكافأة: <strong>{{ salary }}</strong></li>
    <li>تاريخ المباشرة: <strong>{{ start_date }}</strong></li>
    <li>يلتزم الطرف الثاني بتنفيذ المهام الموكلة إليه بأمانة ومهنية، والالتزام بأنظمة الشركة الداخلية وأنظمة العمل المعمول بها في المملكة العربية السعودية.</li>
    <li>يحق لكلا الطرفين إنهاء العقد وفق الإجراءات النظامية بإشعار خطي مسبق.</li>
    <li>هذا العقد ملزم لكلا الطرفين بمجرد التوقيع الإلكتروني عليه، ويعتبر التوقيع المحفوظ في النظام دليلاً قانونياً.</li>
  </ol>
  <p style="margin-top:16px;font-size:12px;color:#777">[Print Format "Contract Employee" غير موجود — تأكد من تثبيت fixtures التطبيق]</p>
</div>
"""


def _inline_private_image(html: str, file_url: str) -> str:
	"""Replace a Frappe private file URL with a base64 data URI in HTML.
	Chrome PDF generator can't fetch /private/files/... over HTTP because it
	has no session — embedding the bytes inline solves that. Same substitution
	works for the on-screen guest preview where /private requires login too."""
	if not html or not file_url:
		return html
	import base64
	import os

	# Only handle URLs Frappe stores; anything else (already-data-URI, http://...) we leave alone.
	if not file_url.startswith("/private/files/") and not file_url.startswith("/files/"):
		return html
	rel = file_url.lstrip("/")
	# /private/files/foo.png → site/private/files/foo.png ; /files/foo.png → site/public/files/foo.png
	if rel.startswith("private/files/"):
		abs_path = frappe.get_site_path("private", "files", rel.split("/", 2)[-1])
	else:
		abs_path = frappe.get_site_path("public", "files", rel.split("/", 2)[-1])
	if not os.path.exists(abs_path):
		return html
	ext = (os.path.splitext(abs_path)[1] or ".png").lstrip(".").lower()
	if ext == "jpg":
		ext = "jpeg"
	with open(abs_path, "rb") as f:
		data = base64.b64encode(f.read()).decode("ascii")
	data_uri = f"data:image/{ext};base64,{data}"
	return html.replace(file_url, data_uri)


def _render_via_print_format(emp):
	pf_name = _get_print_format_name()
	if not pf_name:
		return None
	# validate_print_permission in printview.py doesn't honour ignore_permissions —
	# it calls frappe.has_permission(throw=True). For guest visitors to /sign we
	# need to render under Administrator briefly so the print format works.
	original_user = frappe.session.user
	try:
		if original_user == "Guest":
			frappe.set_user("Administrator")
		html = frappe.get_print(
			doctype="Contract Employee",
			name=emp.name,
			print_format=pf_name,
			no_letterhead=True,
		)
		# Inline image URLs so Chrome PDF / guest preview can render them
		# (private files need a session, and Chrome sub-process has none).
		html = _inline_contract_images(html, emp)
		return html
	except Exception:
		frappe.log_error(title="Print Format render failed", message=frappe.get_traceback())
		return None
	finally:
		if frappe.session.user != original_user:
			frappe.set_user(original_user)


def _inline_contract_images(html: str, emp) -> str:
	"""Inline both the employee signature and the first-party signature from
	Contract Settings into the HTML as base64 data URIs. Also inlines any
	bundled app assets (fonts/letterhead images) so PDF generators that can't
	fetch URLs (wkhtmltopdf, Chrome subprocess) still see them."""
	if emp.signature_image:
		html = _inline_private_image(html, emp.signature_image)
	# First-party signature comes from the Contract Settings single-doctype.
	settings_sig = frappe.db.get_single_value("Contract Settings", "first_party_signature")
	if settings_sig:
		html = _inline_private_image(html, settings_sig)
	# Inline /assets/mu_contracts/... URLs (fonts, header/footer images) as
	# base64 data URIs. Critical for wkhtmltopdf which won't fetch local URLs.
	html = _inline_app_assets(html)
	return html


_ASSET_MIME = {
	"ttf": "font/ttf",
	"otf": "font/otf",
	"woff": "font/woff",
	"woff2": "font/woff2",
	"png": "image/png",
	"jpg": "image/jpeg",
	"jpeg": "image/jpeg",
	"gif": "image/gif",
	"svg": "image/svg+xml",
}


def _inline_app_assets(html: str) -> str:
	"""Rewrite url('/assets/mu_contracts/...') and src="/assets/..." references
	to inline base64 data URIs. Reads the file from disk so it works no matter
	what PDF generator runs."""
	import base64
	import os
	import re

	app_root = frappe.get_app_path("mu_contracts", "public")

	def file_to_data_uri(rel_path: str) -> str | None:
		# rel_path looks like "fonts/Cairo-Regular.ttf" or "images/header.jpg"
		safe_path = os.path.normpath(rel_path)
		if safe_path.startswith(".."):
			return None
		full = os.path.join(app_root, safe_path)
		if not os.path.isfile(full):
			return None
		ext = os.path.splitext(full)[1].lstrip(".").lower()
		mime = _ASSET_MIME.get(ext, "application/octet-stream")
		with open(full, "rb") as f:
			data = base64.b64encode(f.read()).decode("ascii")
		return f"data:{mime};base64,{data}"

	def replace_url(match):
		original = match.group(0)
		path = match.group(1)  # e.g. "fonts/Cairo-Regular.ttf"
		data_uri = file_to_data_uri(path)
		return original.replace(f"/assets/mu_contracts/{path}", data_uri) if data_uri else original

	# Match url('...'), url("..."), and src="..." pointing at our assets.
	pattern = re.compile(r"/assets/mu_contracts/([A-Za-z0-9_./\-]+\.(?:ttf|otf|woff2?|png|jpe?g|gif|svg))")
	# Do it in one pass: replace the path with its data URI everywhere it appears
	def whole_url_replace(m):
		path = m.group(1)
		data_uri = file_to_data_uri(path)
		return data_uri or m.group(0)

	return pattern.sub(whole_url_replace, html)


def _render_fallback(emp):
	return frappe.render_template(
		_fallback_template(),
		{
			"employee_name": emp.employee_name,
			"phone_number": emp.phone_number,
			"national_id": emp.national_id,
			"position": emp.position or "—",
			"salary": frappe.utils.fmt_money(emp.salary or 0, currency="SAR"),
			"start_date": frappe.utils.formatdate(emp.start_date) if emp.start_date else "—",
			"today": frappe.utils.formatdate(frappe.utils.today()),
		},
	)


def _render_contract(emp):
	return _render_via_print_format(emp) or _render_fallback(emp)


def _strip_embed_noise(html: str) -> str:
	"""Strip scripts and printview UI chrome before embedding HTML in /sign."""
	import re

	if not html:
		return html
	html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
	html = re.sub(r"<script[^>]*/>", "", html, flags=re.IGNORECASE)
	# Strip the in-print download/preview chrome we add to the print format itself
	html = re.sub(r'<div[^>]*id=["\']ec-dl["\'][^>]*>.*?</div>', "", html, flags=re.DOTALL | re.IGNORECASE)
	# Strip Frappe's printview toolbar buttons (Get PDF / Print) if present
	html = re.sub(
		r'<div[^>]*class=["\'][^"\']*(?:action-banner|print-format-toolbar)[^"\']*["\'][^>]*>.*?</div>',
		"",
		html,
		flags=re.DOTALL | re.IGNORECASE,
	)
	return html


def _build_signed_html(emp):
	# Render via print format if available (it already shows the signature/IP/date).
	pf_html = _render_via_print_format(emp)
	if pf_html is not None:
		return _strip_embed_noise(pf_html)

	# Fallback path: append signature block to the rendered fallback template.
	contract_html = _strip_embed_noise(_render_fallback(emp))
	if not emp.signature_image:
		return contract_html
	sig_url = frappe.utils.get_url(emp.signature_image)
	signed_on = frappe.utils.format_datetime(emp.signed_on) if emp.signed_on else ""
	sig_block = (
		f'<div class="signature-section" style="margin-top:32px;border-top:1px solid #999;padding-top:20px">'
		f'<p style="font-weight:600">توقيع الطرف الثاني ({emp.employee_name}):</p>'
		f'<img src="{sig_url}" style="max-height:140px;background:#fff;border:1px solid #eee;padding:6px"/>'
		f'<p style="font-size:11px;color:#666;margin-top:10px">'
		f'تاريخ التوقيع: {signed_on} — IP: {emp.signed_ip or ""}'
		f'</p></div>'
	)
	return contract_html + sig_block


@frappe.whitelist(allow_guest=True)
def lookup_employee(phone: str, national_id: str):
	national_id = str(national_id or "").strip()
	phone_norm = _normalize_phone(phone)

	if not phone_norm or not national_id:
		frappe.throw(_("يرجى إدخال رقم الجوال ورقم الهوية"))

	# Use frappe.db.sql directly (bypasses permission checks). In v15
	# frappe.get_all enforces read permission for the current user, and Guest
	# has none on Contract Employee — so it would return 0 rows even when the
	# record exists. We're already auth'ing the visitor via phone+national_id.
	variants = _phone_variants(phone)
	placeholders = ", ".join(["%s"] * len(variants))
	rows = frappe.db.sql(
		f"""
		SELECT name, employee_name, is_signed, national_id
		FROM `tabContract Employee`
		WHERE phone_number IN ({placeholders})
		LIMIT 20
		""",
		variants,
		as_dict=True,
	)
	# Compare national_id loosely (strip whitespace from both sides) in case
	# the stored value has stray spaces.
	rows = [r for r in rows if str(r.national_id or "").strip() == national_id]

	if not rows:
		frappe.throw(_("لم نجد سجل بهذه البيانات. تأكد من رقم الجوال ورقم الهوية."))

	emp = rows[0]
	token = secrets.token_urlsafe(32)
	frappe.cache.set_value(CACHE_PREFIX + token, emp.name, expires_in_sec=TOKEN_TTL, shared=True)

	return {
		"token": token,
		"employee_name": emp.employee_name,
		"already_signed": bool(emp.is_signed),
	}


@frappe.whitelist(allow_guest=True)
def get_contract(token: str):
	employee_id = frappe.cache.get_value(CACHE_PREFIX + token, shared=True)
	if not employee_id:
		frappe.throw(_("انتهت جلسة التحقق. ابدأ من جديد."))

	with _as_administrator():
		emp = frappe.get_doc("Contract Employee", employee_id)
		if emp.is_signed:
			frappe.throw(_("هذا العقد تم توقيعه مسبقاً."))

		return {
			"employee_name": emp.employee_name,
			"contract_html": _strip_embed_noise(_render_contract(emp)),
		}


@frappe.whitelist(allow_guest=True)
def get_signed_contract(token: str):
	employee_id = frappe.cache.get_value(CACHE_PREFIX + token, shared=True)
	if not employee_id:
		frappe.throw(_("انتهت جلسة التحقق. ابدأ من جديد."))

	with _as_administrator():
		emp = frappe.get_doc("Contract Employee", employee_id)
		if not emp.is_signed:
			frappe.throw(_("هذا العقد لم يتم توقيعه بعد."))

		return {
			"employee_name": emp.employee_name,
			"signed_html": _build_signed_html(emp),
		}


def _build_contract_pdf_bytes(emp) -> bytes:
	"""Generate PDF bytes for an employee contract.

	Renders the HTML first, inlines the private signature image as base64
	(Chrome sub-process has no session to fetch /private/files/...), then hands
	the rewritten HTML to the best available PDF generator (chrome if installed,
	otherwise wkhtmltopdf)."""
	pf_name = _get_print_format_name() or "Contract Employee"

	original_user = frappe.session.user
	if original_user == "Guest":
		frappe.set_user("Administrator")
	try:
		html = frappe.get_print(
			doctype="Contract Employee",
			name=emp.name,
			print_format=pf_name,
			no_letterhead=True,
			as_pdf=False,
		)
		html = _inline_contract_images(html, emp)
		return _html_to_pdf(html, pf_name)
	finally:
		if frappe.session.user != original_user:
			frappe.set_user(original_user)


def _html_to_pdf(html: str, pf_name: str) -> bytes:
	"""Convert already-rendered HTML to PDF bytes using whatever generator
	this Frappe version provides.

	Order of preference (best Arabic / RTL output first):
	  1. frappe.utils.pdf.get_chrome_pdf — v17+ ships this directly
	  2. pdf_generator hook — v15/v16 with print_designer-style apps register one
	  3. Playwright headless Chromium — best quality on v15 if installed
	     (pip install playwright && playwright install chromium)
	  4. frappe.utils.pdf.get_pdf (wkhtmltopdf) — always available, but poor RTL
	"""
	# 1. Built-in Chrome generator (v17+)
	try:
		from frappe.utils.pdf import get_chrome_pdf

		pdf = get_chrome_pdf(
			print_format=pf_name,
			html=html,
			options={},
			output=None,
			pdf_generator="chrome",
		)
		if pdf:
			return pdf
	except ImportError:
		pass
	except Exception:
		frappe.log_error(title="get_chrome_pdf failed", message=frappe.get_traceback())

	# 2. Hook-registered chrome generator (older Frappe + print_designer app)
	for hook in frappe.get_hooks("pdf_generator") or []:
		try:
			pdf = frappe.call(
				hook,
				print_format=pf_name,
				html=html,
				options={},
				output=None,
				pdf_generator="chrome",
			)
			if pdf:
				return pdf
		except Exception:
			frappe.log_error(title="pdf_generator hook failed", message=frappe.get_traceback())

	# 3. Playwright headless Chromium — recommended for v15 (huge quality jump
	# over wkhtmltopdf for Arabic). Renders the HTML in real Chromium, so
	# Google Fonts, RTL shaping, ligatures, and modern CSS all work.
	try:
		pdf = _html_to_pdf_via_playwright(html)
		if pdf:
			return pdf
	except ImportError:
		# Playwright not installed — fall through to wkhtmltopdf.
		pass
	except Exception:
		frappe.log_error(title="playwright pdf failed", message=frappe.get_traceback())

	# 4. wkhtmltopdf — always available, but Arabic rendering is poor.
	from frappe.utils.pdf import get_pdf

	return get_pdf(html)


def _html_to_pdf_via_playwright(html: str) -> bytes:
	"""Render HTML to PDF via Playwright (headless Chromium).

	Requires:  pip install playwright  &&  playwright install chromium
	"""
	from playwright.sync_api import sync_playwright

	with sync_playwright() as p:
		browser = p.chromium.launch(args=["--no-sandbox"])
		try:
			page = browser.new_page()
			# wait_until=networkidle so Google Fonts have time to load
			page.set_content(html, wait_until="networkidle", timeout=30000)
			pdf_bytes = page.pdf(
				format="A4",
				print_background=True,
				prefer_css_page_size=True,
			)
			return pdf_bytes
		finally:
			browser.close()


def _send_pdf_response(pdf_bytes: bytes, employee_name: str):
	"""Build a PDF download response. We use response.type='binary' plus an
	explicit Content-Disposition: attachment so mobile browsers (especially
	iOS Safari) trigger a real download instead of trying to render inline."""
	import re
	from urllib.parse import quote

	# ASCII fallback in case the name has chars that don't survive header encoding
	safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", employee_name) or "employee"
	utf8_name = quote(f"contract-{employee_name}.pdf")
	frappe.local.response.filename = f"contract-{safe_name}.pdf"
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "binary"
	frappe.local.response.headers = {
		"Content-Type": "application/pdf",
		"Content-Disposition": f"attachment; filename=\"contract-{safe_name}.pdf\"; filename*=UTF-8''{utf8_name}",
	}


@frappe.whitelist(allow_guest=True)
def download_signed_pdf(token: str):
	employee_id = frappe.cache.get_value(CACHE_PREFIX + token, shared=True)
	if not employee_id:
		frappe.throw(_("انتهت جلسة التحقق. ابدأ من جديد."))

	with _as_administrator():
		emp = frappe.get_doc("Contract Employee", employee_id)
		if not emp.is_signed:
			frappe.throw(_("هذا العقد لم يتم توقيعه بعد."))

		pdf_bytes = _build_contract_pdf_bytes(emp)

	_send_pdf_response(pdf_bytes, emp.employee_name)


@frappe.whitelist()
def download_contract_pdf(name: str):
	"""Internal endpoint used by the DocType "تحميل العقد PDF" button.
	Uses the same inline-image PDF helper so signatures aren't broken icons."""
	if not frappe.has_permission("Contract Employee", "read", doc=name):
		frappe.throw(_("غير مصرح"))

	emp = frappe.get_doc("Contract Employee", name)
	pdf_bytes = _build_contract_pdf_bytes(emp)

	_send_pdf_response(pdf_bytes, emp.employee_name)


@frappe.whitelist(allow_guest=True)
def submit_signature(token: str, signature_b64: str):
	employee_id = frappe.cache.get_value(CACHE_PREFIX + token, shared=True)
	if not employee_id:
		frappe.throw(_("انتهت جلسة التحقق. ابدأ من جديد."))

	if not signature_b64 or "base64," not in signature_b64:
		frappe.throw(_("التوقيع مطلوب"))

	header, encoded = signature_b64.split("base64,", 1)
	image_bytes = base64.b64decode(encoded)

	with _as_administrator():
		emp = frappe.get_doc("Contract Employee", employee_id)
		if emp.is_signed:
			frappe.throw(_("هذا العقد تم توقيعه مسبقاً."))

		from frappe.utils.file_manager import save_file

		sig_file = save_file(
			f"signature-{emp.name}.png",
			image_bytes,
			"Contract Employee",
			emp.name,
			is_private=1,
		)

		emp.signature_image = sig_file.file_url
		emp.is_signed = 1
		emp.signed_on = frappe.utils.now_datetime()
		emp.signed_ip = frappe.local.request_ip
		emp.save(ignore_permissions=True)
		frappe.db.commit()

		signed_html = _build_signed_html(emp)

	return {
		"success": True,
		"signed_html": signed_html,
	}
