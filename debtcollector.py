#!/usr/bin/python
## -*- coding: utf-8 -*-

import time
import web
import users
import forms
import mongo_utils
import lang.en as lang
import templates
import transactions
from templates import render
from session import MongoStore
import pymongo
from pymongo import Connection
from pymongo.dbref import DBRef
import math

#To make sessions work
web.config.debug = False

#Get our mongo connection
c = Connection()
db = c.webpy

#Define our urls
urls = (
    '/','Index',
    '/login/','Login',
    '/logout/','Logout',
    '/register/', 'Register',
    '/network/', 'Network',
    '/contacts/', 'Contacts',
    '/transfer/', 'Transfer',
    '/summary/', 'Summary',
    '/users/search/', 'UserSearch',
    '/users/([a-zA-Z0-9-]+)/', 'Profile',
)

#Create app object
app = web.application(urls, globals())
session = web.session.Session(app, MongoStore(db, 'sessions'))
users.session = session
users.collection = db.users

class Index:
    def GET(self):
        return render('home.html')

class Login:
    def GET(self):
        next = web.input(_method='GET').get('next','/summary/')
        return render('login.html', next=next)

    def POST(self):
        post = web.input(_method='POST')
        errors = {}
        try:
            user = users.authenticate(post['username'], post['password'])
            if user:
                users.login(user)
            else:
                errors['__all__'] = lang.AUTH_FAILURE
        except KeyError:
            errors['__all__'] = lang.AUTH_FAILURE

        if errors:
            return render('login.html', errors=errors, next=post.get('next'))
        else:
            return web.seeother(post.get('next','/summary/'))

class Register:
    def GET(self):
        return render('register.html')

    def POST(self):
        post = web.input(_method='POST')
        errors = {}
        username = forms.get_or_add_error(post, 'username', errors, lang.NO_FIELD_SUPPLIED('username'))
        password = forms.get_or_add_error(post, 'password', errors, lang.NO_FIELD_SUPPLIED('password'))
        password_again = forms.get_or_add_error(post, 'password_again', errors, lang.NO_FIELD_SUPPLIED('password again'))

        forms.validate(errors, 'password_again', lang.PASSWORDS_DONT_MATCH, lambda p,p2: p == p2, (password, password_again))

        if username is not None:
            forms.validate(errors, 'username', lang.FIELD_MUST_BE_LEN('Username', 3), lambda u: len(u) >= 3, (username,))
            forms.validate(errors, 'username', lang.USERNAME_TAKEN, lambda u: not bool(db.users.find_one({'username':u})), (username,))
        if password is not None:
            forms.validate(errors, 'password', lang.FIELD_MUST_BE_LEN('Password', 5), lambda p: len(p) >= 5, (password,))            
            
        if errors:
            return render('register.html', errors=errors)
        else:
            users.register(username=username, password=users.pswd(password), contacts=[])
            web.seeother('/login/')            

class Logout:
    def GET(self):
        users.logout()
        return web.seeother('/')

