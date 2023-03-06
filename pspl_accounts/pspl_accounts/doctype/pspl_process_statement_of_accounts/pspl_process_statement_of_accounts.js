// Copyright (c) 2023, PSPL and contributors
// For license information, please see license.txt

frappe.ui.form.on('PSPL Process Statement Of Accounts', {
	onload: function(frm) {
		frm.set_query('currency', function(){
			return {
				filters: {
					'enabled': 1
				}
			}
		});
		frm.set_query('supplier_group', function(){
			return {
				filters: {
					'is_group': 0
				}
			}
		});
		frm.set_query("account", function() {
			return {
				filters: {
					'company': frm.doc.company
				}
			};
		});
		if(frm.doc.__islocal){
			frm.set_value('from_date', frappe.datetime.add_months(frappe.datetime.get_today(), -1));
			frm.set_value('to_date', frappe.datetime.get_today());
		}
	},
	fetch_suppliers: function(frm) {
		if(frm.doc.supplier_group){
			frappe.call({
				method: "pspl_accounts.pspl_accounts.doctype.pspl_process_statement_of_accounts.pspl_process_statement_of_accounts.fetch_suppliers",
				args: {
					"supplier_group": frm.doc.supplier_group,
				},
				callback: function(r) {
					if(!r.exc) {
						if(r.message.length){
							frm.clear_table('suppliers');
							for (const supplier of r.message){
								var row = frm.add_child('suppliers');
								row.supplier = supplier.name;
								row.primary_email = supplier.email_id;
							}
							frm.refresh_field('suppliers');
						}
						else{
							frappe.throw(__('No Suppliers found with selected options.'));
						}
					}
				}
			});
		}
		else {
			frappe.throw('Enter supplier group.');
		}
	},
	refresh: function(frm){
		if(!frm.doc.__islocal) {
			frm.add_custom_button(__('Send Emails'), function(){
				frappe.call({
					method: "pspl_accounts.pspl_accounts.doctype.pspl_process_statement_of_accounts.pspl_process_statement_of_accounts.send_emails",
					args: {
						"document_name": frm.doc.name,
					},
					callback: function(r) {
						if(r && r.message) {
							frappe.show_alert({message: __('Emails Queued'), indicator: 'blue'});
						}
						else{
							frappe.msgprint(__('No Records for these settings.'))
						}
					}
				});
			});
			frm.add_custom_button(__('Download'), function(){
				var url = frappe.urllib.get_full_url(
					'/api/method/pspl_accounts.pspl_accounts.doctype.pspl_process_statement_of_accounts.pspl_process_statement_of_accounts.download_statements?'
					+ 'document_name='+encodeURIComponent(frm.doc.name))
				$.ajax({
					url: url,
					type: 'GET',
					success: function(result) {
						if(jQuery.isEmptyObject(result)){
							frappe.msgprint(__('No Records for these settings.'));
						}
						else{
							window.location = url;
						}
					}
				});
			});
		}
	},
});
