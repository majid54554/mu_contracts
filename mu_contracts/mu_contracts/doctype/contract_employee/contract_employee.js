frappe.ui.form.on("Contract Employee", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("معاينة العقد"), () => {
			const url = `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.docname)}&no_letterhead=1&_lang=ar`;
			window.open(url, "_blank");
		});

		frm.add_custom_button(__("تحميل العقد PDF"), () => {
			// Use our own endpoint — it inlines the private signature image as
			// base64 before handing HTML to the Chrome PDF generator, otherwise
			// the PDF shows a broken-image icon in the signature cell.
			const url = `/api/method/mu_contracts.api.download_contract_pdf?name=${encodeURIComponent(frm.docname)}`;
			window.open(url, "_blank");
		}).addClass("btn-primary");

		if (frm.doc.signature_image) {
			frm.add_custom_button(__("عرض التوقيع"), () => {
				window.open(frm.doc.signature_image, "_blank");
			});
		}
	},
});
