#Form stuff
AUTH_FAILURE = "Your username and password were incorrect. Sorry"
def NO_FIELD_SUPPLIED(field):
    return 'No %s supplied' % field
PASSWORDS_DONT_MATCH = 'The passwords don\'t match'
def FIELD_MUST_BE_LEN(field, the_len):
    return '%s must be at least %s characters long' % (field, the_len)
USERNAME_TAKEN = 'Username already taken'
NO_CONTACT_FOUND = 'No contact with that username found'
def ALREADY_CONNECTED(contact):
    return "You're already connected to %s" % contact
CANT_CONNECT_TO_SELF = "You can't connect to yourself!"
def MUST_BE_GREATER_THAN_ZERO(field):
    return "%s must be greater than zero" % field
def MUST_BE_POS_INTEGER(field):
    return "%s must be a number greater than zero" % field
