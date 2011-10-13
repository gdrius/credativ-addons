from osv import osv,fields
import time

class sale_damagelog(osv.osv):

    _name = 'sale.damagelog'
    _rec_name = 'ticket_id'
    
    def _get_attachments_count(self, cr, uid, ids, name, arg, context={}):
        res = {}
        attachment_obj = self.pool.get('ir.attachment')
        for id in ids: 
            res[id] = attachment_obj.search(cr, uid, [('res_id','=',id)], context=context, count=True)
        return res
    
    _columns = {
                'ticket_id':fields.char('Ticket ID',size=16),
                'stock_move_id':fields.many2one('stock.move', 'Stock Move', required=True),
                'sale_line_id':fields.related('stock_move_id','sale_line_id',type='many2one',relation='sale.order.line',string='Sale Order Line'),
                'sale_order_id':fields.related('sale_line_id', 'order_id', type='many2one', relation='sale.order',string='Order Reference', required=True),
                'partner_id':fields.related('sale_order_id', 'partner_id', type='many2one', relation='res.partner',string='Customer'),
                'product_id':fields.related('stock_move_id', 'product_id', type='many2one', relation='product.product',string='Product', required=True),
                'product_sku': fields.related('product_id', 'default_code',type='char',size=16, string='Product Code'),
                'dispatch_date' : fields.related('stock_move_id', 'date_planned', type='datetime', string='Order Date'),
                'log_date':fields.datetime('Date Created', required=True),
                'log_uid':fields.many2one('res.users','Created By'),
                'claim_ids':fields.one2many('crm.case','damagelog_id','Claims'),
                'customer_refund_id':fields.many2one('account.invoice','Customer Refund'),
                'customer_refund_amount':fields.related('customer_refund_id','amount_total',type='float',string='Refund Amount'),
                'issue_description':fields.text('Comments'),
                'num_attachments':fields.function(_get_attachments_count,method=True,type='integer',string='#Attachments', store=True),
                'flag_transport':fields.boolean('Transport'),
                'flag_product_quality':fields.boolean('Product Quality'),
                'product_supplier':fields.many2one('res.partner','Product Supplier'),
                'product_qty':fields.float('Qty'),
                'product_uom':fields.many2one('product.uom','UoM', required=True),
                }
    
    _defaults = {
                 'log_date':lambda *a : time.strftime('%Y-%m-%d %H:%M:%S'),
                 'log_uid': lambda self,cr,uid,ctx : uid,
                 }
    
    def onchange_stock_move(self, cr, uid, ids, stock_move_id):
        value = {}
        stock_move_rec = self.pool.get('stock.move').browse(cr, uid, stock_move_id)
        value['sale_order_id'] = stock_move_rec.sale_line_id and stock_move_rec.sale_line_id.order_id.id or False
        value['product_id'] =  stock_move_rec.product_id.id
        value['product_uom'] = stock_move_rec.product_uom.id
        value['product_qty'] = stock_move_rec.product_qty
        return {'value':value}
    
    def create_refund(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        damagelog_rec = self.browse(cr,uid,ids,context=context)[0]
        prod_acc_property =  damagelog_rec.product_id.property_account_income.id or damagelog_rec.product_id.categ_id.property_account_income_categ.id
        prod_acc_id = self.pool.get('account.fiscal.position').map_account(cr, uid, False, prod_acc_property)
        refund_line_vals = {
                            'product_id':damagelog_rec.product_id.id,
                            'uos_id':damagelog_rec.product_uom.id,
                            'quantity':damagelog_rec.product_qty,
                            'price_unit':damagelog_rec.product_id.list_price,
                            'name':'[' + damagelog_rec.product_sku or ' ' + ']' + damagelog_rec.product_id.name,
                            'account_id': prod_acc_id  
                           }
        inv_line_id = inv_line_obj.create(cr, uid, refund_line_vals, context=context)
        partner_acc_property = damagelog_rec.partner_id.property_account_receivable.id
        partner_acc_id = self.pool.get('account.fiscal.position').map_account(cr, uid, False, partner_acc_property)
        refund_vals = {
                        'partner_id':damagelog_rec.partner_id.id,
                        'address_invoice_id':damagelog_rec.sale_order_id.partner_invoice_id.id,
                        'account_id':partner_acc_id,
                        'company_id':damagelog_rec.sale_order_id.user_id.company_id and damagelog_rec.sale_order_id.user_id.company_id.id,
                        'type':'out_refund',
                        'invoice_line':[(6,0,[inv_line_id])]
                      }
        inv_id = invoice_obj.create(cr, uid, refund_vals, context=context)
        self.write(cr, uid, ids, {'customer_refund_id':inv_id}, context=context)
        
sale_damagelog()


class crm_case(osv.osv):
    
    _inherit = 'crm.case'
    
    _columns = {
                'damagelog_id':fields.many2one('sale.damagelog','Damage Log'),
                }
    
crm_case()