class Network:
    @users.login_required
    def GET(self):
        user = users.get_user()
        trans, balance, people_owe_you, you_owe_people = transactions.get_transaction_details(db, user, values_as_nums=True)

        nodes = {user['username']:0}
        paths = {}

        contacts = mongo_utils.deref_list(db, user['contacts'])
        contact_debts = {user['username']: (people_owe_you, you_owe_people)}

        for contact in contacts:
            nodes[contact['username']] = len(nodes)
            trans, balance, people_owe_you, you_owe_people = transactions.get_transaction_details(db, contact, values_as_nums=True)
            contact_debts[contact['username']] = (people_owe_you, you_owe_people)

        #Do some crazy graph shit
        for person, (owe_you, you_owe)  in contact_debts.iteritems():
            for (username, (user, value)) in owe_you.iteritems():                
                if (nodes[username], nodes[person]) not in paths:
                    paths[(nodes[username], nodes[person])] = value
                    
            for (username, (user, value)) in you_owe.iteritems():
                if (nodes[person], nodes[username]) not in paths:
                    paths[(nodes[person], nodes[username])] = value

        print "NODES"
        print nodes

        #Get rid of current user
        radius = 40
        nodes_list = {0:(user['username'], (radius,radius))}
        del nodes[user['username']]
                    
        #Work out where to put stuff with the graphs.
        degree = (2 * math.pi)/len(nodes)
        coords = [(round(math.sin(degree*num)*radius),round(math.cos(degree*num)*radius)) for num in range(len(nodes))]
        coords = map(lambda (x,y): (x+radius, abs(y-radius)), coords)

        #Set up the node coords
        for n,(k,v) in enumerate(nodes.iteritems()):
            nodes_list[v] = (k,(coords[n]))

        print "NODES LIST"
        print nodes_list
        print "PATHS"
        print paths
        

        #Now replace the line mappings with the actual coords
        paths_list = []
        for (person, person2), value in paths.iteritems():                    
            print "PERSON"
            print person
            print "PERSON2"
            print person2
            print "PERSON 1 NODE:"
            print nodes_list[person]
            print "PERSON 2 NODE:"
            print nodes_list[person2]
            if nodes_list[person][1][1] < nodes_list[person2][1][1]:                
                top, bottom = person, person2
            else:
                if nodes_list[person][1][0] < nodes_list[person2][1][0]:
                    top, bottom = person, person2
                else:
                    top, bottom = person2, person

            start_coords = list(nodes_list[top][1])
            height = nodes_list[bottom][1][1] - nodes_list[top][1][1]
            width = abs(nodes_list[bottom][1][0] - nodes_list[top][1][0])
            up_or_down = 'down' if nodes_list[top][1][0] >= nodes_list[bottom][1][0] else 'up'

            paths_list.append((start_coords, height, width, up_or_down, value))                
            #pass

        print paths_list

        return render('network.html', nodes=nodes_list, paths=paths_list, radius=radius)
                


class Contacts:
    @users.login_required
    def GET(self):
        try:
            contacts = mongo_utils.deref_list(db, users.get_user()['contacts'])
        except KeyError:
            contacts = []
        return render('/contacts/index.html', contacts=contacts)

class AddContact:
    @users.login_required
    def GET(self):
        return render('/contacts/add.html')

class UserSearch:
    @users.login_required
    def GET(self):
        return render('/users/search.html')

    @users.login_required
    def POST(self):
        post = web.input(_method='POST')
        errors = {}
        username = forms.get_or_add_error(post, 'username', errors, lang.NO_FIELD_SUPPLIED('username'))
        
        if not errors:
            result = db.users.find_one({'username':username})
            forms.validate(errors, 'username', lang.NO_CONTACT_FOUND, lambda c: bool(c), (result,))
            
        if result:
            return web.seeother('/users/%s/' % result['username'])
        else:
            return render('/users/search.html', errors=errors)

class Profile:
    @users.login_required
    def GET(self, username):
        contact = db.users.find_one({'username':username})
        if not contact:
            raise web.notfound()

        trans, balance, people_owe_you, you_owe_people = transactions.get_transaction_details(db, users.get_user())

        owes_you = False
        you_owe = False
        if contact['username'] in people_owe_you:
            owes_you = people_owe_you[contact['username']][1]
        elif contact['username'] in you_owe_people:
            you_owe = you_owe_people[contact['username']][1]

        return render('/users/profile.html', profile=contact, connected=self.connected(contact), owes_you = owes_you, you_owe = you_owe)
    
    @users.login_required
    def POST(self, username):
        post = web.input(_method='POST')
        errors = {}
        user = users.get_user()

        contact = db.users.find_one({'username':username})

        forms.validate(errors, 'username', lang.NO_CONTACT_FOUND, lambda c: bool(c), (contact,))
        if contact:
            forms.validate(errors, 'username', lang.ALREADY_CONNECTED(contact['username']), lambda u, c: ('contacts' not in u) or (c not in u['contacts']), (user, contact))
            forms.validate(errors, 'username', lang.CANT_CONNECT_TO_SELF, lambda u, c: c!=u, (user, contact))

        if contact and not errors:
            #Add to the user's contacts
            if 'contacts' not in user or not user['contacts']:
                user['contacts'] = []
            user['contacts'].append(DBRef('users',contact['_id']))
            
            #Add user to the other persons contacts
            if 'contacts' not in contact or not contact['contacts']:
                contact['contacts'] = []
            contact['contacts'].append(DBRef('users',user['_id']))
            
            #Save them both
            db.users.save(user)
            db.users.save(contact)                                       

        return render('/users/profile.html', profile=contact, errors=errors, connected=self.connected(contact))    


    def connected(self, user):
        try:
            connected = user in mongo_utils.deref_list(db, users.get_user()['contacts'])
        except KeyError:
            connected = False
        return connected

