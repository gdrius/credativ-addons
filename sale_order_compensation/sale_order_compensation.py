# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 credativ Ltd (<http://credativ.co.uk>).
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
from decimal_precision import decimal_precision as dp

class sale_order_claim(osv.osv):
    '''
    This class allows a refund and a voucher to be issued against a
    sale.order.claim. It also adds some refund and voucher
    calculations to sale.order.claims.
    '''
    _inherit = 'sale.order.claim'

    def _total_refund(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all the refunds for this claim'''
        res = {}

        claim_refund_pool = self.pool.get('sale.claim.resolution.refund')
        issue_refund_pool = self.pool.get('sale.issue.resolution.refund')

        for id in ids:
            claim_refund_ids = claim_refund_pool.search(cr, uid, [('claim_id','=',id)], context=context)
            claim_total = sum([r['refund'] for r in claim_refund_pool.read(cr, uid, claim_refund_ids, ['refund'], context=context)])

            issue_refund_ids = issue_refund_pool.search(cr, uid, [('claim_id','=',id)], context=context)
            issue_total = sum([r['refund'] for r in issue_refund_pool.read(cr, uid, issue_refund_ids, ['refund'], context=context)])

            res[id] = claim_total + issue_total

        return res

    def _total_voucher(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all the vouchers for this claim'''
        res = {}

        claim_voucher_pool = self.pool.get('sale.claim.resolution.voucher')
        issue_voucher_pool = self.pool.get('sale.issue.resolution.voucher')

        for id in ids:
            claim_voucher_ids = claim_voucher_pool.search(cr, uid, [('claim_id','=',id)], context=context)
            claim_total = sum([r['voucher'] for r in claim_voucher_pool.read(cr, uid, claim_voucher_ids, ['voucher'], context=context)])

            issue_voucher_ids = issue_voucher_pool.search(cr, uid, [('claim_id','=',id)], context=context)
            issue_total = sum([r['voucher'] for r in issue_voucher_pool.read(cr, uid, issue_voucher_ids, ['voucher'], context=context)])

            res[id] = claim_total + issue_total

        return res

    def _prev_compensation(self, cr, uid, ids, compensation_type=['refund','voucher'], claim_state=('approved',), context=None):
        '''Calculates the sum of all compensations of the specified
        type(s) made against the same sale.order as this claim and for
        claims in the specified state(s)'''
        res = {}

        order_claims_pool = self.pool.get('sale.order.claim')

        for id in ids:
            sale_order_id = self.browse(cr, uid, id, context=context).sale_order_id
            claim_ids = order_claims_pool.search(cr, uid, [('sale_order_id','=',sale_order_id),
                                                           ('id','<>',id),
                                                           ('state','in',claim_state)], context=context)
            res[id] = sum([sum([getattr(claim, 'total_%s' % (comp_type,))
                                for comp_type in compensation_type])
                           for claim in order_claims_pool.browse(cr, uid, claim_ids, context)])

        return res

    def _prev_refund(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all refunds made against the same
        sale.order as this claim'''
        return self._prev_compensation(cr, uid, ids,
                                       compensation_type=['refund'],
                                       claim_state=('approved',),
                                       context=context)

    def _prev_voucher(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all vouchers issued against the same
        sale.order as this claim'''
        return self._prev_compensation(cr, uid, ids,
                                       compensation_type=['voucher'],
                                       claim_state=('approved',),
                                       context=context)

    def _pending_refund(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all refunds that have been requested
        against the same sale.order as this claim (but not yet
        approved)'''
        return self._prev_compensation(cr, uid, ids,
                                       compensation_type=['refund'],
                                       claim_state=('open','processing','review'),
                                       context=context)

    def _pending_voucher(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all the vouchers that have been
        requested against the same sale.order as this claim (but not
        yet approved)'''
        return self._prev_compensation(cr, uid, ids,
                                       compensation_type=['voucher'],
                                       claim_state=('open','processing','review'),
                                       context=context)

    def _max_refundable(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the maximum that may be refunded against this
        sale.order; defined as the difference between the sale.order
        total and the sum of previous and pending refunds and
        vouchers'''
        return dict([(claim.id, claim.order_total - self._prev_compensation(cr, uid, claim.id,
                                                                            compensation_type=['refund','voucher'],
                                                                            claim_state=('opened','processing','review','approved'),
                                                                            context=context)[claim.id])
                     for claim in self.browse(cr, uid, ids, context=context)])

    def _get_claims_from_issues(self, cr, uid, ids, context=None):
        issue_pool = self.pool.get('sale.order.issue')
        return list(set([issue['order_claim_id'] for issue in issue_pool.read(cr, uid, ids, ['order_claim_id'], context=context)]))

    _columns = {
        'total_refund': fields.function(
            _total_refund,
            type='float',
            string='Total refunded',
            readonly=True,
            store={
                'sale.order.issue': (_get_claims_from_issues , ['refund'], 10)
                }),
        'total_voucher': fields.function(
            _total_voucher,
            type='float',
            string='Total vouchers',
            readonly=True,
            store={
                'sale.order.issue': (_get_claims_from_issues , ['voucher'], 10)
                }),
        'prev_refund': fields.function(
            _prev_refund,
            type='float',
            string='Previous refunds',
            readonly=True),
        'prev_voucher': fields.function(
            _prev_voucher,
            type='float',
            string='Previous vouchers',
            readonly=True),
        'pending_refund': fields.function(
            _pending_refund,
            type='float',
            string='Pending refunds',
            readonly=True),
        'pending_voucher': fields.function(
            _pending_voucher,
            type='float',
            string='Pending vouchers',
            readonly=True),
        'max_refundable': fields.function(
            _max_refundable,
            type='float',
            string='Maximum refundable',
            readonly=True),
        'refund': fields.float(
            'Refund',
            digits_compute=dp.get_precision('Sale Price')),
        'voucher': fields.float(
            'Voucher',
            digits_compute=dp.get_precision('Sale Price')),
        'voucher_code': fields.char(
            'Voucher code',
            size=128),
        }

    def action_open(self, cr, uid, ids, context=None):
        return super(sale_order_claim, self).action_open(cr, uid, ids, context=context)

    def action_process(self, cr, uid, ids, context=None):
        return super(sale_order_claim, self).action_process(cr, uid, ids, context=context)

    def action_review(self, cr, uid, ids, context=None):
        return super(sale_order_claim, self).action_review(cr, uid, ids, context=context)

    def action_approve(self, cr, uid, ids, context=None):
        return super(sale_order_claim, self).action_approve(cr, uid, ids, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        return super(sale_order_claim, self).action_cancel(cr, uid, ids, context=context)

sale_order_claim()


class sale_order_issue(osv.osv):
    '''
    This class allows a refund and a voucher to be issued against a
    sale.order.issue. It also adds some refund and voucher
    calculations to sale.order.issues.
    '''
    _inherit = 'sale.order.issue'

    def __prev_compensation(self, cr, uid, ids, compensation_type=['refund','voucher'], claim_state=('approved',), context=None):
        '''Calculates the sum of all compensation of the specified
        type made against sale.order.issues which are themselves
        against the resource as this sale.order.claim and where the
        parent sale.order.claim's state matches the given claim
        state(s).'''
        res = {}

        order_issues_pool = self.pool.get('sale.order.issue')

        for issue in self.browse(cr, uid, ids, context=context):
            if issue.claim_id.state not in claim_state:
                continue

            issue_ids = order_issues_pool.search(cr, uid, [('resource','=',issue.resource),
                                                           ('id','<>',issue.id)], context=context)
            res[issue.id] = sum([sum([getattr(issue, comp_type)
                                      for comp_type in compensation_type])
                                 for issue in order_issues_pool.browse(cr, uid, issue_ids, context)])

        return res

    def _prev_compensation(self, cr, uid, ids, field_name, arg, context=None):
        return self.__prev_compensation(cr, uid, ids,
                                        compensation_type=['refund','voucher'],
                                        claim_state=('approved',),
                                        context=context)

    def _prev_refund(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all refunds made against the same
        sale.order as this claim'''
        return self.__prev_compensation(cr, uid, ids,
                                        compensation_type=['refund'],
                                        claim_state=('approved',),
                                        context=context)

    def _prev_voucher(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all vouchers issued against the same
        sale.order as this claim'''
        return self.__prev_compensation(cr, uid, ids,
                                        compensation_type=['voucher'],
                                        claim_state=('approved',),
                                        context=context)

    _columns = {
        'refund': fields.float(
            'Refund',
            digits_compute=dp.get_precision('Sale Price')),
        'voucher': fields.float(
            'Voucher',
            digits_compute=dp.get_precision('Sale Price')),
        'prev_compensation': fields.function(
            _prev_compensation,
            type='float',
            string='Compensated',
            readonly=True),
        }

    def on_change_refund(self, cr, uid, ids, refund, order_claim_id, sale_order_id, context=None):
        pass

    def on_change_voucher(self, cr, uid, ids, voucher, order_claim_id, sale_order_id, context=None):
        pass

sale_order_issue()


class sale_order(osv.osv):
    '''
    Add columns to sale.order to sum the total compensation paid out
    against the order.
    '''
    _inherit = 'sale.order'

    def _total_compensation(self, cr, uid, ids, compensation_type=['refund','voucher'], claim_state=('approved',), context=None):
        '''Calculates the sum of all compensations of the specified
        type(s) and in the specified state(s) made against this
        sale.order'''
        res = {}

        order_claims_pool = self.pool.get('sale.order.claim')

        for id in ids:
            claim_ids = order_claims_pool.search(cr, uid, [('sale_order_id','=',id),
                                                           ('state','in',claim_state)], context=context)
            res[id] = sum([sum([getattr(claim, 'total_%s' % (comp_type,))
                                for comp_type in compensation_type])
                           for claim in order_claims_pool.browse(cr, uid, claim_ids, context)])

        return res

    def _total_refund(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all refunds made against this
        sale.order'''
        return self._total_compensation(cr, uid, ids,
                                       compensation_type=['refund'],
                                       claim_state=('approved',),
                                       context=context)

    def _total_voucher(self, cr, uid, ids, field_name, arg, context=None):
        '''Calculates the sum of all vouchers issued against this
        sale.order'''
        return self._total_compensation(cr, uid, ids,
                                       compensation_type=['voucher'],
                                       claim_state=('approved',),
                                       context=context)

    _columns = {
        # FIXME Consider storing these as their calculation requires
        # at least four inner loops and it will make generating the
        # list view of sale orders take even longer
        'total_refund': fields.function(
            _total_refund,
            type='float',
            string='Refunded',
            readonly=True),
        'total_voucher': fields.function(
            _total_voucher,
            type='float',
            string='Vouchers',
            readonly=True),
        }
