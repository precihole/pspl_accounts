# Copyright (c) 2023, PSPL and contributors
# For license information, please see license.txt

import copy

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, format_date, getdate, today
from frappe.utils.jinja import validate_template
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_print_style
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa

class PSPLProcessStatementOfAccounts(Document):
	def validate(self):
		if not self.subject:
			self.subject = "Statement Of Accounts for {{ supplier.name }}"
		if not self.body:
			self.body = "Hello {{ supplier.name }},<br>PFA your Statement Of Accounts from {{ doc.from_date }} to {{ doc.to_date }}."

		validate_template(self.subject)
		validate_template(self.body)

		if not self.suppliers:
			frappe.throw(_("Suppliers not selected."))

def get_report_pdf(doc, consolidated=True):
	statement_dict = {}
	base_template_path = "frappe/www/printview.html"
	template_path = (
		"pspl_accounts/pspl_accounts/doctype/pspl_process_statement_of_accounts/pspl_process_statement_of_accounts.html"
	)

	for entry in doc.suppliers:
		tax_id = frappe.get_doc("Supplier", entry.supplier).tax_id
		presentation_currency = doc.currency
		if doc.letter_head:
			from frappe.www.printview import get_letter_head

			letter_head = get_letter_head(doc, 0)

		filters = frappe._dict(
			{
				"from_date": doc.from_date,
				"to_date": doc.to_date,
				"company": doc.company,
				"finance_book": doc.finance_book if doc.finance_book else None,
				"account": [doc.account] if doc.account else None,
				"party_type": "Supplier",
				"party": [entry.supplier],
				"presentation_currency": presentation_currency,
				"group_by": doc.group_by,
				"currency": doc.currency,
				"cost_center": [cc.cost_center_name for cc in doc.cost_center],
				"project": [p.project_name for p in doc.project],
				"show_opening_entries": 0,
				"include_default_book_entries": 0,
				"tax_id": tax_id if tax_id else None,
			}
		)
		col, res = get_soa(filters)

		for x in [0, -2, -1]:
			res[x]["account"] = res[x]["account"].replace("'", "")

		if len(res) == 3:
			continue

		html = frappe.render_template(
			template_path,
			{
				"filters": filters,
				"data": res,
				"ageing": None,
				"letter_head": letter_head if doc.letter_head else None,
				"terms_and_conditions": frappe.db.get_value(
					"Terms and Conditions", doc.terms_and_conditions, "terms"
				)
				if doc.terms_and_conditions
				else None,
			},
		)

		html = frappe.render_template(
			base_template_path,
			{"body": html, "css":  (), "title": "Statement For " + entry.supplier},
		)
		statement_dict[entry.supplier] = html

	if not bool(statement_dict):
		return False
	elif consolidated:
		result = "".join(list(statement_dict.values()))
		return get_pdf(result, {"orientation": doc.orientation})
	else:
		for supplier, statement_html in statement_dict.items():
			statement_dict[supplier] = get_pdf(statement_html, {"orientation": doc.orientation})
		return statement_dict



def get_recipients_and_cc(supplier, doc):
	recipients = []
	for clist in doc.suppliers:
		if clist.supplier == supplier:
			if clist.primary_email:
				recipients.append(clist.primary_email)
	cc = []
	if doc.cc_to != "":
		try:
			cc = [p.user for p in doc.cc_to]
		except Exception:
			pass

	return recipients, cc


def get_context(supplier, doc):
	template_doc = copy.deepcopy(doc)
	del template_doc.suppliers
	template_doc.from_date = format_date(template_doc.from_date)
	template_doc.to_date = format_date(template_doc.to_date)
	return {
		"doc": template_doc,
		"supplier": frappe.get_doc("Supplier", supplier),
		"frappe": frappe.utils,
	}


@frappe.whitelist()
def send_emails(document_name, from_scheduler=False):
	signature_template = (
		"pspl_accounts/pspl_accounts/doctype/pspl_process_statement_of_accounts/signature.html"
	)
	doc = frappe.get_doc("PSPL Process Statement Of Accounts", document_name)
	report = get_report_pdf(doc, consolidated=False)

	if report:
		for supplier, report_pdf in report.items():
			attachments = [{"fname": supplier + ".pdf", "fcontent": report_pdf}]
			sender = frappe.get_value('Email Account', doc.sender, 'email_id')
			recipients, cc = get_recipients_and_cc(supplier, doc)
			context = get_context(supplier, doc)
			subject = frappe.render_template(doc.subject, context)
			message = frappe.render_template(doc.body, context) + frappe.render_template(signature_template, context)

			frappe.enqueue(
				queue="short",
				method=frappe.sendmail,
				recipients=recipients,
				sender=sender,
				cc=cc,
				subject=subject,
				message=message,
				now=True,
				reference_doctype="PSPL Process Statement Of Accounts",
				reference_name=document_name,
				attachments=attachments,
			)
		return True
	else:
		return False

@frappe.whitelist()
def fetch_suppliers(supplier_group):
	return frappe.get_list('Supplier',
		{
			'supplier_group': supplier_group,
			'email_id': ['!=', '']
		},
		['name', 'email_id']
	)

@frappe.whitelist()
def download_statements(document_name):
	doc = frappe.get_doc("PSPL Process Statement Of Accounts", document_name)
	report = get_report_pdf(doc)
	if report:
		frappe.local.response.filename = doc.name + ".pdf"
		frappe.local.response.filecontent = report
		frappe.local.response.type = "download"