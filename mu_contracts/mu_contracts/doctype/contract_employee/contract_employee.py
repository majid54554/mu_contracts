import frappe
from frappe.model.document import Document


class ContractEmployee(Document):
	def validate(self):
		if self.phone_number:
			self.phone_number = "".join(c for c in str(self.phone_number) if c.isdigit() or c == "+")
		if self.national_id:
			self.national_id = str(self.national_id).strip()
