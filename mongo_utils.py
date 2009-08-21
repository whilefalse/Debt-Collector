def deref_list(db, list):
    return map(lambda(ref): db.dereference(ref), list)

