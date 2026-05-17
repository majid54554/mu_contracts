import base64
import secrets
from datetime import date as _date

import frappe
from frappe import _


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
	Contract Settings into the HTML as base64 data URIs."""
	if emp.signature_image:
		html = _inline_private_image(html, emp.signature_image)
	# First-party signature comes from the Contract Settings single-doctype.
	# We cache the single in flags so multiple calls in the same request reuse it.
	settings_sig = frappe.db.get_single_value("Contract Settings", "first_party_signature")
	if settings_sig:
		html = _inline_private_image(html, settings_sig)
	return html


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

	# Try every plausible phone format so a user entering 0501234567 still
	# matches a stored +966501234567 (and vice versa). Match national_id
	# exactly OR with leading/trailing whitespace stripped on either side.
	rows = frappe.get_all(
		"Contract Employee",
		filters={
			"phone_number": ["in", _phone_variants(phone)],
			"national_id": national_id,
		},
		fields=["name", "employee_name", "is_signed"],
		limit=1,
	)
	if not rows:
		# Fallback: maybe national_id is stored with extra whitespace.
		# Look it up by phone variants alone and compare national_id loosely.
		candidates = frappe.get_all(
			"Contract Employee",
			filters={"phone_number": ["in", _phone_variants(phone)]},
			fields=["name", "employee_name", "is_signed", "national_id"],
			limit=20,
		)
		for c in candidates:
			if str(c.national_id or "").strip() == national_id:
				rows = [c]
				break

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

	emp = frappe.get_doc("Contract Employee", employee_id)
	if not emp.is_signed:
		frappe.throw(_("هذا العقد لم يتم توقيعه بعد."))

	return {
		"employee_name": emp.employee_name,
		"signed_html": _build_signed_html(emp),
	}


def _build_contract_pdf_bytes(emp) -> bytes:
	"""Generate PDF bytes for an employee contract using Chrome PDF generator.

	Renders the HTML first, inlines the private signature image as base64
	(Chrome sub-process has no session to fetch /private/files/...), then hands
	the rewritten HTML to the chrome PDF generator hook directly."""
	from frappe.utils.pdf import get_chrome_pdf

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
			pdf_generator="chrome",
		)
		html = _inline_contract_images(html, emp)

		return get_chrome_pdf(
			print_format=pf_name,
			html=html,
			options={},
			output=None,
			pdf_generator="chrome",
		)
	finally:
		if frappe.session.user != original_user:
			frappe.set_user(original_user)


@frappe.whitelist(allow_guest=True)
def download_signed_pdf(token: str):
	employee_id = frappe.cache.get_value(CACHE_PREFIX + token, shared=True)
	if not employee_id:
		frappe.throw(_("انتهت جلسة التحقق. ابدأ من جديد."))

	emp = frappe.get_doc("Contract Employee", employee_id)
	if not emp.is_signed:
		frappe.throw(_("هذا العقد لم يتم توقيعه بعد."))

	pdf_bytes = _build_contract_pdf_bytes(emp)

	frappe.local.response.filename = f"contract-{emp.employee_name}.pdf"
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def download_contract_pdf(name: str):
	"""Internal endpoint used by the DocType "تحميل العقد PDF" button.
	Uses the same inline-image PDF helper so signatures aren't broken icons."""
	if not frappe.has_permission("Contract Employee", "read", doc=name):
		frappe.throw(_("غير مصرح"))

	emp = frappe.get_doc("Contract Employee", name)
	pdf_bytes = _build_contract_pdf_bytes(emp)

	frappe.local.response.filename = f"contract-{emp.employee_name}.pdf"
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "pdf"


@frappe.whitelist(allow_guest=True)
def submit_signature(token: str, signature_b64: str):
	employee_id = frappe.cache.get_value(CACHE_PREFIX + token, shared=True)
	if not employee_id:
		frappe.throw(_("انتهت جلسة التحقق. ابدأ من جديد."))

	if not signature_b64 or "base64," not in signature_b64:
		frappe.throw(_("التوقيع مطلوب"))

	emp = frappe.get_doc("Contract Employee", employee_id)
	if emp.is_signed:
		frappe.throw(_("هذا العقد تم توقيعه مسبقاً."))

	header, encoded = signature_b64.split("base64,", 1)
	image_bytes = base64.b64decode(encoded)

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

	return {
		"success": True,
		"signed_html": _build_signed_html(emp),
	}
