def get_or_add_error(the_dict, index, the_errors, error_msg):
    try:
        return the_dict[index]
    except KeyError:
        the_errors[index] = error_msg

def validate(the_errors, error_index, error_msg, test, args):
    if not test(*args):
        the_errors[error_index] = error_msg
