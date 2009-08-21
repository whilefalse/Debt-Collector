## -*- coding: utf-8 -*-

from pymongo.objectid import ObjectId
import pymongo
import users
import time

def get_transaction_details(db, user, values_as_nums=False):
    #Get transactions
    from_transactions = [t for t in db.transactions.find({'from_user':user['_id']}).sort('timestamp', pymongo.ASCENDING)]
    to_transactions = [t for t in db.transactions.find({'to_user':user['_id']}).sort('timestamp', pymongo.ASCENDING)]
    
    #Get totals and balance
    total_from = sum([t['value'] for t in from_transactions])
    total_to = sum([t['value'] for t in to_transactions])
    balance = total_from-total_to
    
    #Put into a single sorted list, using clever merging
    transactions = []
    totals = {}
    while from_transactions and to_transactions:
        if from_transactions[-1]['timestamp'] > to_transactions[-1]['timestamp']:
            trans = from_transactions.pop()
            totals = update_totals(totals, 'to', trans)
        else:
            trans = to_transactions.pop()
            totals = update_totals(totals, 'from', trans)

        transactions.append(format_transaction(db, trans))
        
    if to_transactions:
        for t in to_transactions:
            totals = update_totals(totals, 'from', t)
            transactions.append(format_transaction(db, t))
    else:
        for t in from_transactions:
            totals = update_totals(totals, 'to', t)
            transactions.append(format_transaction(db, t))

    #Build up the totals into nice to handle lists
    people_owe_you = {}
    you_owe_people = {}
    for user_id, total in totals.iteritems(): 
        total = round(total,2)
        user_id = ObjectId.url_decode(user_id)
        
        user = db.users.find_one({'_id': user_id})
        if total > 0:
            if values_as_nums:
                val = total
            else:
                val = u'£%.2f' % total

            people_owe_you[user['username']] = [user, val]
        elif total < 0:
            if values_as_nums:
                val = abs(total)
            else:
                val = u'£%.2f' % abs(total)

            you_owe_people[user['username']] = [user, val]

    print you_owe_people
    return transactions, balance, people_owe_you, you_owe_people


def update_totals(totals, user_mode, trans):
    user = trans['%s_user' % user_mode].url_encode()
    val = trans['value'] if user_mode == 'to' else 0.0 - trans['value']
    
    totals[user] = totals[user] + val if user in totals else val
    return totals


def format_transaction(db, t):
    u = users.get_user()

    to_user = None if u['_id'] == t['to_user'] else db.users.find_one(t['to_user'])
    from_user = None if u['_id'] == t['from_user'] else db.users.find_one(t['from_user'])

        
    t.update({'from_user':from_user, 'to_user':to_user, 'value':u'£%.2f' % t['value'], 'timestamp': time.strftime('%d %b %Y',time.localtime(t['timestamp']))})
    return t