class Transfer:
    @users.login_required

    def _deref_contacts(self):
        user = users.get_user()

        try:
            user.update({'contacts': mongo_utils.deref_list(db, user['contacts'])})
        except KeyError:
            user['contacts'] = []
            
        return user

    def GET(self):
        return render('transfer.html', user=self._deref_contacts())

    def POST(self):
        post = web.input(_method='POST')
        errors = {}
        user = users.get_user()
        mode = ''

        #Get all the stuff we want from POST
        if 'from_username' in post:
            mode = 'from'
            other_username = forms.get_or_add_error(post, '%s_username' % mode, errors, lang.NO_FIELD_SUPPLIED('username'))
        else:
            mode = 'to'
            other_username = forms.get_or_add_error(post, '%s_username' % mode, errors, lang.NO_FIELD_SUPPLIED('username'))

        value_pounds = forms.get_or_add_error(post, '%s_value_pounds' % mode, errors, lang.NO_FIELD_SUPPLIED('pounds value'))
        value_pence  = forms.get_or_add_error(post, '%s_value_pence' % mode, errors, lang.NO_FIELD_SUPPLIED('pence value'))
        reason  = forms.get_or_add_error(post, '%s_reason' % mode, errors, lang.NO_FIELD_SUPPLIED('reason'))

        #Process and validate the amount
        try:
            if value_pounds.strip() == '':
                value_pounds = 0
            if value_pence.strip() == '':
                value_pence = 0

            value_pounds = int(value_pounds)
            value_pence = int(value_pence)
            if value_pounds < 0 or value_pence < 0:
                raise Exception

            if value_pounds != None and value_pence != None:
                forms.validate(errors, '%s_value' % mode, lang.MUST_BE_GREATER_THAN_ZERO('Value'), lambda po,pe: (po+pe*100)>0, (value_pounds,value_pence))
        except:
            errors['%s_value' % mode] = lang.MUST_BE_POS_INTEGER('Pounds and pence')
            
        #Validate the reason
        forms.validate(errors, '%s_reason' % mode, lang.NO_FIELD_SUPPLIED('reason'), lambda r: bool(r), (reason,))

        #Validate and get the other user
        if other_username:
            other_user = db.users.find_one({'username':other_username})
            forms.validate(errors, '%s_username' % mode, lang.NO_CONTACT_FOUND, lambda u: bool(u), (other_user,))

        #Now do the rendering
        if not errors:
            value = round((float(value_pounds)*100 + float(value_pence)) / 100.0, 2)
            
            if mode == 'to':
                from_user, to_user = user, other_user
            else:
                from_user, to_user = other_user, user

            trans = db.transactions.save({'from_user': from_user['_id'], 'to_user': to_user['_id'], 'value':value, 'timestamp':time.time(), 'reason':reason})

            return render('transfer.html', success=True, user=self._deref_contacts(), from_user=from_user, to_user=to_user, value="%.2f" % value, mode=mode)
        else:
            return render('transfer.html', errors=errors, user=self._deref_contacts())


class Summary():
    @users.login_required
    def GET(self):
        user = users.get_user()

        trans, balance, people_owe_you, you_owe_people = transactions.get_transaction_details(db, user)

        return render('summary.html', transactions=trans, balance=balance, people_owe_you=people_owe_you, you_owe_people=you_owe_people)


#Set up custom error pages
def notfound():
    return web.notfound(render('404.html'))
app.notfound = notfound

def internalerror():
    return web.internalerror(render('500.html'))
app.internalerror = internalerror

if __name__ == "__main__":
    app.run()
